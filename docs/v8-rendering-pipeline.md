# COMI V8 Rendering Pipeline — Technische Dokumentation

> **Stand:** Juli 2026  
> **Ziel:** Verständnis aller Rendering-Mechanismen in Curse of Monkey Island (ScummVM V8),  
> insbesondere für die HD-Compositing-Erweiterung (comiupscale).

---

## 1. Überblick: Der Frame-Loop

Jeder Frame durchläuft in `ScummEngine::scummLoop()` (scumm.cpp ~3080) folgende Schritte:

```
scummLoop(delta)
├── processInput()               ← Maus/Tastatur
│   └── checkExecVerbs()         ← V8: Verb-Klicks abarbeiten
├── removeBlastObjects/Texts     ← V8-Reset
├── runAllScripts()              ← V8-Script-Engine läuft
├── restoreBlastObjectsRects()
├── walkActors()                 ← Actor-Bewegung
├── moveCamera()                 ← Kamerascrolling
├── updateObjectStates()         ← States von Room-Objekten aktualisieren
├── scummLoop_handleDrawing()
│   ├── redrawBGAreas()          ← Background + Room-Objekte zeichnen
│   └── processDrawQue()         ← Draw-Queue abarbeiten (inkl. FLOBJs)
├── scummLoop_handleActors()
│   ├── setActorRedrawFlags()
│   ├── resetActorBgs()
│   └── processActors()          ← Actors sortieren + zeichnen (AKOS)
├── handleMouseOver()            ← Verb-Highlight
├── updatePalette()
├── drawDirtyScreenParts()       ← Dirty-Rects → Screen Blit + HD Composite
│   ├── updateDirtyScreen(kVerbVirtScreen)  ← Verbs
│   ├── updateDirtyScreen(kTextVirtScreen)  ← Text
│   ├── updateDirtyScreen(kMainVirtScreen)  ← Haupt-Screen
│   └── renderHDComposite()      ← HD-Overlay (nur bei _hdScale > 1)
└── scummLoop_handleSound()
```

**Drei separate Virtual Screens** (in COMI):
| VirtScreen | Inhalt | Höhe |
|------------|--------|------|
| `kMainVirtScreen` | Spielwelt (Raum + Objekte + Actors) | 480px (COMI) |
| `kVerbVirtScreen` | Verb-Leiste (unten) | 40px ? |
| `kTextVirtScreen` | Dialog-Text (oben) | variabel |

---

## 2. 8-Bit Compositing (ohne HD)

### 2.1 Hintergrund & Room-Objekte

```cpp
// gfx.cpp ~1103
redrawBGAreas()
├── redrawBGStrip()              ← Hintergrund-Bitmap (SMAP/BMAP) Strips
└── drawRoomObjects()            ← Room-Objekte (state != 0, non-FLOBJ)
```

`drawRoomObjects()` (object.cpp ~620) iteriert über alle lokalen Objekte in **umgekehrter ID-Reihenfolge** (höchste ID = hinten):

```cpp
for (i = (_numLocalObjects-1); i > 0; i--)
    if (_objs[i].obj_nr > 0 && (_objs[i].state & 0xF))
        drawRoomObject(i, arg);
```

> **Wichtig:** Nur Objekte mit `state & 0xF != 0` werden gezeichnet.  
> FLOBJs mit `state=0` werden hier **übersprungen**.

### 2.2 Object Image Format (OBIM)

Jedes Room-Objekt hat eine **OBIM** (Object Image) — ein Bitmap im Scumm-Strip-Format:
- Vertikale Strips (8 Pixel breit)
- Jeder Strip ist RLE-komprimiert
- Enthält Header mit Breite/Höhe in Strips

```cpp
ptr = getObjectImage(getOBIMFromObjectData(od), getState(od.obj_nr));
_gdi->drawBitmap(ptr, &_virtscr[kMainVirtScreen], x, ypos, width, height,
                  x - xpos, numstrip, flags);
```

`gdi->drawBitmap()` ist der zentrale 8-Bit-Renderer — er dekomprimiert Strips direkt in den Framebuffer.

### 2.3 Draw-Queue (processDrawQue)

```cpp
// object.cpp ~1178
void ScummEngine::processDrawQue() {
    for (i = 0; i < _drawObjectQueNr; i++) {
        j = _drawObjectQue[i];
        if (j)
            drawObject(j, 0);   // ← OHNE state-Prüfung!
    }
}
```

Objekte kommen in die Queue durch:
- `addObjectToDrawQue()` (z.B. aus `setObjectState()`, `drawObjectAt()`)
- V8-Script-Opcodes `o6_drawObject` (0x61) → `setObjectState()`
- V8-Script-Opcodes `o6_drawObjectAt` (0x62) → Zustand+Position ändern

`drawObject()` (object.cpp ~647) zeichnet **immer** — es prüft nur:
- `obj_nr == 0` → skip
- OBIM-valid → zeichnen via `gdi->drawBitmap()`

**Das ist der Weg, wie FLOBJs gezeichnet werden:** Ein V8-Script ruft `drawObject` auf oder setzt den State, was das Objekt in die Queue bringt.

---

## 3. Das FLOBJ-System (Floating Objects)

### 3.1 Was ist ein FLOBJ?

FLOBJs sind Objekte, die als eigenständige `rtFlObject`-Ressourcen existieren, unabhängig vom aktuellen Raum. COMI nutzt sie für:
- **Obj 114:** `inventory-bg-object` (Inventar-Hintergrund, 640×472)
- **Obj 115:** `increment-inventory-arrow` (Pfeil nach rechts)
- **Obj 116:** `decrement-inventory-arrow` (Pfeil nach links)
- **Obj 105:** `system-cursor-icon`
- **Obj 120:** `two-balloons-icon-object` (Dialog-Icon)

### 3.2 FLOBJ-Ressourcen-Format

```cpp
// object.cpp ~1968-2036
loadFlObject(uint object, uint room) {
    // 1. Finde OBIM + OBCD im Room-Ressource
    findObjectInRoom(&foir, foImageHeader | foCodeHeader, object, room);

    // 2. Allociere lokalen Object-Slot
    objslot = findLocalObjectSlot();

    // 3. Kopiere OBCD + OBIM in eine neue rtFlObject-Ressource
    flob_size = obcd_size + obim_size + 8;
    slot = findFlObjectSlot();
    flob = _res->createResource(rtFlObject, slot, flob_size);

    WRITE_UINT32(flob, MKTAG('F','L','O','B'));
    WRITE_BE_UINT32(flob + 4, flob_size);
    memcpy(flob + 8, foir.obcd, obcd_size);      // Object Code
    memcpy(flob + 8 + obcd_size, foir.obim, obim_size);  // Object Image

    // 4. Verknüpfe lokales ObjectData mit FLOBJ-Slot
    od->fl_object_index = slot;
}
```

**Struktur einer FLOBJ-Ressource:**
```
Offset  Inhalt
0x00    'FLOB' (4 Bytes Tag)
0x04    Größe (Big-Endian uint32)
0x08    OBCD (Object Code — V8-Bytecode für Script)
...     OBIM (Object Image — Strips-Bitmap)
```

### 3.3 Lock/Unlock-Mechanismus

V8-Scripte steuern FLOBJs über Kernel-Funktionen:

```cpp
// script_v8.cpp ~1086
case 11:    // lockObject
    _res->lock(rtFlObject, _objs[objidx].fl_object_index);
    break;
case 12:    // unlockObject
    _res->unlock(rtFlObject, _objs[objidx].fl_object_index);
    break;
```

**Wichtig:** `lock()`/`unlock()` steuern **nur den Resource-Lifecycle** (Garbage Collection),  
**nicht die Sichtbarkeit** auf dem Bildschirm.

- `lock()` verhindert, dass die Resource freigegeben wird
- `unlock()` erlaubt der GC, die Resource beim nächsten `nukeResource()` zu entfernen
- `isLocked()` bleibt für Inventory-Objekte **dauerhaft true** — das ist KEIN Visibility-Signal

**Beleg aus hd_state.log:**
```
FLOBJ[1] obj=116 fl=1 locked=1 state=0 decrement-inventory-arrow
FLOBJ[2] obj=115 fl=2 locked=1 state=0 increment-inventory-arrow
FLOBJ[3] obj=114 fl=3 locked=1 state=0 inventory-bg-object
FLOBJ[4] obj=105 fl=4 locked=1 state=0 system-cursor-icon
FLOBJ[5] obj=188 fl=5 locked=1 state=0 dialog-decrement-icon
FLOBJ[6] obj=189 fl=6 locked=1 state=0 dialog-increment-icon
FLOBJ[22] obj=120 fl=7 locked=0 state=0 two-balloons-icon-object
```

Alle Inventory-FLOBJs sind `locked=1` — sie sind permanent gesperrt und werden nie freigegeben.  
Nur `two-balloons-icon-object` (120) ist `locked=0`.

### 3.4 Wie FLOBJs auf den Bildschirm kommen

FLOBJs werden **nicht** über `drawRoomObjects()` gezeichnet (V8: state=0 → skip, **und** `drawRoomObject()` überspringt sie explizit).  
Sie werden gezeichnet durch:

1. **V8-Script-Opcodes:** Ein Script ruft `drawObject(opcode 0x61)` oder `drawObjectAt(opcode 0x62)` auf → `addObjectToDrawQue()` → `processDrawQue()` → `drawObject()`.
2. **Verb-System:** In COMI werden Inventory-Objekte als Verbs dargestellt — `setVerbObject()` kopiert das OBIM in ein `rtVerb`-Resource, und `drawVerbBitmap()` rendert es auf den Verb-Screen.

**Wichtig:** `setVerbObject()` explizit verboten für FLOBJs:
```cpp
// verbs.cpp ~1422
if (whereIsObject(object) == WIO_FLOBJECT)
    error("Can't grab verb image from flobject");
```

---

## 4. Das Verb-System

### 4.1 VerbSlot-Struktur

```cpp
// verbs.h
struct VerbSlot {
    Common::Rect curRect, oldRect;  // Bildschirmposition
    uint16 verbid;                  // Verb-ID
    uint8  color, hicolor, dimcolor, bkcolor, type;  // Text + Typ
    uint8  charset_nr, curmode;     // Font + Modus (0=inaktiv, 1=aktiv, 2=gehighlighted)
    uint16 saveid;                  // 0 = immer sichtbar
    uint8  key;                     // Tastenkürzel
    bool   center;
    uint8  prep;
    uint16 imgindex;
    int16  origLeft;
    // HD-spezifisch:
    int16  hd_obj_nr;               // Welches Objekt-Bild verwendet wird
    int16  hd_room;                 // In welchem Raum das Objekt ist
};
```

### 4.2 Verb-Typen

```cpp
enum { kTextVerbType = 0, kImageVerbType = 1 };
```

- **TextVerb:** Text-String aus der `rtVerb`-Resource
- **ImageVerb:** OBIM-Bitmap aus einem Room-Objekt (via `setVerbObject`)

### 4.3 setVerbObject — Wie Verben Objekt-Bilder bekommen

```cpp
// verbs.cpp ~1411
void ScummEngine::setVerbObject(uint room, uint object, uint verb) {
    // Finde OBIM + OBCD des Objekts im Raum
    findObjectInRoom(&foir, foImageHeader | foCodeHeader, object, room);

    // Kopiere OBIM in rtVerb-Ressource
    byte *ptr = _res->createResource(rtVerb, verb, size);
    memcpy(ptr, foir.obim, size);

    // HD: Merke welche Objekt-Nummer + Raum
    _verbs[verb].hd_obj_nr = object;
    _verbs[verb].hd_room = room;
}
```

In COMI ruft der Game-Script für jedes Inventory-Item `setVerbObject()` auf —  
das kopiert das OBIM des Items in einen Verb-Slot. Wenn der Spieler rechtsklickt,  
wird das Inventar als Reihe von Image-Verbs gezeichnet.

### 4.4 Verb-Rendering-Loop

```cpp
// verbs.cpp ~519
void ScummEngine::redrawVerbs() {
    for (i = 0; i < _numVerbs; i++) {
        drawVerb(i, mouseOver ? 1 : 0);
    }
}
```

`drawVerb()` ruft für `kImageVerbType` → `drawVerbBitmap()`:
```cpp
// verbs.cpp ~1231
void ScummEngine::drawVerbBitmap(int verb, int x, int y) {
    obim = getResourceAddress(rtVerb, verb);
    // Strips zeichnen
    for (i = 0; i < imgw; i++)
        _gdi->drawBitmap(imptr, vs, tmp, ydiff, imgw * 8, imgh * 8, i, 1, flags);
}
```

---

## 5. AKOS — Actor-Kostüm-System

### 5.1 Ressourcen-Struktur

AKOS ist **kein separates Frame-Textur-System**.  
Eine AKOS-Ressource enthält alles in einem Blob:

| TAG | Inhalt |
|-----|--------|
| `AKHD` | Header: Version, Flags (#chores, #cels, compression codec, #layers) |
| `AKCH` | Chore-Offset-Tabelle (für Animationen) |
| `AKCI` | Cel-Info-Array (width, height, relX, relY, moveX, moveY) |
| `AKOF` | Offset-Tabelle (Pointer in AKCD, AKCI) |
| `AKSQ` | Sequenz-Befehle (loop, goto, sound, conditional vis, DisplayAuxFrame) |
| `AKCD` | Komprimierte Pixel-Daten (RLE-kodiert via Codec) |
| `AKPL` | Palette-Lookup (256 Farben) |

**Codec-Typen** (`akos.h`):
```
AKOS_BYLE_RLE_CODEC    = 1   ← COMI Standard
AKOS_CDAT_RLE_CODEC    = 5
AKOS_RUN_MAJMIN_CODEC  = 16
AKOS_TRLE_CODEC        = 32
```

### 5.2 Zeichen-Pipeline

```cpp
// akos.cpp ~309
byte AkosRenderer::drawLimb(const Actor *a, int limb) {
    // 1. Lade AKOS-Ressource
    // 2. Bestimme aktuelle Animation (Chore) basierend auf facing + frame
    // 3. Lese Sequenz-Befehle aus AKSQ
    // 4. Für jeden Cel-Eintrag:
    //    - Lese Cel-Info (width, height, relX, relY) aus AKCI
    //    - Lese komprimierte Pixel aus AKCD via AKOF
    //    - Dekomprimiere via Codec (z.B. byleRLEDecode)
    //    - Schreibe in 8-Bit-Framebuffer
}
```

**Mehrere Limbs pro Actor** (z.B. Körper + Kopf + Arme) werden **unabhängig** gezeichnet  
und durch relative Offsets (moveX, moveY) übereinander positioniert.

### 5.3 AKOS-Sequenz-Befehle

```
AKC_DrawMany                    = 0x4020  // Mehrere Cels gleichzeitig
AKC_EmptyCel                    = 0x4001  // Leerer Frame
AKC_GoToState / AKC_IfVarGoTo  = 0x4030..0x4031
AKC_StartSound                  = 0x4015
AKC_StartAnim / StartVarAnim    = 0x4080..0x4081
AKC_Flip                        = 0x408A
AKC_DisplayAuxFrame             = 0x408E  // Wichtig für HD!
AKC_HideActor                   = 0x4086
AKC_EndSeq                      = 0x40FF
```

**HD-Interception (akos.cpp ~370ff):**
```cpp
// Cel-Index speichern für Step 2.6
a->_hdCurrentCel = (code & AKC_CelMask);
a->_hdRelX = (int16)READ_LE_UINT16(&costumeInfo->relX);
a->_hdRelY = (int16)READ_LE_UINT16(&costumeInfo->relY);
```

---

## 6. HD-Compositing (renderHDComposite)

### 6.1 HD Canvas

- **Auflösung:** z.B. 2560×1888 (4x)
- **Format:** 32-bit RGBA
- **Hintergrund:** Pre-rendered HD PNG (aus `hd/backgrounds/`)
- **Ohne HD-Background:** Skalierung des 8-bit Content auf HD-Auflösung

### 6.2 Compositing Steps

```
renderHDComposite() [gfx.cpp ~1229]
│
├── Step 1: HD-Background
│   Kopieren des HD-Background-PNG in _hdComposite
│   (3-bpp RGB → 4-bpp RGBA)
│
├── Step 2: 8-bit Content overlay
│   Jedes 8-bit-Pixel, das != clean background, wird auf HD gemappt
│   (über aktuelle Palette) und in _hdComposite geblendet.
│   Index 255 = AKOS transparent → überspringen.
│   Clean-Background-Diff: nur Vordergrundpixel.
│
├── Step 2.5: HD Object Textures
│   Für jedes lokale Objekt (umgekehrte ID-Ordnung):
│   - FLOBJ mit state=0 → Gate über isLocked() (nur V8)
│   - Non-FLOBJ state=0 → immer skippen
│   - HD-Textur laden (hd/objects/obj{NR}_room{R}_state{S}.png)
│   - Culling: überspringe wenn keine sichtbaren 8-bit-Pixel im Bereich
│   - Alpha-Blit mit Alpha-Mask-Tracking
│
├── Step 2.6: HD Costume Textures
│   Für jeden sichtbaren Actor (z-sortiert wie processActors):
│   - HD-Textur via _hdCurrentCel laden
│   - RelX/RelY für Position
│   - Alpha-Blending (voll, halb, oder transparent)
│   - alpha=0: HD-Background wiederherstellen oder darunter liegendes erhalten
│   - Alpha-Mask-Update
│
├── Step 2.6b: 8-bit UI Overlay (nach HD Costumes)
│   Nur Pixel ausserhalb Actor-Bounding-Boxes:
│   - Wenn HD-Costume-Pixel (alpha mask=1) → nie überschreiben
│   - Sonst: 8-bit-Vordergrundpixel drüberlegen
│   → Erhält UI-Elemente (Titelkarten, Text) über HD Costumes
│
├── Step 2.7: HD Font Characters
│   Literarische Font-Chars aus _hdFontChars auf HD-Canvas
│
├── Step 2.8: HD Verb Overlay
│   _hdVerbSurface (von drawVerbBitmap zwischengespeichert):
│   - Nur für "large" Verben (>90% HD-Canvas, z.B. Inventory-Hintergrund)
│   - Alpha-Blit direkt in HD
│
└── Step 3: Copy to screen
    _system->copyRectToScreen(...)
```

### 6.3 Das FLOBJ-Visibility-Problem

Der 8-bit-Renderer hat **kein explizites Visibility-Signal** für FLOBJs:

| Signal | Wert für Inventory-FLOBJs | Bedeutung |
|--------|--------------------------|-----------|
| `state & 0xF` | immer 0 | Steuert nur Room-Objekte |
| `isLocked()` | immer true (locked) | Lifecycle, nicht Visibility |
| `getState()` | immer 0 | Kein Eintrag in ObjectStateTable |
| `_objectStateTable` | kein Eintrag | FLOBJs nie per putState gesteuert |
| `_numVerbs` / `_verbs[].curmode` | variabel | Zeigt nur ob Verb aktiv |
| `WIO_FLOBJECT` | ja | Nur für Script-Routing |

**Aktuelle HD-Lösung** (unvollständig):
```cpp
// gfx.cpp ~1411
if (od.fl_object_index && (od.state & 0xF) == 0) {
    if (_game.version <= 6)
        continue;          // V6: FLOBJs mit state=0 nie zeichnen
    // V8: nur zeichnen wenn gelockt (hilft nicht)
    if (!_res->isLocked(rtFlObject, od.fl_object_index))
        continue;
}
```

> **⚠️ Wichtig:** FLOBJs werden im originalen 8-Bit-Renderer **nie durch `drawRoomObject()` gezeichnet**  
> (`object.cpp ~612`: `if (version <= 6 || fl_object_index == 0) drawObject(i, arg)`).  
> Schritt 2.5 ist also ein **komplett neuer Rendering-Pfad**, der im Original nicht existiert.  
> Das macht das Visibility-Problem fundamental: es gibt kein Vorbild im 8-Bit-Code.

---

## 7. FLOBJ-Rendering: Drei unabhängige Pfade

FLOBJs haben **drei potenzielle Wege**, auf den Bildschirm zu kommen:

| Pfad | Beschreibung | Aktiv? |
|------|-------------|:-----:|
| **A: drawRoomObject()** | Klassischer Object-Renderer (object.cpp ~612) | ❌ In V8 explizit deaktiviert |
| **B: Verb-System (kVerbVirtScreen)** | `drawVerbBitmap()` rendert OBIM auf Verb-Screen | ✅ Inventory als Verb |
| **C: HD Step 2.5** | FLOBJ-HD-Textur direkt auf HD-Canvas | ✅ Nur im HD-Modus |

**Pfad A ist der Grund, warum `state` und `getState()` nie funktionieren:** V8 überspringt FLOBJs bewusst,  
weil sie über einen anderen Mechanismus verwaltet werden (Verbs + Blast Objects).

---

## 8. UsageBits-System (usage_bits.h/.cpp)

Der 8-Bit-Screen ist in **Strips** (8 Pixel breit) unterteilt. Jeder Strip hat 96 Bits:

```
gfxUsageBits[410 Strips × 3 uint32s]
```

| Bit | Flag | Bedeutung |
|:---:|------|-----------|
| 96 | USAGE_BIT_DIRTY | Strip-Hintergrund muss neu gezeichnet werden |
| 95 | USAGE_BIT_RESTORED | Strip wurde restauriert (Blast-Objects) |
| 1-80 | Actor N | Actor N belegt diesen Strip |

- `setGfxUsageBit(strip, USAGE_BIT_DIRTY)` — markiert Strip als dirty
- `testGfxUsageBit(strip, USAGE_BIT_DIRTY)` — prüft ob Strip dirty
- `testGfxAnyUsageBits(strip)` — prüft ob Actor-Bits gesetzt

---

## 9. Frame-Composition-Reihenfolge (V8/COMI)

Komplette Sequenz pro Frame (`scumm.cpp ~3080-3299`):

```
 1. processInput()
      └── checkExecVerbs()           ← Verb-Klicks abarbeiten

 2. removeBlastObjects()             ← Overlay-Queue reset
    removeBlastTexts()

 3. runAllScripts()                  ← V8-Script-Engine
      └── o8_drawObject()            ← Kann Objekte in Draw-Queue setzen

 4. restoreBlastObjectsRects()       ← Overlay-Rects wiederherstellen
    restoreBlastTextsRects()

 5. walkActors()                     ← Actor-Bewegung
    moveCamera()

 6. updateObjectStates()             ← _objs[i].state aus _objectStateTable syncen

 7. scummLoop_handleDrawing():
    a. redrawBGAreas():
       - redrawBGStrip()             ← Hintergrund Strips
       - drawRoomObjects()           ← NUR non-FLOBJ objects (state!=0)
    b. processDrawQue()              ← Queued objects (auch FLOBJs!)
    c. redrawVerbs()                 ← Verb-Leiste (COMI: Verb-Coin)

 8. scummLoop_handleActors():
    a. setActorRedrawFlags()         ← COMI: ALLE Actors redraw=true
    b. resetActorBgs()               ← Hintergrund hinter Actors restaurieren
    c. processActors()               ← Actors sortieren + zeichnen (AKOS)
       └── drawActorCostume()
            └── AkosRenderer::drawLimb()

 9. scummLoop_handleEffects()        ← Palette-Cycling, Fades

10. updatePalette()                  ← Palette-Änderungen anwenden

11. drawDirtyScreenParts() (V6+):
    a. drawBlastObjects()            ← Screen-Overlays
    b. processUpperActors()          ← V8: actors mit layer<0 (Inventory-Chest)
    c. drawBlastTexts()              ← Untertitel
    d. updateDirtyScreen(verbs)      ← Verb-VirtScreen blitten
       updateDirtyScreen(text)       ← Text-VirtScreen blitten
       updateDirtyScreen(main)       ← Haupt-VirtScreen blitten (coalesced strips)
    e. renderHDComposite()           ← HD-Compositing (nur wenn _hdScale>1)

12. scummLoop_handleSound()
```

---

## 10. FLOBJ vs. Room-Object — Vergleich

| Kriterium | Room-Object | FLOBJ |
|-----------|-------------|-------|
| Resource-Typ | Teil von `rtRoom` | Eigener `rtFlObject`-Slot |
| Persistenz | Nur im aktuellen Room | Überlebt Room-Transition (wenn locked) |
| Script-Code | In Room-OBCD | In `rtFlObject`-Ressource (eigener Slot) |
| Image | Direkter Offset in `rtRoom` | 'OBIM'-Tag via `findResource()` im FLOBJ-Blob |
| Drawing (V8) | `drawObject()` in `drawRoomObject()` | **Nicht** via classic Renderer; nur Verb-System |
| Show/Hide | `putState()` (Bytecode 0x8a) | `lockObject`/`unlockObject` (Kernel 11/12) |
| Room-Exit | Immer gelöscht | Nur unlocked; locked überleben |
| COMI-Usage | Raum-Dekoration | Inventory-Items, UI-Elemente |
| Max-Slots | `_numLocalObjects` (~200) | `_numFlObject` = 50 (V6) / 128 (V8) |

---

## 11. GDI.drawBitmap-Details (gfx.cpp ~3367-3487)

Der zentrale 8-Bit-Renderer:

```
drawBitmap(ptr, vs, x, y, width, height, stripnr, numstrip, flag)
├── SMAP (Strip-Map-Offset-Tabelle) lesen
│   V8: ptr selbst ist SMAP (kein findResource nötig)
├── Z-Plane-Liste laden (getZPlanes)
├── Für jeden Strip:
│   ├── Dirty-Rect aktualisieren (tdirty/bdirty)
│   ├── drawStrip(): RLE-Chunk dekomprimieren → FB
│   ├── COMI: immer transpStrip=true
│   └── decodeMask(): Z-Buffer-Masken updaten
└── Z-Buffer: RLE-decodierte Masken pro Z-Plane
    (wichtig für Actor-Clipping gegen Objekte)
```

---

## 12. Wichtige Code-Stellen

### 12.1 `drawRoomObject()` — Der Gate (object.cpp ~600-618)

```cpp
void ScummEngine::drawRoomObject(int i, int arg) {
    const int mask = (_game.version <= 2) ? kObjectStateIntrinsic : 0xF;
    ObjectData *od = &_objs[i];
    if ((od->state & mask) == 0)
        return;               // state=0 → unsichtbar
    do {
        a = od->parentstate;
        if (!od->parent) {
            if (_game.version <= 6 || od->fl_object_index == 0)
                drawObject(i, arg);   // ← FLOBJs werden hier ÜBERSPRUNGEN!
            break;
        }
        od = &_objs[od->parent];
    } while ((od->state & mask) == a);
}
```

### 12.2 `clearRoomObjects()` — FLOBJ-Persistenz (object.cpp ~760-784)

```cpp
// Locked FLOBJs überleben Room-Transitions!
if (_objs[i].fl_object_index) {
    if (!_res->isLocked(rtFlObject, _objs[i].fl_object_index)) {
        _res->nukeResource(rtFlObject, _objs[i].fl_object_index);
        _objs[i].obj_nr = 0;
        _objs[i].fl_object_index = 0;
    }
    // Locked FLOBJs bleiben erhalten!
}
```

### 12.3 Script-Dispatch für FLOBJs (script.cpp ~453-459)

```cpp
case WIO_FLOBJECT:   // V8-Script-Engine: Bytecode kommt aus FLOBJ-Ressource
    idx = _objs[idx].fl_object_index;
    _scriptOrgPointer = getResourceAddress(rtFlObject, idx);
    _lastCodePtr = &_res->_types[rtFlObject][idx]._address;
```

### 12.4 `getOBIMFromObjectData()` (object.cpp ~1370-1382)

```cpp
const byte *ScummEngine::getOBIMFromObjectData(const ObjectData &od) {
    if (od.fl_object_index) {
        ptr = getResourceAddress(rtFlObject, od.fl_object_index);
        ptr = findResource(MKTAG('O','B','I','M'), ptr); // Sucht 'OBIM' im FLOBJ-Blob
    } else {
        ptr = getResourceAddress(rtRoom, _roomResource) + od.OBIMoffset;
    }
    return ptr;
}
```

### 12.5 object.h — ObjectData (lines 64-79)

```cpp
struct ObjectData {
    uint32 OBIMoffset;         // Offset zum OBIM im Room
    uint32 OBCDoffset;         // Offset zum OBCD im Room
    int16  walk_x, walk_y;
    uint16 obj_nr;             // 0 = Slot frei
    int16  x_pos, y_pos;
    uint16 width, height;
    byte   actordir;
    byte   parent;
    byte   parentstate;
    byte   state;              // Synced from _objectStateTable via updateObjectStates()
    byte   fl_object_index;    // 0 = Room-Objekt, >0 = FLOBJ-Slot in rtFlObject
    byte   flags;
};
```

---

## 13. Verb-Screen vs. Main-Screen vs. FLOBJs

**Wichtige Erkenntnis:** Das Inventory-Overlay in COMI wird NICHT als FLOBJ auf den Main-Screen gezeichnet.  
Es wird auf den **Verb-Virtual-Screen** gerendert:

- COMI hat einen separaten `kVerbVirtScreen` (unterer Bildbereich)
- Das Inventory-Panel ist ein Fullscreen-Verb
- `setVerbObject()` erzeugt ein Verb mit `hd_obj_nr=114` (inventory-bg-object)
- `drawVerbBitmap()` rendert es in den Verb-Screen
- `updateDirtyScreen(kVerbVirtScreen)` bringt es auf den Bildschirm

**ABER:** FLOBJs (114, 115, 116, 105) haben trotzdem `state=0`, `locked=1` und werden **trotzdem**  
in Step 2.5 erfasst — weil sie im `_objs[]` Array existieren. Das HD-Overlay rendert sie also  
doppelt: einmal als Verb-Overlay (Step 2.8) und einmal als FLOBJ (Step 2.5).

---

## 14. Schlüssel-Dateien

| Datei | Inhalt |
|-------|--------|
| `scumm.cpp ~3080` | `scummLoop()` — Haupt-Frame-Loop |
| `scumm.cpp ~4046` | `scummLoop_handleDrawing()` — Drawing-Phase |
| `scumm.cpp ~4057` | `ScummEngine_v7::scummLoop_handleDrawing()` — V7+ inkl. redrawVerbs() |
| `gfx.cpp ~538` | `drawDirtyScreenParts()` — Dirty-Rect-to-Screen |
| `gfx.cpp ~1229` | `renderHDComposite()` — HD Compositing (Steps 1-3) |
| `gfx.cpp ~1103` | `redrawBGAreas()` — Background + Room-Objekte |
| `gfx.cpp ~3367` | `Gdi::drawBitmap()` — Strip-Bitmap-Renderer (SMAP, Z-Planes) |
| `gfx.cpp ~3489` | `drawStrip()` — Einzel-Strip dekomprimieren |
| `gfx.cpp ~4012` | Decompressoren (BMCOMP\_\* codecs) |
| `object.cpp ~600` | `drawRoomObject()` — **Der Gate: V8 skippt FLOBJs** |
| `object.cpp ~620` | `drawRoomObjects()` — Non-FLOBJ Objekte |
| `object.cpp ~647` | `drawObject()` — Strips-Bitmap Rendering |
| `object.cpp ~1178` | `processDrawQue()` — Queued Objects inkl. FLOBJs |
| `object.cpp ~1370` | `getOBIMFromObjectData()` — OBIM für FLOBJs via findResource |
| `object.cpp ~1679` | `setObjectState()` — State+Draw-Queue |
| `object.cpp ~1968` | `loadFlObject()` — FLOBJ-Erstellung (FLOB+OBCD+OBIM) |
| `script_v8.cpp ~1086` | kernelSetFunctions 11/12: lockObject/unlockObject |
| `script_v8.cpp ~1427` | `o8_drawObject()` — V8-Bytecode 0x98 |
| `script.cpp ~453` | Script-Dispatch für WIO\_FLOBJECT |
| `verbs.cpp ~519` | `redrawVerbs()` — Verb-Rendering |
| `verbs.cpp ~1130` | `drawVerb()` — Text/Image-Verb zeichnen |
| `verbs.cpp ~1231` | `drawVerbBitmap()` — Verb-Bitmap (OBIM aus rtVerb) |
| `verbs.cpp ~1411` | `setVerbObject()` — Objekt-Bild an Verb binden (hd\_obj\_nr!) |
| `akos.cpp ~309` | `drawLimb()` — AKOS-Cel zeichnen |
| `akos.cpp ~649` | `paintCelByleRLE()` — BYLE-RLE-Dekoder |
| `akos.h` | AKOS-Header-Strukturen, Codecs, Command-Enums |
| `actor.cpp ~2314` | `processActors()` — Actor-Sortierung + Rendering |
| `actor.cpp ~2508` | `processUpperActors()` — V8 Actors mit layer<0 |
| `actor.cpp ~2522` | `drawActorCostume()` — AKOS-Costume-Renderer aufrufen |
| `actor.cpp ~2988` | `setActorRedrawFlags()` — COMI: alle Actors redraw=true |
| `object.h` | `ObjectData` struct (fl\_object\_index, state, etc.) |
| `verbs.h` | `VerbSlot` struct (verbid, type, curmode, hd\_obj\_nr, etc.) |
| `scumm.h` | Engine-Klasse mit \_numFlObject, \_verbs, etc. |
| `usage_bits.h` | `USAGE_BIT_DIRTY`, `USAGE_BIT_RESTORED` |
| `usage_bits.cpp` | `setGfxUsageBit`, `testGfxUsageBit`, etc. |

---

## 15. Offene Fragen für das HD-Projekt

1. **Visibility-Signal:** Wie erfährt Step 2.5, ob ein FLOBJ gerade sichtbar sein soll?
   - `isLocked()` ist konstant true
   - `state` ist konstant 0
   - `getState()` liefert 0
   - Gibt es ein spezifisches `ScriptSlot`-Signal?
   - **Neue Erkenntnis:** Der Verb-Slot `curmode` wechselt zwischen 0 (inaktiv) und 1 (aktiv) — das wäre ein echtes Visibility-Signal.

2. **Verb-Draw-Zeitpunkt:** `drawVerbBitmap()` wird in `redrawVerbs()` aufgerufen,  
   das in `scummLoop_handleDrawing()` passiert — **vor** `renderHDComposite()`.  
   Bei "large" Verben wird die HD-Textur in `_hdVerbSurface` zwischengespeichert  
   und in Step 2.8 direkt in HD geblendet. Kleine Verben werden in den 8-bit  
   Verb-Screen gerendert und dann in Step 2 geupscaled.

3. **FLOBJ vs. Verb Doppelrendering:**  
   Pfad C (HD Step 2.5) rendert FLOBJs als HD-Textur.  
   Pfad B (Verb-System) rendert dasselbe FLOBJ als Verb.  
   → Lösung: Step 2.5 müsste FLOBJs überspringen, die bereits als Verb gezeichnet werden.

4. **Actor-AKOS-Cel-Mapping:** Wie werden AKOS-Cel-IDs auf HD-PNG-Dateien gemappt?  
   Aktuell via `_hdCurrentCel` — aber mehrere Limbs/DrawMany-Cels pro Frame  
   können verschiedene Cels haben. Die HD-Textur muss das gesamte Actor-Image  
   in einer Pose sein, nicht pro-Limb. Zusätzliches Problem: `_hdCurrentCel`  
   wird bei jedem Limb überschrieben — nur der letzte Limb-Cel bleibt erhalten.

5. **drawRoomObject überspringt FLOBJs in V8:**  
   `object.cpp ~612`: `if (_game.version <= 6 || od->fl_object_index == 0)`  
   → FLOBJs werden nie durch den 8-bit Object-Renderer gezeichnet.  
   Step 2.5 ist der EINZIGE Pfad, der FLOBJs als Objekte rendert —  
   es gibt kein Vorbild im 8-Bit-Code für die Sichtbarkeitssteuerung.

---

*Dokumentation erstellt aus ScummVM-Codeanalyse Juli 2026*  
*Fork: harrytyp/comiupscale — https://github.com/harrytyp/comiupscale*
