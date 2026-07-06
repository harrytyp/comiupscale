# Inventory HD Fix — Root Cause & Solution

> **Datum:** 6. Juli 2026
> **Version:** v0.0.53+
> **Status:** ✅ Inventory background (obj 114) rendered in HD
> **Offen:** Inventory item icons still SD

---

## 1. Das Problem

Der HD Inventar-Hintergrund (`0003_inventory-bg-object_0000.png`, obj_nr=114) wurde nie in HD angezeigt. 17+ Build-Versuche (v0.0.26–v0.0.52) haben es nicht geschafft, das Inventar korrekt in HD darzustellen.

### Symptome
- Inventar immer SD (v0.0.26 baseline)
- Inventar NIE sichtbar (v0.0.27)
- Inventar PERMANENT sichtbar, nicht interagierbar (v0.0.28–32)
- HD Texturfragmente oben links (v0.0.40–48)
- "Off by one pixel" Culling (v0.0.50–52)

---

## 2. Die Render-Pfade

### Pfad A: Verb System → drawVerbBitmap → Step 2.8 (NIE funktioniert)

V8 Scripts → `o8_verbOps` → `SO_VERB_IMAGE` → `setVerbObject()` → `drawVerbBitmap()` → `_hdVerbSurface` → Step 2.8 compositing.

**Warum tot:** `setVerbObject()` hat einen Guard:
```cpp
if (whereIsObject(object) == WIO_FLOBJECT)
    error("Can't grab verb image from flobject");
```
Der Inventar-Hintergrund (obj 114) ist ein FLOBJ (`fl_object_index=3`) → `SO_VERB_IMAGE` würde crashen. Die V8 Scripts rufen es nie auf. `hd_obj_nr` bleibt 0 auf allen Verb-Slots. `drawVerbBitmap` wird nie fürs Inventar aufgerufen.

**Zusätzlich:** `_hdVerbDrawCount` (von drawVerbBitmap inkrementiert) war immer 0 → falsches "inventory closed" Signal.

### Pfad B: Step 2.5 FLOBJ Compositing (der richtige Pfad)

`renderHDComposite()` → Step 2.5 → iteriert `_objs[]` rückwärts → lädt HD Textur für obj 114 aus Room 3 → positioniert an `od.x_pos/y_pos` → Culling → Alpha-Blending.

**Warum geculled?** Der Culling-Check vergleicht 8-Bit-Pixel im Objektbereich mit dem Clean Background. Bei Inventar offen: 258.743 sichtbare Pixel von 302.080 (85.7%). Threshold war 151.040 (50%). Eigentlich locker bestanden — aber `inventoryActive` war **immer false**, was eine zusätzliche Force-Cull-Schwelle aktivierte:
```cpp
if (!inventoryActive)
    threshold = MAX(threshold, visiblePixels + 1); // force cull
```
→ `threshold = MAX(151040, 258744) = 258744 > 258743` → CULLED **um 1 Pixel**.

---

## 3. Die Lösung (v0.0.53)

### Problem: `inventoryActive` wurde nie gesetzt

Die Variable `inventoryActive` war auf `false` initialisiert und wurde NIE auf `true` gesetzt. Der ursprüngliche Ansatz (Verb-System-Signal) funktionierte nie, weil `setVerbObject` nie aufgerufen wird.

### Lösung: Cursor (obj=105) als binäres Signal

Der `system-cursor-icon` FLOBJ (obj_nr=105, fl=4) ist im 8-Bit-Composite sichtbar:
- **Inventar ZU:** 0 sichtbare Pixel (Cursor wird als Hardware/Software-Overlay gezeichnet, nicht im 8-Bit-Composite)
- **Inventar OFFEN:** ~3.000 sichtbare Pixel (Script zeichnet den Cursor als FLOBJ im Composite)

→ Perfektes binäres Signal.

### Implementierung (gfx.cpp, nach dem Pixel-Scan):

```cpp
// Real-time inventory detection using cursor (obj=105) visibility.
if (od.obj_nr == 105 && od.fl_object_index != 0 && visiblePixels > 100)
    inventoryActive = true;
```

Damit wird `inventoryActive=true` gesetzt, sobald der Cursor im 8-Bit-Composite sichtbar ist. Für obj=114 (large FLOBJ) entfällt dann die Force-Cull-Schwelle, und der normale 50%-Threshold (151.040) greift → 258.743 > 151.040 → **RENDER**.

### Warum funktioniert das?

| Objekt | Zustand | visiblePixels | Schwellwert bei invActive=false | Schwellwert bei invActive=true | Ergebnis |
|--------|---------|--------------|-------------------------------|-------------------------------|----------|
| obj=105 (cursor) | zu | 0 | 1 (force) | — | CULL |
| obj=105 (cursor) | offen | 3.045 | 1 (force) | — | RENDER |
| obj=114 (bg) | zu | 57.755 | 151.040 | — | CULL |
| obj=114 (bg) | offen | 258.743 | 258.744 (off by 1!) | 151.040 | **RENDER** ✓ |

---

## 4. Logging-Entwicklung

Die Debug-Logs durchliefen mehrere Iterationen:

| Version | Methode | Problem |
|---------|---------|---------|
| v0.0.30 | `warning("HDDBG ...")` | Konsolenausgabe, keine Datei |
| v0.0.47 | `hd_state.log` mit DumpFile | Nur letzter Frame (truncate) |
| v0.0.50 | `hdPrintf()` → Buffer | Buffer vollgelaufen mit STATE-Dumps |
| v0.0.51 | Persistent buffer + append | Read-modify-write bis 64KB→truncate |
| v0.0.54 | **Buffer-only: 24KB→file** | ✅ Sauber: ~100 Frames History |

### Aktuelle Log-Einträge:
- `--- frame=N room=N ---` — Frame-Header
- `POS obj=114 ...` — Position des Inventar-Hintergrunds
- `CULL/RENDER obj=114 ...` — Culling-Entscheidung
- `KEY 'i' (0x69)` — Tastatureingaben
- `MOUSE LCLICK/RCLICK pos=(x,y)` — Mausklicks
- `setVerbObject: ...` — falls Verb-System je feuert
- `drawVerbBitmap ...` — falls Verb-Bitmap je geladen wird
- `step2.8 verb-overlay ...` — Step 2.8 Compositing

---

## 5. Ausblick

**Inventar-Icons:** Die HD Texturen für Inventar-Gegenstände (obj 117-274, Room 3) existieren in `/hd/objects/`. Sie werden aktuell noch nicht in HD gerendert. Mögliche Ursachen:
- Culling im Step 2.5 killt sie (Main VirtScreen Diff zeigt keine Veränderung, weil Inventar auf Verb VirtScreen liegt)
- Positionen sind (0,0) → falsche HD-Position
- Kein `setVerbObject` → kein drawVerbBitmap → kein HD-Ladeversuch

**Nächste Schritte:**
1. Input-Rekorder bauen (Tasten/Maus aufzeichnen)
2. Automatisierte Wiedergabe der Inputs
3. Debugging der Inventar-Icons mit Input-Rekorder
