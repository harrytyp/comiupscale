# Fehlende HD-Texturen: vier Ursachenklassen und der aktuelle Befund

Ziel: im fertigen Bild keine 8-Bit-Grafik mehr. Dafür muss jede sichtbare 8-Bit-Textur
einer Ursache zugeordnet werden können. Diese vier Klassen sind zu unterscheiden:

| Klasse | Erkennungsmerkmal | Werkzeug |
|---|---|---|
| 1 fehlt | keine Datei im Asset-Verzeichnis | `hd_missing.log`, `NOMAP`/`MISSING` |
| 2 wird nicht geladen | Datei vorhanden, Engine fragt sie nie an | `hd_spy.log` + Verzeichnisvergleich |
| 3 falsche Position | HD gezeichnet, aber versetzt | 8-Bit- und HD-Kasten je Bild vergleichen |
| 4 scrollt/skaliert falsch | Versatz oder Maßstab driftet über die Bildfolge | Vergleich über die Folge, `shift_probe.py` |

## Befund vom 24.10.2026

**Klasse 1 ist flächendeckend.** Vergleich der Asset-Verzeichnisse:

```
94 Räume mit HD-Hintergrund
65 Räume mit HD-Objekten
29 Räume mit Hintergrund, aber ohne jedes Objekt-Asset:
   2, 4, 5, 6, 7, 8, 11, 17, 25, 27, 29, 38,
   40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 57, 79, 88, 89, 90, 93, 94
```

**Klasse 2 in den Schiffsszenen.** Die Texturspur (`HD_SPY=1`) zeigt für Raum 47:

```
216 × AKOS nr=254 frame=8      (Figur)
  1 × OBJ  nr=1367 state=1 x=0 y=0 w=640 h=480
```

Ein einzelnes Objekt deckt den ganzen Bildschirm ab und wird in 8 Bit gezeichnet. Die
Engine fragt dafür **kein** HD-Bild an (`hd_missing.log` bleibt leer), weil Vollbild-Objekte
im Objektpfad als „nicht zum Laufzeit-Kompositing geeignet" gelten. In Räumen wie 40–50 ist
der Raumhintergrund selbst ein solches Objekt: das HD-Bild ist geladen, wird aber in 8 Bit
überzeichnet.

Nachweis der Sichtbarkeit: mit `HD_TINT_8BIT=1` sind 97,4 Prozent des Bildes magenta, und
der Vordergrundzähler meldet 302080 von 307200 Pixeln (98,3 Prozent).

## Die Quelle der Pipeline ist selbst unvollständig

Alle Objekt-Texturen entstehen aus `/opt/data/dist/comi-original-assets.zip`
(`reupscale_objects.sh` liest ausschließlich daraus). In diesem ZIP liegen:

```
objects/  ->  1365 Bilder
Raum 0003 ->   366 Bilder
Raum 0047 ->     0 Bilder
Raum 0041 ->     0 Bilder
Raum 0089 ->     0 Bilder
```

Die 29 Räume fehlen also nicht erst beim Hochskalieren, sondern schon in der Rohsammlung.
Der Fehler sitzt im Schritt, der dieses ZIP erzeugt, nicht im Upscaler und nicht in der
Engine. Solange das ZIP unvollständig ist, kann kein noch so guter Fix am Renderer die
Räume reparieren.

Reihenfolge zum Beheben:

1. ZIP für die 29 Räume ergänzen (Objekte aus den Spieldaten extrahieren)
2. `bash scripts/reupscale_objects.sh --objects`
3. `python scripts/build_object_map.py`
4. `python scripts/check_texture_packs.py` und `python scripts/rebuild_texture_packs.py`
5. Messung wiederholen (`HD_TINT_8BIT=1`), Magenta-Anteil vergleichen

## Nächste Schritte

1. **Objekte für die 29 Räume extrahieren** und in die Textur-Packs aufnehmen
   (Pipeline, nicht Einzelfall). Danach `config/object_map.json` neu bauen.

   Ablauf je Raum, so wie die vorhandenen Objekte entstanden sind:

   ```
   nutcracker sputm room decode COMI.LA0 <raum>     # legt <raum>/OBJS/*.png an
   # jede Objekt-PNG auf 4x hochskalieren und als hd/objects/<raum>_<name>_<state>.png ablegen
   python scripts/build_object_map.py               # Objektnummer -> Name/Zustand
   python scripts/check_texture_packs.py            # Pack vollstaendig?
   ```

   `scripts/full_pipeline.sh` extrahiert in Zeile 95 nur die Hintergründe (`bg_<raum>.png`).
   Die Objekt-Extraktion fehlt dort als Schritt — sie muss in die Pipeline, nicht als
   Handarbeit daneben. Genau diese Lücke erklärt die 29 Räume ohne Objekt-Assets.
2. **Vollbild-Objekte als Hintergrund behandeln**: Ist ein Objekt so groß wie der
   Bildschirm und existiert eine HD-Fassung, darf die 8-Bit-Version nicht darüber
   gezeichnet werden. Das ist eine Regel in der Zeichenlogik.
3. Klassen 3 und 4 danach prüfen; sie brauchen Bildfolgen, keine Einzelbilder.

## Warum frühere Messungen das nicht fanden

Verglichen wurden Hintergründe, nie die einzelnen Texturen. Ein Vollbild-Objekt, das den
HD-Hintergrund überdeckt, sieht in jeder Kennzahl „unauffällig" aus, weil das Bild ja zum
Original passt — nur eben in der falschen Auflösung.

## Versuch: Vollbild-Objekt nicht über HD zeichnen

Regel eingebaut (`object.cpp`): deckt ein Objekt mindestens den Bildschirm ab und ist ein
HD-Hintergrund für den Raum geladen, wird es nicht gezeichnet; jeder Fall landet in
`work/dumps/hd_fullcover.log`.

Ergebnis: die Regel greift in Raum 87 (`SKIP room=87 obj=1367`), **nicht in Raum 47**.
Dort bleibt der Vordergrund bei 98,3 Prozent, und es erscheint keine SKIP-Zeile — das
Vollbild wird also nach dem Raumsprung nicht über `drawObject` gezeichnet, sondern über
den Raumbild-Pfad (`redrawBGStrip`/Raumzeichnung).

Nächster Schritt: dieselbe Regel im Raumbild-Pfad anwenden oder den 8-Bit-Bildschirm nach
dem Laden des HD-Hintergrunds neu aufbauen. `_bgNeedsRedraw` beim Laden zu setzen hat
nicht gereicht.

## Wichtig: das Ausblenden ist geloest — hier wird es nicht neu aufgemacht

Die Frage „ab wann blenden wir ein Objekt aus" ist bereits beantwortet und im Code gelöst:
die Zeichenstufe misst die **tatsächlich sichtbaren Pixel** (`visiblePixels`, Stichprobe
über jede vierte Zeile/Spalte). Geschlossenes Inventar (Objekt 114) hat rund 640 sichtbare
Pixel, offen sechststellig; unter einem Drittel der Fläche gilt es als geschlossen und wird
ausgeblendet. Diese Regel bleibt unangetastet.

Der Fehler liegt woanders: die **Fehlt-Maske** (`hdMissingMask`) wird aus der *deklarierten*
Objektgröße gebaut, nicht aus den sichtbaren Pixeln. Für Objekt 114 heißt das 640x472 statt
640 Pixel — die Maske deckt den ganzen Bildschirm, und die Vordergrundprüfung entscheidet
nicht mehr am Bildinhalt.

Beleg (`HD_SPY=1`, erster Lauf):

```
FG sx=0 sy=0 cur=242 clean=242 maske=1     <- gleicher Wert, trotzdem Vordergrund
MASKE obj=114 w=640 h=472 rx=0 ry=0        <- deklarierte Groesse, nicht sichtbare Pixel
```

Die beiden Versuche, das über Flächendeckung zu lösen, sind wieder zurückgenommen — sie
hätten das gelöste Thema ein zweites Mal aufgemacht. Richtig ist, die Maske mit **derselben**
Sichtbarkeitsprüfung zu bauen wie die Zeichenstufe.

## Wer die Fehlt-Maske fuellt

Mit `HD_SPY=1` protokolliert (`hd_maskobj.log`). In Raum 47 ist es **Objekt 114** — der
Inventarhintergrund, geschlossen, aber mit 640x472 über dem ganzen Bild:

```
MASKE obj=114 w=640 h=472 rx=0 ry=0 state=0
```

Damit ist die Fehlt-Maske vollstaendig gesetzt, und die Vordergrundpruefung entscheidet
nicht mehr anhand des Bildinhalts: die ersten protokollierten Pixel zeigen
`cur=242 clean=242 maske=1` — gleicher Wert, trotzdem Vordergrund.

Die Ausnahme fuer flaeckendeckende Objekte (90 Prozent) steht im Code, wirkt aber noch
nicht; die Protokollzeile gibt jetzt auch `visW x visH` aus, damit der naechste Lauf zeigt,
an welcher Zahl die Bedingung scheitert.

## Drei Versuche, alle ohne Wirkung auf Raum 47

| Versuch | Ergebnis |
|---|---|
| Vollbild-Objekt in `drawObject` überspringen | greift in Raum 87, nicht in 47 (keine SKIP-Zeile) |
| `_bgNeedsRedraw` nach dem Laden des HD-Hintergrunds | keine Änderung |
| Vollbild-Objekt aus `hdMissingMask` ausschließen | keine Änderung (98,3 % / 97,37 % unverändert) |

**Der offene Widerspruch**, der als Nächstes geklärt werden muss:

```
Stichprobe der Vorlage gegen den Bildschirm:  0,8 % abweichend  (4800 Pixel, Raster 8)
Schleife im Zeichenlauf:                     98,3 % Vordergrund (302080 von 307200)
```

Beide Zahlen stammen aus demselben Build, demselben Frame, denselben Puffern — und sie
widersprechen sich. Also unterscheiden sie sich in etwas, das ich noch nicht sehe: anderer
Puffer, anderer Zeitpunkt im Frame oder eine andere Zeilenbasis.

Nächster Schritt: in der Schleife die ersten 20 abweichenden Pixel mit Koordinaten und
beiden Farbindizes protokollieren. Damit ist in einem Lauf belegt, was dort wirklich
verglichen wird, statt der dritten Hypothese zu folgen.

## Behoben: Maske benutzt jetzt dieselbe Sichtbarkeitsprüfung

Die Fehlt-Maske prüft vor dem Eintrag, wie viele Pixel des Objektkastens sich tatsächlich
vom sauberen Hintergrund unterscheiden (Stichprobe alle 4 Pixel). Unter einem Viertel gilt
das Objekt als nicht sichtbar — dieselbe Regel, die die Zeichenstufe für das Ausblenden
benutzt, nur eine Stelle weiter. Es ist damit **keine neue Regel**, sondern die vorhandene
Entscheidung an der zweiten Stelle.

Messung Raum 47 (gleicher Lauf, feste Zeit):

```
vorher:  Vordergrund 98,3 %   Magenta 97,37 %
nachher: Vordergrund  1,0 %   Magenta  0,00 %
```

Das Bild ist durchgehend HD, kein Magenta mehr. Im letzten Bild einer Folge steigt der
Magenta-Anteil wieder auf 97 Prozent — dort wechselt die Szene (Inventar/Übergang), das ist
der nächste eigene Fall.

## Messung nach dem Fix (alle scrollenden Räume, HD_TINT_8BIT)

Anteil der Bildfläche, der noch aus der 8-Bit-Ebene kommt:

```
0,00 %  22, 40, 45, 46, 47, 48, 49, 50, 51, 53, 55, 60, 75, 79
0,01 %  14        0,02 %  61, 70
0,86 %  15        1,17 %  41
3,37 %  44        4,46 %  33
8,02 %  86
keine Aufnahme: 25, 42, 43
```

Vor dem Fix: Raum 47 bei 97,37 Prozent. Die Oberdecks 44 bis 51 lagen zwischen 0 und
3,4 Prozent statt bei 97.

Rohdaten: `docs/magenta-anteil-scrollende-raeume.csv`.

## Restprozente nach dem Fix: fehlende Objekt-Assets, nicht Zeichenfehler

Raum 86 war der höchste Rest (8,5 Prozent Magenta). Auswertung der Fehlt-Maske:

```
29 Objekte in der Maske   (105, 114, 115, 116, 1337, 1339, 1340, 1341, ...)
 6 HD-Assets fuer Raum 86
23 Objekte ohne HD-Bild
```

Damit ist der Rest Klasse 1: die Objekte sind nicht vorhanden, nicht falsch gezeichnet. Für
Räume 33, 44 und 41 gilt dasselbe Muster in kleinerem Umfang (4,5 / 3,4 / 1,2 Prozent).

## Aufzeichnung auch ohne Sprung scharfschalten

`_hdCaptureArmed` hing am Sprung (`HD_JUMP_ROOM`). Räume, die darüber nicht erreichbar sind
(25, 42, 43, 86), lieferten deshalb **null** Bilder, obwohl der Lauf sauber durchlief
(`rc=0`, 240 Bilder). Jetzt schaltet auch das erfolgreiche Laden eines HD-Hintergrunds die
Aufzeichnung scharf, sofern `HD_JUMP_ROOM` gesetzt ist. Raum 86 liefert damit 80 Bilder.

## Klasse 2 gefunden: Assets vorhanden, Objekttabelle unvollständig

Arbeitsliste erzeugt (`docs/fehlende-objekte.txt`, je Raum die Objekte, die ohne HD-Bild
gezeichnet werden). Erstes Ergebnis:

```
Raum 15: 25 Objekte in der Fehlt-Maske, aber 21 HD-Assets vorhanden
config/object_map.json: 560 Einträge, obj 398/399/403 fehlen
hd/objects/0015_bottomless-mug-object_0000.png  u. a. existieren
```

Das ist **Klasse 2**: die Datei ist da, die Engine findet sie nicht, weil die Zuordnung
Objektnummer → Name fehlt. Kein fehlendes Asset, kein Zeichenfehler — eine Lücke in der
Tabelle.

`scripts/build_object_map.py` läuft derzeit nicht durch:

```
ImportError: cannot import name 'load_resource' from 'nutcracker.sputm.resource'
```

Die Import-Pfade im Skript passen nicht zur installierten nutcracker-Version (die
Extraktion selbst, `extract_all_raw.py`, benutzt andere Pfade und läuft). Das ist zu
reparieren, bevor die Tabelle neu gebaut werden kann.

## Korrektur: es ist doch Klasse 1

Die Vermutung, die Objekttabelle verhindere das Laden vorhandener Assets, war falsch. Für
Raum 15 enthält `config/object_map.json` 19 Einträge, und die vorhandenen Bilder sind
korrekt zugeordnet:

```
412 -> bottomless-mug-object -> hd/objects/0015_bottomless-mug-object_0000.png
```

Die Objekte in der Fehlt-Maske (398, 399, 403, 405, 406, ...) haben dagegen **kein** Bild —
weder in der Tabelle noch im Verzeichnis. Sie fehlen in der Extraktion.

Damit gilt für alle Reste dasselbe: **Klasse 1, fehlende Objektbilder**. Die Tabelle ist in
Ordnung; der Tabellenbauer war nur zusätzlich kaputt (Importpfad) und ist repariert.

Der Unterschied zwischen „Assets vorhanden" und „Objekte in der Maske" kommt daher, dass die
Zählung pauschal je Raum erfolgte: 21 Bilder für Raum 15 heisst nicht, dass die 25 gezeichneten
Objekte versorgt sind — es sind verschiedene Objekte.

## Werkzeug: DOBJ vollständig auslesen

`scripts/dump_dobj.py` gibt das Objektverzeichnis aus (Nummer, Name, Raum, Zustand):

```
1401 DOBJ-Einträge
 398  gold-tooth-object   room=15
 399  town-mudpuddle      room=15
```

Damit ist belegbar, welche Objekte es im Spiel gibt. Objekt 398 existiert also — sein Bild
fehlt in der Sammlung, nicht in den Spieldaten.

## Extraktion: Räume mit und ohne Objekte

`extract_all_raw.py` meldet jetzt je Raum die Zahl der Objekte. Erste Messung:

```
Room 47: mask index None (0/0 objects agree)  ->  0 Objekte
Room 86: mask index None (3/6 objects agree)  ->  6 Objekte
```

Raum 47 hat in den Spieldaten **keine** Objektbilder; sein Vollbild ist ein Raumbild.
Raum 86 hat sechs, gezeichnet werden einundzwanzig.

Die Extraktion deckt nur einen Teil der Räume ab (40 von 94 hatten Objektdateien). Das ist
die eigentliche Pipeline-Lücke: `read_objects` liefert für viele Räume nichts, und der
Grund dafür ist noch nicht bestimmt.

## Warum manche Räume keine Objektbilder liefern — untersucht

Werkzeuge: `scripts/count_obim.py` (OBIM je Raum), `scripts/obim_struktur.py` (Aufbau je OBIM),
`scripts/dump_dobj.py` (Objektverzeichnis, 1401 Einträge).

```
Raum 15: 43 OBIM      Raum 86: 29 OBIM
Raum 41:  0 OBIM      Raum 47:  0 OBIM
```

Räume 41 und 47 haben **keine** Objektbilder in den Spieldaten — dort ist nichts zu holen,
das Vollbild ist ein Raumbild.

Bei 15 und 86 haben viele OBIM **nur einen Kopf (IMHD) und kein Bild (IMAG)**:

```
OBIM 0: {'IMHD': 1, 'IMAG': 1}
OBIM 1: {'IMHD': 1}          <- kein Bild
OBIM 2: {'IMHD': 1}          <- kein Bild
```

Solche Objekte zeichnen ihr Bild aus einer anderen Quelle. Zwei Änderungen sind eingebaut,
haben die Messung aber noch nicht bewegt:

1. `read_objects` im v8-Zweig liest zusätzlich `IMxx`-Blöcke, wenn kein `IMAG` da ist.
2. `HdObjectManager::loadObject` sucht unter den anderen Räumen desselben Objekts weiter,
   wenn der Pfad im aktuellen Raum fehlt.

Messung danach: Raum 86 8,65 → 8,39 Prozent, Raum 15 0,86 → 0,99 Prozent. Also **nicht**
die Lösung — die Bilder existieren offenbar auch unter anderen Raumschlüsseln nicht.

Nächster Ansatz: für ein konkretes Objekt (86, Nummer aus `hd_maskobj.log`) prüfen, ob es
im Objektverzeichnis überhaupt einen Dateinamen hat, und ob dieser Name irgendwo in
`hd/objects/` liegt. Damit ist entschieden, ob es ein Extraktions- oder ein Zuordnungsproblem
ist — für genau dieses Objekt, nicht für den ganzen Raum.

## Die Objekttabelle war unvollständig — 560 von 1401

Der Grund, warum Objekte wie `1339 soggy-paper-cone` (Raum 86) nie ein HD-Bild bekommen
konnten: `config/object_map.json` enthielt nur Objekte mit vorhandener Bilddatei — **560 von
1401** Einträgen des Objektverzeichnisses. Für die übrigen 841 kannte die Engine nicht einmal
den Namen, also konnte sie auch kein geteiltes Bild finden.

Der Tabellenbauer nimmt jetzt **alle** DOBJ-Einträge auf (Name, Raum, Zustand), auch ohne
Datei, und ergänzt Verweise auf geteilte Bilder (die `-icon`-Fassung in einem anderen Raum).

```
object_map.json: 1401 Einträge   (vorher 560)
841 Objekte ohne Bilddatei aufgenommen
```

Wirkung auf die Messung: **keine.** Raum 86 8,65 → 8,72 Prozent, Raum 15 0,86, Raum 33 4,44,
Raum 44 3,29 — alle im Bereich der Schwankung.

Damit ist belegt: die Objekte, die in 8 Bit gezeichnet werden, haben in den Spieldaten
**kein eigenes Bild**, und die geteilte Icon-Fassung greift nur in Einzelfällen (ein Treffer).
Für den Rest müsste das Bild aus einer anderen Quelle kommen — Kandidat sind die
Inventar-/Icon-Objekte, die als eigene Objekte mit eigener Nummer geführt werden.

## Zustands-Spiegelung: eingebaut, aber nicht die Ursache

Zustand 1 ist in COMI die gespiegelte Fassung von Zustand 0. Fehlt das Bild für den
gezeichneten Zustand, nimmt `HdObjectManager` jetzt das Basis-Bild und spiegelt es —
in `getObjectSurface` (der Masken- und Zeichenpfad) **und** in `loadObject`.

Betroffen sind 49 Objekte im Spiel, zum Beispiel:

```
275 cannon-treasure-door    Raum 9   Dateien [0]  fehlt [1]
434 town-bush-plaque        Raum 15  Dateien [0]  fehlt [1]
1335 pepper-mill            Raum 86  Dateien [0]  fehlt [1]
```

Messung danach: Raum 86 8,58 Prozent, Raum 15 0,99 Prozent — unverändert. Die Spiegelung ist
trotzdem richtig (sie schließt eine echte Lücke), sie erklärt den Rest aber nicht.

## Der Rest in Raum 86 ist ein einziges Objekt ohne Bild

Die Magenta-Flächen im Bild wurden direkt geortet (`harness/magenta_orte.py`, 32er-Blöcke,
Rückrechnung auf Raumpixel). Ergebnis: ein senkrechter Streifen bei x 560-600, y 176-352.

Bei Kamera 592 fällt das genau auf:

```
1360  carnival-snowcone-sign  rx=1152 ry=248  224x120   ->  0 Assets
```

Das ist der sichtbare Rest. Das Objekt hat kein Bild in der Sammlung. Bei den anderen
Räumen liegt derselbe Fall vor (`1350 soda-jerk-object`, Raum 86, ebenfalls 0 Assets).

## Wie ScummVM das Objektbild holt (Code-Beleg)

`getObjectImage` in `engines/scumm/object.cpp` (v8): `IMAG` → `WRAP` → `OFFS` + `BOMP/SMAP`.
Fehlt der `IMAG`-Block, gibt die Funktion `nullptr` zurück und es wird **nichts** gezeichnet.

Daraus folgen zwei Aussagen:

1. Objekte, deren OBIM nur `IMHD` enthält, sind für das Bild unsichtbar — sie können keinen
   8-Bit-Rest erzeugen. Die Magenta-Flächen stammen also von Objekten **mit** `IMAG`.
2. Solche Objekte wiederum sind extrahierbar, und für Raum 86 wurden sechs erzeugt.

Damit bleibt ein Widerspruch offen: die Fehlt-Maske nennt 21 Objekte für Raum 86, die
Extraktion erzeugt sechs — und mindestens eines der genannten (1360
`carnival-snowcone-sign`) hat weder in der Sammlung noch unter seinem Namen ein Bild.

Nächster Schritt: die sechs extrahierten Namen den 21 Masken-Objekten gegenüberstellen.
Damit steht fest, ob die Maske Objekte nennt, die gar nicht gezeichnet werden (dann ist die
Maske zu weit), oder ob Bilder unter einem anderen Namen entstehen (dann ist die
Namensbildung das Problem).

## Kurskorrektur: der Rest kommt nicht aus Objekten

Drei Belege, unabhängig voneinander:

1. `hd_missing.log` wird bei einem Raum-86-Lauf **gar nicht angelegt** — `HdObjectManager` meldet
   kein einziges fehlendes Objekt.
2. Die Extraktion gewinnt 6 Objekte aus 29 OBIM; die übrigen 23 haben nur `IMHD` und keinen
   Bildblock (`obim_struktur.py`). Ohne Bildblock zeichnet ScummVM nichts (`getObjectImage`).
3. Der HD-Hintergrund ist an jeder Kameraposition zu 99,8 Prozent deckend — es gibt kein Loch,
   das man mit einem Alpha-Test finden könnte.

Der Magenta-Streifen wandert außerdem mit der Kamera (x 560-608 im ersten Bild, x 192-240 im
zweiten), nicht mit einem Objekt.

Damit gilt: die sichtbaren 8-Bit-Flächen entstehen im **Hintergrund-Pfad** von
`renderHDComposite` — die HD-Ebene deckt dort nicht ab, obwohl das Bild deckend ist. Die
früheren Schlüsse („fehlende Objekt-Assets") sind damit widerlegt; die Objekttabelle und die
Zustands-Spiegelung bleiben trotzdem richtige Korrekturen, sie beheben nur etwas anderes.

Nächster Schritt: im Komposit je Bild die verwendeten Versätze mitschreiben (SD links, HD
links, Skalierung) und mit der Lage des Streifens vergleichen. Damit ist die Stelle im Code
benannt statt im Bild gesucht.

## Der Rest ist die Vordergrund-Ebene des Raums

Die Signalfarbe sitzt auf `palFg` — den Vordergrund-Pixeln des Raumbilds. Und genau diese
Ebene fehlt in der gesamten Kette:

```
hd/              backgrounds, costumes, fonts, objects, objects_layers
Roh-Extraktion   backgrounds, costumes, fonts, objects, objects_layers
```

Kein `foreground`, kein `SMAP`, kein `PF`. Die HD-Hintergründe wurden aus dem *Hintergrund*
hochskaliert; die Vordergrund-Ebene zeichnet ScummVM zur Laufzeit darüber, und im HD-Satz gibt
es dafür nichts. Wo der Vordergrund leer ist, fällt es nicht auf — deshalb sehen die meisten
Räume sauber aus. In Raum 86 ist er ein senkrechter Streifen, und der wandert mit der Kamera,
weil er Teil des Raumbilds ist.

Das erklärt alle Beobachtungen auf einmal:

- `hd_missing.log` bleibt leer — es ist kein Objekt.
- Die OBIM ohne Bildblock sind irrelevant — sie werden nicht gezeichnet.
- Der HD-Hintergrund ist deckend — der Vordergrund liegt darüber, nicht darin.
- Der Streifen wandert mit der Kamera — er gehört zum Raum, nicht zu einem Objekt.

Nächster Schritt: die Vordergrund-Ebene (PF/SMAP) extrahieren, hochskalieren und im Komposit
über den HD-Hintergrund legen. Damit verschwindet der Rest — und zwar für alle Räume, nicht
nur für Raum 86.

## Messung: die 8-Bit-Pixel stammen aus Objekten, und die Objekte haben keinen Bildblock

Die Engine zählt jetzt selbst, wer die 8-Bit-Pixel malt (`HD_TINT_8BIT`, Zeile `quelle:` in
`hd_fg.log`):

```
fgVon8bit 21,9 %   Figur 5.363 (8,0 %)   Objekt 62.028 (92,0 %)   sonst 0
```

Zuordnung der Magenta-Flächen zu den Maskenrechtecken (gleicher Lauf, gleiches Bild):

```
obj 1341  104x184 bei (  8,224)  magenta 78,2 %   14.973 px
obj 1349   72x112 bei ( 48,216)  magenta 89,6 %    7.222 px
obj 1348   96x168 bei (192,160)  magenta 40,0 %    6.445 px
obj 1339   72x48  bei (280,312)  magenta 50,1 %    1.733 px
```

Diese Objekte sind **keine** FL-Objekte (`fl=0` an allen Maskeneinträgen), holen ihr Bild also
laut `getOBIMFromObjectData` aus dem Raum selbst:

```cpp
ptr = getResourceAddress(rtRoom, _roomResource) + od.OBIMoffset;
```

In Raum 86 haben aber 24 von 29 OBIM nur einen Kopf:

```
1  snowcone-object        IMHD
2  dinghy-dogs-hair       IMHD
4  soggy-paper-cone       IMHD
...
25 carnival-snowcone-sign IMHD
```

Damit steht der Widerspruch fest und ist eng umrissen: die Objekte werden gezeichnet, haben
im Raum aber keinen eigenen `IMAG`-Block. Der nächste Schritt ist ein einzelner Log-Eintrag an
der Zeichenstelle — der aufgelöste OBIM-Zeiger und die dort gefundenen Tags für `obj=1341`.
Damit ist belegt, ob ScummVM vorwärts in den nächsten OBIM läuft oder die Bilder aus einer
anderen Struktur holt.

## Der Rest sind Figuren — bewiesen durch Abschalten

Statt die Quelle aus Koordinatenkästen zu schließen (was in die Irre führte: 92 Prozent
"Objekte" war reine Geometrie, weil die Kästen halbe Bildschirme groß sind), lassen sich
Zeichenwege abschalten und messen:

```
normal                     8,65 % magenta
HD_NO_OBJECTS=1            8,74 %   unverändert
HD_NO_ACTORS=1             0,00 %   alles weg
HD_NO_ACTORS=1 HD_NO_OBJECTS=1  0,00 %
```

Damit ist belegt: **jede verbleibende 8-Bit-Fläche gehört zu einer Figur.** Objekte,
Hintergrund, Objekttabelle und Objektzustände sind als Ursache ausgeschlossen — jede dieser
Vermutungen ist damit widerlegt, nicht nur bestritten.

`hasCostume()` meldet dabei keine Fehltreffer (das neue `hd_costume_miss.log` bleibt leer),
also findet die Engine ein HD-Bild und legt einen Eintrag an. Die Figur wird trotzdem in
8 Bit gezeichnet — der Fehler liegt damit **nach** der Eintragsbildung, beim Zeichnen des
Eintrags (Laden der Fläche oder Deckungsprüfung), nicht bei der Suche.

Schalter: `HD_NO_OBJECTS` (object.cpp, `drawObject`), `HD_NO_ACTORS` (actor.cpp,
`drawActorCostume`, nicht im Trefferpfad).

## Figur gefunden, Laden in Ordnung — der Fehler liegt in der Deckung

Zwei Wege, auf denen eine Figur stillschweigend in 8 Bit bleibt, sind jetzt protokolliert:

- `hasCostume()` ohne Treffer → `hd_costume_miss.log` — **bleibt leer**
- `loadCostume()` schlägt fehl → `hd_costume_loadfail.log` — **bleibt leer**

Beide Dateien entstehen bei einem Raum-86-Lauf nicht. Die Engine findet das HD-Bild also und
lädt es. Trotzdem bleibt die Figur in 8 Bit sichtbar (Abschalttest: ohne Figuren 0,00 Prozent).

Damit ist die Ursache auf die **Deckung** eingegrenzt: die 8-Bit-Silhouette der Figur ist
größer als die Fläche, die die HD-Textur überdeckt — oder die Reihenfolge im Komposit lässt
magenta stehen, wo die HD-Figur nicht hinreicht. Das ist die letzte Stelle vor dem Ziel.

## Alpha-Löcher im Kostüm: gemessen, aber nicht die Ursache

Die sichtbare Figur in Raum 86 ist `akos=438` (Datei `LFLF_0086_AKOS_0438_aframe_0.png`,
672x544). Sie hat sehr viele durchsichtige Stellen **innerhalb** der Silhouette:

```
transparent gesamt   65,0 %
Loecher innen        110.759 Pixel = 30,3 % der Bildflaeche
```

Das schien die Erklärung: die Engine zeichnet die HD-Figur, an den Löchern bleibt die
8-Bit-Figur stehen. `hdFillAlphaHoles` lief mit 3 Durchgängen und füllt einen Ring pro
Durchgang — also auf 200 erhöht und gemessen:

```
Raum 86: 8,72 % magenta — unveraendert (vorher 8,65-8,74)
Nebenwirkung: Lauf deutlich langsamer (80 -> 44 Bilder je Messung)
```

Damit ist auch das widerlegt, und die Änderung wurde zurückgenommen. Die Löcher sind
vorhanden, aber nicht die Ursache des 8-Bit-Rests.

Offen bleibt damit allein die Deckungsfrage im Komposit: das Rechteck, in das die HD-Figur
geschrieben wird, gegen die Fläche der 8-Bit-Figur im selben Bild.

## Zerlegung des Komposits in seine Stufen

Die Engine schreibt mit `HD_DUMP_STEPS=1` jeden Zwischenstand. Über Raum 86 gemessen:

```
1_hintergrund    0,00 % magenta
2_vordergrund   21,94 %
3_objekte       21,94 %     Objekt-Schritt deckt nichts ab
4_kostueme       8,72 %     Kostüm-Schritt deckt 13,22 Punkte ab
fertig           8,72 %
```

Damit ist der Rest **quantifiziert**: der Kostüm-Schritt deckt 60 Prozent des 8-Bit-Vordergrunds
ab und lässt 8,72 Punkte stehen. Der Objekt-Schritt trägt nichts bei — seine Pixel sind
entweder schon vorher abgedeckt oder er zeichnet nicht über sie.

Zusammen mit dem Abschalttest (ohne Figuren: 0,00 Prozent) heißt das: die HD-Kostüme decken die
8-Bit-Silhouette der Figur nur teilweise. Die verbleibenden 8,72 Prozent sind die Differenz
zwischen 8-Bit-Figur und HD-Figur — Ausrichtung, Skalierung oder Form.

## Die Kostümbilder sind da — sie werden nur nicht verwendet

Raum 86 hat HD-Kostüme für **AKOS 0423 bis 0438** (16 Kostüme, 823 Dateien). Trotzdem bekommen
nur **zwei** Akteure einen HD-Eintrag (`ai=18` → akos 432, `ai=20` → akos 438). Die übrigen
werden 8 Bit gezeichnet, obwohl ihr Bild vorliegt.

Die Restflächen sind kompakt und hoch, nicht flach — also Figuren/Requisiten, keine Schatten:

```
Flaeche 55808   58x100 Bildschirmpixel   Fuellung 0,60
Flaeche 26276   42x84                    Fuellung 0,47
Flaeche 10964   31x47                    Fuellung 0,47
Flaeche  6640   22x24                    Fuellung 0,79
```

Der Ausfall ist damit im Sammelschritt der Einträge zu suchen (`gfx.cpp`, Schleife über
`_actors` ab ~2700). Dort gibt es genau zwei stille Ausgänge, die keinen Eintrag erzeugen und
nichts protokollieren:

- `sameCel && firstCel > 0` ist falsch **und** die Limb-Schleife findet nichts, weil
  `_hdNumLimbs == 0` ist oder alle `_hdLimbCel[li] <= 0` sind.
- `!a->_visible` bzw. `_costume == 0` (zählt `step26_noCostume`, ohne Nummer).

Der erste Fall ist der wahrscheinliche: ein Akteur ohne Limb-Daten erzeugt weder Eintrag noch
Protokollzeile und bleibt damit vollständig in 8 Bit. Genau dort ist als Nächstes eine
Protokollzeile mit `ai`, `_costume`, `_hdNumLimbs` und den Limb-Cels nötig — und für den Fall
ohne Limb-Daten ein Rückfall auf das vollständige Kostümbild.

## Schatten in HD: der Rest fällt

Ursache war die Auslassung `if (a->_shadowMode != 0) continue;`. Die Sonde zeigt, dass genau
die fehlenden Akteure diesen Wert tragen:

```
ai=1   akos=399  sichtbar=1  schatten=3  limbs=2  cel0=13
ai=12  akos=429  sichtbar=1  schatten=3  limbs=3  cel0=7
```

Neu: Schatten werden gezeichnet, aber nicht mit ihrer Textur, sondern als abgedunkelte Fassung
(RGB auf 45/40 Prozent, Deckkraft 150/255) auf einer eigenen Kopie — der Zwischenspeicher
bleibt unberührt. Damit ist der Schatten scharf und vom Hintergrund unabhängig.

Messung (magenta, Mitte des Laufs):

```
Raum 86   8,65 -> 1,31 %     (max 1,91)
Raum 15   0,86 -> 0,29 %
Raum 33   4,44 -> 0,17 %     (einzelne Bilder bis 7,06)
Raum 41   1,17 -> 0,00 %
Raum 44   3,29 -> 7,14 %     <- Verschlechterung, offen
```

Raum 44 ist der einzige Rückschritt: mit `HD_NO_ACTORS=1` fällt er auf 2,78 Prozent, die
restlichen 4,36 Punkte stammen also von Akteuren — dort ist zu prüfen, ob viele Schattenakteure
den Eintragspuffer (256) füllen und echte Figuren verdrängen.

## Objekte ohne eigenes Bild gehören zum Raumbild

Viele OBIM tragen nur einen Kopf (IMHD) und kein Bild (IMAG). ScummVM zeichnet sie nicht —
sie sind Teil des Raumbilds, und die HD-Ebene deckt sie bereits ab. Die Fehlt-Maske markierte
sie trotzdem und erzeugte damit einen Rest, den es gar nicht gibt.

Jetzt wird vor dem Eintrag in die Maske geprüft, ob das Objekt in den Spieldaten ein Bild hat:

```cpp
if (!getObjectImage(getOBIMFromObjectData(mod), mod.state & 0xF))
    continue;
```

**Wirkung (magenta, Mitte des Laufs):**

```
Raum 86   1,31 -> 0,02 %
Raum 44   7,14 -> 3,85 %
```

Raum 44 hat danach noch 3,85 Prozent, davon 3,72 von Figuren (`HD_NO_ACTORS=1` → 0,13 Prozent).
Die betroffenen Akteure tragen `schatten=3` (akos=2 und akos=253).

## Schatten: schwarz und durchsichtig, nicht abgedunkelte Figur

Die erste Fassung multiplizierte die Kostümfarben (RGB 45/40 Prozent) und behielt damit den
Farbton der Figur — der Schatten wirkte bräunlich und wie ein Teil des Bildes. Richtig ist ein
reiner Schatten: schwarz, Deckkraft aus der Alpha-Maske des Kostüms.

```cpp
const uint32 a = (c >> 24) * 55 / 100;
row[sx2] = (a << 24);      // schwarz, 55 Prozent der Maskendeckkraft
```

Damit dunkelt der Schatten nur ab und trägt keine eigenen Farben. Messung: Raum 86 bleibt bei
0,02-0,04 Prozent.

## Nur Modus 1 ist ein Schatten

`_shadowMode` traegt nicht nur Schatten: Raum 44 fuehrt die Spielfigur (`akos=2`) mit dem
Wert 3. Wer `!= 0` als Schatten behandelt, malt also echte Figuren schwarz zu — genau der
Effekt, der als "braeunlicher Schatten" auffiel.

Mit `_shadowMode == 1`:

```
Raum 86   0,03 %
Raum 44   3,87 %
```

Raum 86 bleibt damit sauber, ohne dass Figuren abgedunkelt werden — die Abdunkelung war fuer
die Abdeckung nie noetig. Raum 44 unveraendert; dort liegt der Rest woanders.

## Raum 44: der HD-Satz sass um den Kameraversatz zu weit links

Gemessen mit dem eigenen Messplatz (Kopie der Release-Binary, deren Diagnosepfade auf einen
eigenen Ordner zeigen, damit parallele Aufgaben sich die Aufnahmen nicht loeschen):
`HD_TINT_8BIT=1`, `HD_FIXED_DELTA=20`, `HD_JUMP_ROOM=44`, `HD_DUMP_SEQ=1`, `HD_EXIT_AFTER=240`,
magenta in der Mitte der Folge. Ausgangswert auf HEAD ca595c97: **3,87 Prozent** (80 Bilder,
max 3,89), identisch mit dem Wert aus der Regressionsmessung.

Drei Fassungen, gleiche Messung, nur die Zeichenposition der HD-Kostueme geaendert:

```
unveraendert                                       3,87 %
Cel-Hotspot (relX/relY) ein zweites Mal addiert    3,40 %
Kameraversatz sdLeft nicht mehr abgezogen          0,78 %
```

Die letzte Fassung bleibt stehen. Sie ist in Raeumen ohne Kameraversatz wirkungslos
(Gegenprobe: Raum 47 unveraendert 0,00 Prozent, Raum 9 0,02 Prozent wie vorher), weil dort
`sdLeft = 0` gilt und der ausgerechnete Wert derselbe ist.

Nachkontrolle mit der installierten Release-Binary (`release/linux/scummvm`, md5 gleich der
Fork-Binary), zweiter unabhaengiger Lauf: Raum 44 **0,78 Prozent** (80 Bilder, max 0,78),
Raum 47 **0,00 Prozent**. Beide Zeilen stehen in `reports/magenta/ergebnis.csv`.

Warum das die richtige Stelle ist: der Komposit uebernimmt die 8-Bit-Ebene spaltenweise 1:1
(`hdXStart[sx] = sx * hdW / visW`, der Kameraversatz steckt in Schritt 1, also in der
Hintergrundkopie). Die 8-Bit-Figur steht damit in Pufferkoordinaten, und der HD-Pfad durfte
`sdLeft` nicht ein zweites Mal abziehen. In Raum 44 (Kamera 46) sass jedes HD-Kostuem 46
Spielpixel zu weit links, die 8-Bit-Silhouette blieb rechts davon stehen.

Der Cel-Hotspot war dagegen schon enthalten: `entries[ei].drawX` ist `relX` plus der
aufgelaufene Limb-Versatz aus dem AKOS-Kopf, und `drawY` entsprechend. Ein zweites Einrechnen
verbessert Raum 44 nur auf 3,40 Prozent, also deutlich schlechter als die Kamera-Korrektur, und
verschiebt die Figur zusaetzlich senkrecht. Deshalb verworfen.

Was danach uebrig bleibt: 0,78 Prozent in Raum 44, verteilt auf mehrere kleine Flaechen. Das ist
die Differenz zwischen 8-Bit-Silhouette und HD-Textur (Alpha-Raender, Skalierung), nicht mehr die
Lage. Fuer die naechste Stufe gehoert dort die Deckungspruefung hin, nicht die Position.

Messwerkzeug: `harness/versatz_stufen.py` (Stufen 2 bis 4 eines Laufs, Kaesten und
Kreuzkorrelation) und `harness/versatz_sichtung.py`. Ein Vergleich der Stufen ist nur im selben
Lauf zulaessig, weil die Stufendumps jedes Bild ueberschrieben werden.

## Alpha-Kanal im Kostuem-Blitz: geprueft, kein blinder RGB-Schreibvorgang

Verdacht: der Blit der HD-Kostueme schreibt RGB ohne den Alpha-Byte zu pruefen, deshalb
stehen an durchsichtigen Stellen Farben der Textur im Bild. Der Code sagt etwas anderes.
Die Zeichenschleife (`gfx.cpp:2987` bis `gfx.cpp:3058`) hat drei Zweige auf `alpha = pix >> 24`:

```
alpha >= 128    Bildpunkt wird geschrieben, Maske wird gesetzt          (2987)
alpha 1..127    mit dem, was darunter liegt, verrechnet                (2991)
alpha == 0      HD-Hintergrund zurueck, Maske wird gesetzt             (3014)
```

Der Alpha-Kanal wird also ausgewertet. Was an durchsichtigen Stellen trotzdem 8 Bit zeigt,
sind zwei Regeln, die die 8-Bit-Ebene als Fuellung benutzen:

1. `alpha == 0`, wenn darunter 8-Bit-Vordergrund liegt (`foregroundBelow`), dann bleibt der
   8-Bit-Punkt stehen (`gfx.cpp:3028` bis `3053`). Eingebaut fuer Raum 89, wo die Figur unter
   der durchsichtigen Flaeche einer grossen HD-Hand steckt.
2. Stufe 2.6b legt danach 8-Bit-Punkte erneut ueberall dort ab, wo die HD-Maske leer ist
   (`gfx.cpp:3145` bis `3240`), und zwar in echten Palettenfarben.

Punkt 2 ist der Grund, warum der Magenta-Anteil die sichtbare 8-Bit-Flaeche unterschaetzt:
`HD_TINT_8BIT` faerbt nur die 8-Bit-Ebene der Stufe 2 und die Haengebleibsel aus Punkt 1.
Die Stufe 2.6b schreibt echte Farben und wird von der Messung gar nicht erfasst.

### Gegenprobe mit Zaehlern im Blit (`HD_ALPHA_SPY`)

Neuer Schalter, nur Zaehler, keine Aenderung am Bild. Raum 44, Sprung per `HD_JUMP_ROOM`,
80 Bilder (F=44 bis F=123), Aufruf:

```
cd /opt/data/local/comi-hd-repo/release/linux
HD_JUMP_ROOM=44 HD_FIXED_DELTA=20 HD_EXIT_AFTER=240 HD_DUMP_SEQ=1 HD_TINT_8BIT=1 \
  HD_TRACE_DRAW=1 HD_ALPHA_SPY=1 timeout -k 5 120 ./scummvm --config=scummvm_video.ini --path=game comi
python3 harness/alpha_gegenprobe.py <hd_state.log> <hd_seq>
```

Je Bild werden fuenf Kostuem-Eintraege gezeichnet (akos 253 auf ai 17, 251 auf ai 4 zweimal,
2 auf ai 1 zweimal). Summe ueber den Lauf, in Komposit-Pixeln (2560x1920):

```
durchsichtige Kostuem-Punkte          86.463.507
  HD-Hintergrund zurueck              83.858.560   97,0 %
  8 Bit bleibt sichtbar                1.952.627    2,26 %
  HD-Kostuem liegt schon darunter         652.320
```

Das sind je Bild 24.408 Komposit-Punkte, in der Aufnahme (1280x960) 6.102 Punkte, also
**0,50 Prozent des Bildes**. Gemessenes Magenta im gleichen Lauf: Mitte 3,87 Prozent, max 3,92.
Damit stammen **12,8 Prozent** des sichtbaren Magentas aus der Transparenz-Regel; die uebrigen
87 Prozent sind 8-Bit-Punkte, an die kein gezeichnetes HD-Kostuem ueberhaupt heranreicht.

Zusatz aus dem Protokoll: Stufe 2.6b legt je Bild **16.852** 8-Bit-Punkte in Palettenfarben
neu ab (`step2.6b ui-overlay: pixels=16852`). Diese Punkte erscheinen im Magenta-Bild nicht,
sind aber sichtbar. Genau das sind die braunen Stellen: Palettenbraun der 8-Bit-Ebene in
Flaechen, die die HD-Textur durchsichtig laesst.

### Messung nach dem Diagnose-Build

```
Raum 44, magenta_check.py   Bilder 80   Mitte 3,87 %   max 3,89 %
```

Gleich wie vorher (3,87 / 3,89). Die Zaehler aendern das Bild nicht, der Befund ist also nicht
durch die Instrumentierung entstanden.

### Was daraus folgt

- Ein fehlender Alpha-Test ist **widerlegt**: 97 Prozent der durchsichtigen Texturpunkte
  bekommen den HD-Hintergrund, nur 2,26 Prozent behalten 8 Bit.
- Offen bleibt eine Entscheidung, keine Reparatur: die beiden Regeln, die 8 Bit als Fuellung
  nehmen, abschaffen oder einschraenken. Regel 1 ist fuer Raum 89 noetig, Regel 2 fuellt
  UI und Objekte ohne HD-Bild. Beide schreiben echte Palettenfarben, deshalb faellt es als
  Braun auf und nicht als Magenta.
- Moegliche, messbare Einschraenkung von Regel 1: den 8-Bit-Punkt nur stehen lassen, wenn er
  zu einem **anderen** Akteur gehoert als dem, dessen Kostuem gerade gezeichnet wird (Daten
  dafuer liegen vor: Position, Breite, `_top`, `_bottom` je Akteur). Wirkung hoechstens
  0,50 Punkte in Raum 44, Risiko: Loecher in Figuren, deren Koerperteile sich in mehreren
  Eintraegen ueberlappen. Ohne Sichtpruefung nicht eingebaut.

### Dateien

```
Screenshot ohne Marker   projects/comi-hd/reports/vergleich/raum44_hd_aktuell.png
Screenshot markiert      projects/comi-hd/reports/vergleich/raum44_hd_8bit_markiert.png
Protokoll des Laufs      projects/comi-hd/work/raum44_alpha/hd_state_alpha_spy.log
Bildfolge markiert       projects/comi-hd/work/raum44_alpha/tint/ (160 Dateien)
Auswertung               projects/comi-hd/harness/alpha_gegenprobe.py
                         projects/comi-hd/harness/alpha_orte.py
                         projects/comi-hd/harness/alpha_rechteck.py
```

`alpha_rechteck.py` taugt nur als grobe Probe: die Rechtecke der Eintraege sind so gross, dass
sie ein Drittel des Bildes abdecken (43,7 Prozent des Magentas liegt darin, 33,8 Prozent der
Flaeche sind Rechteck). Eine Zuordnung "innen/aussen" ist damit nicht belastbar, deshalb steht
die Aussage oben auf den Zaehlern im Blit, nicht auf den Rechtecken.

## Nachmessung Raum 44: beide Zeichnungen teilen denselben Bezug

Stand nach c45f93df, gemessen am 25.10. um 12:35 mit der ausgelieferten
`release/linux/scummvm` (Binary vom 11:49, `gfx.cpp` seit 133450b2 unveraendert,
HEAD c45f93df bringt nur Doku). Die Aufgabe ging von 46 Spielpixeln Versatz und
3,87 Prozent Magenta aus; das ist der Stand VOR 133450b2. Hier steht, was danach gilt.

Magenta-Anteil aus `harness/magenta_check.py 44`, Mitte der Folge:

```
vor der Kamerakorrektur   3,87 %
Lauf 11:55                0,78 %
dieser Lauf 12:35         0,95 %   (80 Bilder, max 0,95)
```

Die Differenz 0,78 gegen 0,95 ist Bildraster, nicht Zeichnung: die Bildfolge haengt an
der Zahl der Kompositionen, die ausgewerteten Bilder liegen also nicht an derselben
Stelle. Beide Werte liegen weit unter 3,87.

Ortsaufloesung des Rests (tinted Stufenlauf, `harness/magenta_rest_orte.py`):

```
Stand vor der Korrektur (Binary 11:19)                    3,88 %
  Figur, breiter Saum     (344,100)-(400,311)   24.046 px
  zweite Figur            (534,181)-(591,269)   12.270 px
  Randstreifen rechts     (594,141)-(603,371)    9.132 px
  Fuesse                  (542,312)-(587,331)    1.116 px

Stand jetzt (Binary 11:49)                                0,96 %
  Randstreifen rechts     (594,140)-(603,371)    9.172 px
  Fuesse                  (338,292)-(377,311)    2.026 px
```

Der Figurensaum ist weg. Vorher war er 56 Spielpixel breit (344 bis 400), die
8-Bit-Figur stand also sichtbar neben dem HD-Kostuem. Jetzt bleibt am Koerper nichts
und an den Fuessen 0,16 Prozentpunkte (Schattenkante, siehe Abschnitt zum Schatten).

Geometrisch, im selben Lauf gemessen (`harness/versatz_stufen.py`, Stufenbilder 2x):
8-Bit-Figur `(335,100)-(400,311)`, HD-Figur `(335,99)-(399,311)`. Kastenkanten also
0 bis 0,5 Spielpixel auseinander, Schwerpunkt x 367,0 gegen 367,3 (2x) = 0,15
Spielpixel. Der Schwerpunkt y weicht 2,9 Spielpixel ab, weil die HD-Textur eine andere
Massenverteilung hat als die 8-Bit-Silhouette; die Kanten stimmen.

Was uebrig bleibt, ist nicht die Figur: ein 9 Spielpixel breiter, 231 Pixel hoher
Streifen am rechten Bildrand (594 bis 603). Er ist vor und nach der Korrektur gleich
gross (9.132 gegen 9.172 px), war also vorher schon da und gehoert zur Kante der
8-Bit-Vorlage im scrollenden Raum. Offen, eigene Aufgabe.

Gegenprobe `HD_NO_ACTORS=1`: damit fehlt die 8-Bit-Figur, und die Differenz der beiden
8-Bit-Bilder ist die Figurenmaske (17 gemeinsame Bilder, `harness/versatz_raum44.py`).
Sichtbild vorher/nachher: `projects/comi-hd/reports/vergleich/dopplung_raum44.png`
(oben Binary 11:19, darunter Binary 11:49, gleicher Ausschnitt, unten das ganze Bild).
Messlaeufe in `projects/comi-hd/work/raum44_nachmessung/{mit,ohne,tint}`, Werkzeuge
`harness/versatz_raum44_lauf.py`, `harness/dopplung_raum44_bild.py`,
`harness/magenta_rest_orte.py`.


## Schatten unter Guybrush: HD-Flaeche weg, 8-Bit-Rest bleibt

Aufgabe: die braune, strukturlose Schattenflaeche unter Guybrush soll verschwinden, Fuesse
und Figur bleiben. Die Flaeche steckt in der HD-Kostuemtextur selbst (aus der 8-Bit-Vorlage
mit hochskaliert), nicht im Hintergrund.

### Wo die Flaeche herkommt

In der 8-Bit-Vorlage hat der Schatten eine eigene, dunkle, nicht schwarze Farbe:

```
LFLF_0001_AKOS_0002_aframe_*.png   (Roh-Extraktion work/extract-fix4/costumes)
Schattenfarbe  (83,43,43)          Figur (255,199,175)   Hintergrund (0,0,0)
356 von 688 Frames haben die Farbe, 332 sind kleine Cels ohne Schatten
```

Der Schatten ist eine breite, flache Flaeche direkt unter den Fuessen: Breite mindestens
50 Prozent der Figurenbreite, Hoehe hoechstens 30 Prozent des Bildes, mindestens 30 Punkte.
Genau diese Punkte, 4x auf die HD-Groesse gebracht, werden im HD-Bild auf Alpha 0 gesetzt.
Alles andere bleibt unveraendert (Pixelgleichheit ausserhalb der Maske geprueft, RGB
unberuehrt). Im HD-Original deckt sich die Maske 1:1 mit deckenden Pixeln, deren Farbe dort
(153,51,4) ist, Streuung 7: eine flache Flaeche, wie beschrieben.

Werkzeug: `harness/schatten_entfernen.py` (nur Guybrush, LFLF_0001_AKOS_0002), Sicherung
`hd/costumes_backup`, Zwischenstand des verunglueckten Alpha-Experiments vom 25.10. 11:24
in `hd/costumes_defekt_20261025` (dort war die Figur mitgeloescht, 19.072 statt 158.266
deckende Punkte).

### Messung Raum 44 (80 Bilder je Lauf, feste Kamera)

```
HD_JUMP_ROOM=44 HD_FIXED_DELTA=20 HD_EXIT_AFTER=240 HD_DUMP_SEQ=1 ./scummvm \
  --config=scummvm_video.ini --path=game comi
```

Fenster am Fussbereich (Verbundbild 1280x960: y 584 bis 622, x 676 bis 794):

```
                                   vorher              nachher
Bilder mit flacher Flaeche >=500 px   65 von 80           0 von 80
Schattenfarbe je Bild (Mittel)        2218 px             7 px
8-Bit-Anteil im Fenster               0,1 %               36,9 %
```

Die flache braune Flaeche ist damit in allen Bildern weg, die Fuesse sind unveraendert
(Sichtpruefung und Pixelvergleich). Bild:
`projects/comi-hd/reports/vergleich/schatten_guybrush.png`.

### Was offen bleibt: die 8-Bit-Ebene malt den Schatten weiter

Nach dem Entfernen fuellt die 8-Bit-Ebene die Stelle: 36,9 Prozent des Fensters sind wieder
8-Bit, sichtbar als grober, karierter Flicken (vorher 0,1 Prozent). Ursache gemessen mit
`HD_ALPHA_SPY=1`:

```
ALPHASPY ai=1 akos=2 cel=22 schatten=3 a0=80286 a0bg=69781 a0keep8=9444 a0hd=1061
```

Von 15.296 Schattenpunkten der Textur bleiben 9.444 stehen (`a0keep8`), weil im Zweig
`alpha == 0` die Pruefung `foregroundBelow` die 8-Bit-Fassung **derselben** Figur als
schutzwerten Vordergrund wertet (gfx.cpp, alpha==0-Zweig, Regel fuer Raum 89). Diese Regel
ist fuer ein anderes HD-Kostuem gedacht, nicht fuer die eigene Figur.

Zwei Wege, beide noch nicht eingebaut:

1. **Regel einschraenken:** den 8-Bit-Punkt nur stehen lassen, wenn er zu einem anderen
   Akteur gehoert. Risiko: Loecher in Figuren, deren HD-Textur innen durchsichtig ist
   (bei akos 438 sind das 30 Prozent der Silhouette).
2. **Marke im Asset:** Alpha 0 plus RGB 255,0,255 heisst "bewusst entfernt, immer
   HD-Hintergrund zeigen", und der alpha==0-Zweig ueberspringt fuer diese Punkte die
   foregroundBelow-Pruefung. Gebaut und wieder zurueckgenommen: der Linux-Build dieser
   Umgebung kann nicht linken, weil libXcursor und libXss fehlen (`-lXcursor`, `-lXss`;
   die Ersatzverweise liegen in `build/x11link`, fuer die beiden fehlt die Bibliothek
   auf dem System). Der Code-Aenderung fehlt damit der Nachweis am laufenden Bild.

Bis dahin gilt: die HD-Schattenflaeche ist weg, der Rest an dieser Stelle ist der
8-Bit-Anteil, den auch die Dopplungen verursachen (eigene Aufgabe).

Dateien:

```
Aufnahmen vorher/nachher     projects/comi-hd/work/raum44_schatten/{vorher,nachher}
8-Bit-Anteil vorher/nachher  projects/comi-hd/work/raum44_schatten/{vorher_tint,nachher_tint}
Zaehler im Blit              projects/comi-hd/work/raum44_schatten/nachher_spy/hd_state.log
Messung                      /opt/data/kanban/workspaces/t_778e21be/endmessung.json
```

Hinweis zu den Kopien: der Messlauf liest `release/linux/hd`, die kanonische Ablage ist
`hd/costumes` (Symlink auf `scummvm/fork/hd`). Beide sind aktualisiert. Die Kopie
`game/hd` und der Windows-Satz enthalten weiterhin die alten Bilder.

## Weisser Saum an den Texturen: im PNG vorhanden, im Spiel nur ueber den Vorwaerm-Pfad

Aufgabe: pruefen, ob die HD-Texturen einen weissen RGB-Saum an den Alphagrenzen tragen, und
ihn entfernen. Ergebnis vorweg: die Texturen tragen ihn (7.507 von 25.302 Kostuemframes),
die Engine entfernt ihn beim Einzelladen auch schon, aber der Pfad, der die Texturen beim
Raumwechsel vorwaermt, hat die Bereinigung uebersprungen. Diese Luecke ist geschlossen.

### Befund im Testrahmen

```
hd/costumes/LFLF_0001_AKOS_0002_aframe_10.png   (316x848, Guybrush)
Alpha-Verteilung   a=0 123.698 | 1-31 5.060 | 32-80 1.415 | 81-254 11.676 | 255 126.119
a=0        RGB-Mittel  10/ 5/ 5   fast weiss (min>=190)  0,0 %
0<a<=80    RGB-Mittel   2/ 1/ 0   fast weiss             0,0 %
Rand (a>0 mit Nachbar a<32) 9.443 px                     0,0 %
haeufigste Farbe der durchsichtigen Punkte  (0,0,0), danach die Schattenfarbe (83,43,43)
```

An genau diesem Rahmen gibt es also keinen weissen Saum: die Extraktion hat den Hintergrund
dort auf Schwarz gesetzt (und der Schattenfix vom 25.10. hat die Schattenfarbe auf Alpha 0
gelegt). Ein weisser Saum kann aus dieser Textur nicht kommen.

### Befund ueber alle Kostuemframes

```
harness/saum_scan_schnell.py, 25.302 Dateien in hd/costumes
Frames mit mehr als 50 weissen Saumpixeln     7.507  (29,7 %)
weisse Saumpixel roh                          39.725.828
Spitzenreiter  LFLF_0013_AKOS_0063_aframe_57    171.468
```

Wo der Saum sitzt, ist der Hintergrund der Datei weiss (254,254,254) und der Ring um die
Figur ebenfalls weiss: der Upscaler hat gegen Weiss freigestellt und den Rand mitgemischt.
Beispiel LFLF_0011_AKOS_0051_aframe_0: 36.998 Randpixel, davon 97,8 % fast weiss, die
durchsichtigen Punkte sind zu 100 % weiss.

### Was die Engine schon tut

`removeWhiteFringe()` (`hd_fringe.h`) loescht fast weisse Punkte am Rand (alle Kanaele >=190,
Nachbar mit Alpha <32, zehn Durchgaenge) und laeuft an zwei Stellen: `hd_object_manager.cpp:119`
und `hd_costume_manager.cpp:181`, jeweils in `loadPNG()`. Zusaetzlich schliesst
`hdFillAlphaHoles()` Loecher in der Deckkraft (Objekte in `loadPNG`, Kostueme in
`loadCostume`).

### Die Luecke: der parallele Decoder

`hd_batch_decode.h` (Issue #14, Vorwaermen beim Raumwechsel) dekodiert nur PNG nach RGBA.
`preloadCostumeRange()` (`hd_costume_manager.cpp:306`) und `preloadRoom()`
(`hd_object_manager.cpp:442`) schrieben diese Rohflaechen direkt in den Texturspeicher, und
der Zeichenweg nimmt Cache-Treffer ungeprueft (`gfx.cpp:2839`, `loadCostume` liefert bei
Treffer den Zeiger auf den Cache-Eintrag). Damit wurden die vorgewaermten Frames mit weissem
Saum und mit offenen Alpha-Loechern gezeichnet, waehrend derselbe Frame nach einem
Einzelladen sauber war.

Fix (beide Stellen, gleiche Reihenfolge wie in `loadPNG`):

```cpp
removeWhiteFringe(jobs[i].surface);
hdFillAlphaHoles(jobs[i].surface, 3);
```

### Messung im Spiel: alte gegen neue Binary

Je Raum ein Verbundbild an derselben Stelle, `HD_JUMP_ROOM=<raum> HD_DUMP_STEPS=1
HD_DUMP_AT=60`, gezaehlt werden geaenderte Pixel und davon die vorher fast weissen
(`harness/saum_schritte_vergleich.py`):

```
Raum   Stufe                 geaendert   davon vorher fast weiss
44     Hintergrund                  0              0
44     Objekte                    108              0
44     Kostueme                   552             10
13     alle Stufen                  0              0
30     Vordergrund/Objekte/Kostueme 524           336
```

In Raum 30 verschwindet damit ein heller Rand an einer Figur, die aus der Objektschicht
kommt; in Raum 44 sind es 552 Punkte, davon nur 10 fast weiss (dort vor allem geschlossene
Alpha-Loecher). Raum 13 zeigt keinen Unterschied, weil die dort gezeichneten Frames schon
vorher sauber geladen wurden. Die Kostuemframes selbst waren in allen drei Raeumen bereits
durch `loadPNG` bereinigt; der sichtbare Unterschied kommt aus dem Vorwaerm-Pfad.

Bilder:

```
Vorher/Nachher Kopf (Raum 44)  projects/comi-hd/reports/vergleich/weisser_saum_vorher_nachher.png
Vorher/Nachher Figur (Raum 30) projects/comi-hd/reports/vergleich/weisser_saum_raum30_vorher_nachher.png
Screenshot Raum 44             projects/comi-hd/reports/vergleich/raum44_nachher.png
Rohdaten je Frame              projects/comi-hd/reports/weisser-saum/scan_kostueme.csv
Aufnahmen                      projects/comi-hd/work/saum/raum{44,13,30}_{vorher,nachher}
```

### Was offen bleibt

1. Raum 44 zeigt an seinem Testrahmen keinen weissen Saum. Wenn dort einer zu sehen war,
   kam er nicht aus dieser Textur. Sicher belegt ist der Saum fuer die 7.507 betroffenen
   Frames und seine Entfernung an der Figur in Raum 30.
2. Nach dem Filter bleibt in einer Stichprobe von 150 betroffenen Frames rechnerisch
   13,3 Prozent der weissen Randpunkte stehen (roh 691.229, danach 92.237). Die Messgroesse
   ueberschaetzt den Rest, weil das Loeschen der Randpunkte neue Nachbarschaft zu Weiss
   schafft (Hemd, Haut, Segel werden mitgezaehlt); in Einzelfaellen steigt die Zahl dadurch
   ueber den Rohwert. Nicht angefasst: eine Farbangleichung an deckende Nachbarn wuerde
   echte weisse Motivteile falsch einfaerben.
3. Die Ladezeitwirkung des zusaetzlichen Durchlaufs beim Vorwaermen ist nicht gemessen.
4. `HD_JUMP_ROOM` liefert nur fuer die Raeume 44, 13 und 30 Bilder; 11, 21, 16, 82, 9 und 51
   blieben leer, dort ist keine Messung moeglich.

### Build-Hinweis

Der Linux-Build in dieser Umgebung linkt nur mit der SDL2-Variante ohne X11 und mit dem
SONAME der ALSA-Bibliothek, weil die Entwicklungsverweise fuer Xcursor, Xss und asound
fehlen. In `scummvm/fork/config.mk` steht deshalb in `LIBS`:

```
-L.../build/install/sdl2-native.nox11/lib -Wl,-Bstatic -lSDL2 -Wl,-Bdynamic -l:libasound.so.2 ...
```

## Dopplung bei anderen Figuren: vier Raeume gemessen, ein Zeichenweg

Auftrag war die Beobachtung, der Kamerafix (133450b2) wirke nur bei Guybrush, andere
Kostueme seien weiterhin gedoppelt oder falsch platziert. Gemessen wurde deshalb je Raum
und je Akteur der Versatz zwischen der 8-Bit-Silhouette und der HD-Flaeche, zusaetzlich
welchen Zeichenweg der Akteur nimmt.

### Messplatz

Ein Lauf je Raum mit der eigenen Binary-Kopie (`work/engine/scummvm-d67`, Aufnahmepfade
auf `d67*` umgeschrieben, damit parallel laufende Aufgaben im selben Verzeichnis die
Bilder nicht ueberschreiben, Werkzeug `harness/dopplung_binary.py`):

```
HD_JUMP_ROOM=<raum> HD_FIXED_DELTA=20 HD_EXIT_AFTER=120 HD_DUMP_STEPS=1
HD_TRACE_DRAW=1 HD_TINT_8BIT=1
```

Der feste Zeitschritt macht das Bild reproduzierbar, die Stufendumps liefern in einem
Lauf Hintergrund (Stufe 1), eingefärbten 8-Bit-Vordergrund (Stufe 2), Objekte
(Stufe 3) und Kostueme (Stufe 4). Ausgewertet mit `harness/dopplung_auswertung.py`
(Kaesten und Deckung je Akteur), `harness/dopplung_versatz_je_akteur.py` (bester Versatz
per Kreuzkorrelation) und `harness/dopplung_spiegel.py` (welcher Anker zum HD-Kasten
passt). Sichtblaetter: `projects/comi-hd/reports/vergleich/dopplung_akteure_raum{9,15,44,86}.png`
(drei Felder: 8-Bit eingefaerbt, HD-Kostueme mit Kaesten der Eintraege, Ueberlagerung).

### Ergebnis je Eintrag

Versatz in Spielpixeln, bester Wert der Kreuzkorrelation der HD-Flaeche gegen die
8-Bit-Silhouette; in Klammern die Deckung an dieser Stelle (Anteil der
8-Bit-Silhouette, den die HD-Flaeche abdeckt).

```
Raum 9   (F=239, Kamera 0)
  ai= 1  akos 0002  gliedmassen  cel34   dx  0     dy +1     (0,98)
  ai= 1  akos 0002  gliedmassen  cel22   dx +0,5   dy +0,5   (0,99)
  ai= 2  akos 0025  gliedmassen  cel3    dx  0     dy  0     (0,98)
  ai= 2  akos 0025  gliedmassen  cel5    dx  0     dy  0     (0,98)
  ai=12  akos 0026  komplett     cel0    dx  0     dy  0     (0,96)

Raum 44  (F=119, Kamera 0)
  ai= 1  akos 0002  gliedmassen  cel34   dx +0,5   dy +1     (0,96)
  ai= 1  akos 0002  gliedmassen  cel22   dx +0,5   dy  0     (0,93)
  ai= 4  akos 0251  gliedmassen  cel8    dx  0     dy +2     (0,98)
  ai= 4  akos 0251  gliedmassen  cel11   dx +44    dy  0     (0,45) nicht belastbar
  ai=17  akos 0253  komplett     cel15   dx  0     dy  0     (1,00)

Raum 15  (F=119, Kamera 0)
  ai= 1  akos 0002  gliedmassen  cel22   dx +1     dy  0     (1,00) stark verkleinert
  ai= 1  akos 0002  gliedmassen  cel34   dx +1     dy  0     (1,00) stark verkleinert
  ai= 4  akos 0075  komplett     cel10   dx  0     dy  0     (1,00)
  ai=17  akos 0083  komplett     cel15   dx  0     dy  0     (0,99)

Raum 86  (F=119, Kamera 0)
  ai= 1  akos 0399  gliedmassen  cel13   dx +1     dy  0     (0,38) nicht belastbar
  ai= 1  akos 0399  gliedmassen  cel31   dx +0,5   dy  0     (0,98)
  ai= 3  akos 0424  komplett     cel18   dx  0     dy  0     (0,95)
  ai= 4  akos 0426  komplett     cel0    dx  0     dy  0     (1,00)
  ai= 5  akos 0012  komplett     cel2    dx  0     dy  0     (0,87)
  ai=19  akos 0437  Rueckfall cel0       kein Gegenstueck im 8-Bit-Bild, siehe Befund a
  ai=20  akos 0438  komplett     cel0    dx  0     dy  0     (0,90)
```

20 gueltige Eintraege: 18 liegen bei 0 bis 1 Spielpixel in x und y, einer bei 2 Pixeln,
einer ist nicht belastbar (sein Fenster enthaelt die Silhouette des Nachbarn, daher der
Ausreisser dx +44 bei nur 0,45 Deckung). Dieselbe Spanne gilt fuer die beiden nicht
belastbaren Eintraege in x. Ein raum- oder figurenabhaengiger Unterschied ist nicht
vorhanden: Guybrush (0002) verhaelt sich wie 0025, 0026, 0251, 0075, 0399, 0424, 0426,
0437, 0438 und 0012, und die Starkverkleinerung in Raum 15 (Blit 13x33 HD-Punkte aus
232x376, rund 5 Prozent) aendert nur 1 Spielpixel.

Ein gespiegelter Eintrag kam in diesen Bildern nicht vor: bei allen Eintraegen liegt die
linke Kante der HD-Flaeche exakt auf dem Anker fuer ungespiegelt (Abweichung 0,
`harness/dopplung_spiegel.py`). Der Spiegelzweig ist mit dieser Messung also weder belegt
noch widerlegt.

### Welchen Zeichenweg nehmen die anderen Figuren

Alle Akteure laufen durch dieselbe Schleife in `renderHDComposite` (Schritt 2.6,
`gfx.cpp:2660` bis `gfx.cpp:3095`). Es gibt keinen zweiten Zeichenweg fuer einzelne
Kostueme oder Raeume, sondern zwei Unterfaelle, die je Akteur und Bild aus den
AKOS-Daten entschieden werden:

- **komplett:** alle Gliedmassen zeigen auf dasselbe Cel (`sameCel`, `gfx.cpp:2733`).
  Dann genau ein Eintrag an der Position `pos.x + relX` (`gfx.cpp:2744` bis `2755`).
- **gliedmassen:** verschiedene Cels, je Gliedmass ein Eintrag an der aufgelaufenen
  Position aus dem AKOS-Kopf (`gfx.cpp:2756` bis `2776`).
- **Rueckfall auf Cel 0** (`gfx.cpp:2778` bis `2794`): kein Gliedmass gefunden, das
  Kostuem existiert aber. Dann wird Cel 0 an `_hdRelX` gezeichnet.

Die Zeichenposition ist in beiden Unterfaellen dieselbe Rechnung (`gfx.cpp:2932`):
`hdCX = (pos.x + drawX * sclX / 255) * hdW / visW`, gespiegelte Figuren zusaetzlich um
die Blitbreite nach links versetzt (`gfx.cpp:2947`). HD-Objekte (Schritt 2.5) sind an
diesen Stellen nicht im Spiel: in allen vier Raeumen ist die Differenz Stufe 3 gegen
Stufe 2 null. Figuren, die als Raumobjekt gezeichnet werden, gibt es dort also nicht.

### Zwei Befunde, die wie eine Dopplung aussehen, aber keine Position sind

**a) Der Rueckfall auf Cel 0 zeichnet ein Kostuem, das die 8-Bit-Ebene nicht zeichnet.**
Raum 86, `ai=19`, `akos 0437`: das HD-Bild wird mit 72x60 HD-Punkten (18x15 Spielpixel)
bei Spielpixel (552,240) gezeichnet; die 8-Bit-Silhouette hat dort 48 Punkte, die
HD-Flaeche 614. Ein Bruchstueck ohne Gegenstueck im 8-Bit-Bild. Ursache ist der
Rueckfall oben, wenn ein sichtbarer Akteur mit Kostuem in diesem Bild von AKOS gar nicht
gezeichnet wurde.

**b) Durchsichtige Ueberlagerungskostueme vergroessern die gemessene HD-Flaeche.**
`akos 0253` (Raum 44) und `akos 0083` (Raum 15) sind je 896x1388 HD-Punkte gross, also
224x347 Spielpixel, und dabei zu 1 Prozent deckend und zu 7 bis 10 Prozent
halbtransparent (`harness/kostuem_png_info.py`). Im Bild aendern sie ueber die ganze
Flaeche Pixel, deshalb zaehlt die Differenz Stufe 4 gegen Stufe 3 dort 17.000 Punkte,
waehrend die 8-Bit-Silhouette nur 3.000 bis 7.800 hat. Das ist keine zweite Figur,
sondern eine kaum sichtbare Flaeche, die der Diff-Schwellwert mitnimmt.

### Ein Code-Befund, der ausserhalb dieser Raeume wirkt

Die 8-Bit-Ebene zeichnet ein Kostuem nach Pufferkoordinaten:
`bcr->_actorX = _pos.x - _vm->_virtscr[kMainVirtScreen].xstart` (`actor.cpp:2664`,
zweite Stelle `actor.cpp:2671`). Der Komposit liest die Pufferspalte 1:1
(`hdXStart[sx] = sx * hdW / visW`; der Kameraversatz steckt in Schritt 1, also in der
Hintergrundkopie). Damit die HD-Flaeche deckungsgleich liegt, muss sie denselben
Fensteranfang abziehen. Der HD-Pfad tut das seit 133450b2 nicht mehr (`gfx.cpp:2932`,
Kommentar `gfx.cpp:2922` bis `2931`).

Beides ist nur gleich, solange `vs->xstart == 0` ist. Genau dieser Fall lag in Raum 44
vor: dort stand `hdWindowLeft()` (aus der Kamera) auf 46, waehrend der Puffer mit
`xstart = 0` lief; das Abziehen dieses Werts setzte die Figur 46 Spielpixel nach links,
das Weglassen ist dort richtig. In Bildern mit laufendem Fenster (`xstart != 0`) fehlt
die Subtraktion dagegen, und die Figur sitzt um `xstart` Spielpixel zu weit rechts. Die
richtige Groesse ist deshalb nicht `hdWindowLeft()`, sondern `vs->xstart`, also genau
das, was die 8-Bit-Ebene selbst benutzt.

Nachgewiesen ist dieser Fall hier nicht. Ein Sprunglauf landet mit `xstart = 0`; die
erzwungene Kamerafahrt (`HD_SCROLL_TEST`) ergibt einen Zustand, in dem der Fensteranfang
der Komposition und der des 8-Bit-Puffers auseinanderlaufen (Raum 15, F=159:
`xstart = 368`, danach gelten 43 Prozent des Bildes als 8-Bit-Vordergrund, die
Vordergrundpruefung erkennt also das halbe Bild falsch) — dieser Zustand ist kuenstlich
und taugt nicht als Beleg. Der FIFO-Weg (`walk`, `JEV_CMD_FIFO`) hat den Ego nicht in
Bewegung gesetzt (0 von 4 Kommandos ausgefuehrt, `r15w`). Eine Messung mit echtem
Scrollen bleibt offen und gehoert zur Aufgabe "Positionierung raum- und
figurenunabhaengig".

### Grenzen dieser Messung

- **Raum 3 ist so nicht messbar.** Der Sprung landet wieder in Raum 87 (Intro), im
  Protokoll steht `room=0x480` und `xstart=65276`, und die 8-Bit-Ebene hat null
  Vordergrundpunkte. Raum 3 ist der Startbildschirm, kein normaler Raum.
- **Gespiegelte Figuren** kommen in den vier Aufnahmen nicht vor (siehe oben).
- **Bewegte Figuren** sind nicht gemessen; die Stufendumps schreiben nur das letzte Bild
  eines Laufs.
- Die Deckungszahl ist bei Eintraegen, deren Fenster den Nachbarn mitfasst, zu niedrig
  (0,38 und 0,45 oben) und taugt dort nicht als Fehlergroesse; der Versatz ist in diesen
  Faellen ebenfalls nicht belastbar und als solcher gekennzeichnet.

### Was daraus folgt

Kein Fix an der Zeichenposition fuer diese vier Raeume: es gibt dort nichts zu
verbessern, der Versatz liegt schon bei 0 bis 2 Spielpixeln, und die Karte verlangt einen
Commit nur bei belegter Verbesserung. Der offene Kameraterm ist oben benannt und gehoert
in die Positionierungsaufgabe, nicht in diese. Der Rueckfall auf Cel 0 (Befund a) ist ein
Kandidat fuer eine eigene Aenderung: den Rueckfall nur zeichnen, wenn der Akteur in
diesem Bild wirklich von AKOS gezeichnet wurde. Ohne Sichtpruefung nicht eingebaut, weil
der Rueckfall fuer andere Faelle gedacht ist.

### Dateien

```
Messlaeufe            projects/comi-hd/work/dopplung/r{9,15,44,86}/
                      projects/comi-hd/work/dopplung/r15s (Kamerafahrt), r15w (FIFO-Walk)
Binary-Kopie          projects/comi-hd/work/engine/scummvm-d67
Sichtblaetter         projects/comi-hd/reports/vergleich/dopplung_akteure_raum{9,15,44,86}.png
Werkzeuge             projects/comi-hd/harness/dopplung_lauf.sh
                      projects/comi-hd/harness/dopplung_lauf_walk.sh
                      projects/comi-hd/harness/dopplung_auswertung.py
                      projects/comi-hd/harness/dopplung_versatz_je_akteur.py
                      projects/comi-hd/harness/dopplung_spiegel.py
                      projects/comi-hd/harness/dopplung_karte.py
                      projects/comi-hd/harness/dopplung_sichtblatt.py
                      projects/comi-hd/harness/dopplung_binary.py
                      projects/comi-hd/harness/kostuem_png_info.py
```

### Nachtrag: der Rueckfall auf Cel 0 ist am Akteur belegt, und `cel <= 0` filtert einen gueltigen Cel

Ein zweiter Lauf in Raum 86 mit `HD_SPY=1` (Ordner `work/dopplung/r86spy`, Protokoll
`work/dumps/d67_actor_prob.log`, Auswertung `harness/dopplung_akteurprobe.py`) schreibt je
Bild eine Zeile pro Akteur. Fuer `ai=19` steht in allen 120 Bildern:

```
AKTEUR ai=19 akos=437 sichtbar=1 schatten=3 limbs=0 cel0=0 cel1=0
```

Der Akteur ist also sichtbar und hat ein Kostuem, AKOS zeichnet ihn aber nie (kein
Gliedmass), und der HD-Pfad faellt deshalb auf Cel 0 zurueck. Die 8-Bit-Ebene zeichnet an
dieser Stelle nichts (Befund a oben), das HD-Bild schon. Damit ist die Ursache belegt und
nicht nur aus dem Code abgeleitet.

Beim Nachsehen faellt eine zweite Stelle auf: der Gliedmassen-Zweig ueberspringt Cels mit
`if (cel <= 0) continue;` (`gfx.cpp:2760`). Der Cel-Index 0 ist aber gueltig, der Rueckfall
zeichnet ihn selbst. Akteure, deren Gliedmassen alle auf Cel 0 zeigen, laufen deshalb
nicht durch den Gliedmassen-Zweig, sondern durch den Rueckfall, und werden mit genau
einem Bild gezeichnet. In Raum 86 betrifft das `ai=4` (`limbs=1 cel0=0`) und `ai=20`
(`limbs=1 cel0=0`), in Raum 9 `ai=12`. Bei allen dreien liegt der HD-Kasten trotzdem
deckungsgleich (dx 0, dy 0), der Rueckfall zeichnet also an der richtigen Stelle; der
Unterschied liegt nur in der Zahl der Eintraege, nicht in der Lage.

Was daraus folgt, unveraendert: den Rueckfall nur zeichnen, wenn der Akteur in diesem Bild
wirklich von AKOS gezeichnet wurde (dann bleibt das Bruchstueck aus Raum 86 weg), und den
Cel-Index 0 im Gliedmassen-Zweig zulassen (`cel < 0` statt `cel <= 0`). Beides ist eine
Code-Aenderung ohne Messung am Bild und deshalb hier nicht eingebaut; sie gehoert in eine
eigene Aufgabe mit Sichtpruefung.

## Gegenpruefung (comi-pruef, 25.10.): Kriterium 2 nicht belegt

Pruefung des Nachweises oben gegen die drei Kriterien der Karte `t_ff786911`. Ergebnis
vorweg: die Code-Aenderung ist plausibel und am Objektpfad belegt, die Sichtpruefung an
Figuren fehlt. Die Karte geht zurueck an comi-bau.

### Kriterium 1, weisse Randpixel je geprueftem Frame

Rohdaten nachgezaehlt (`reports/weisser-saum/scan_kostueme.csv`): 25.302 Frames, davon
7.507 mit mehr als 50 weissen Saumpixeln, Summe roh 39.725.828. Deckt sich mit dem Bericht.

Stichprobe der 150 betroffenen Frames (seed 7) unabhaengig nachgerechnet, Ergebnis je Frame
in `reports/weisser-saum/pruef_frames_150.csv`:

```
Saumpixel roh 691.229  -> nach Filter 92.237     13,3 %
Frames ohne Rest                                  3 von 150
Frames mit Rest > 500                            29
Frames, in denen die Zahl nicht sinkt            77
```

Die Kennzahl des Berichts zaehlt jeden fast weissen Punkt im Umkreis von drei Pixeln um
Transparenz. Deshalb sinkt sie in 77 von 150 Frames gar nicht: das Loeschen legt die
naechste Reihe frei. Eine zweite, engere Kennzahl wurde mitgemessen, naemlich fast weisser
Punkt mit direktem Nachbarn alpha == 0, also die im Bild tatsaechlich an der Kante
sichtbare Reihe:

```
Saumkante roh 297.180  -> nach Filter 12.244     4,1 %
Frames mit Saumkante 0 nachher                   67 von 150
Frames mit Rest > 20                             35
```

Damit ist die Wirkung des Filters an der Kante belegt: 95,9 Prozent der sichtbaren weissen
Randpunkte verschwinden. Die Karte verlangt die Zahl je Frame, und in dieser Form liegt sie
im Bericht nicht vor. Nachgemessen gilt "deutlich reduziert oder null" nicht fuer jeden
Frame: 83 von 150 Frames behalten eine Saumkante, 35 davon mehr als 20 Punkte.

### Kriterium 2, Sichtpruefung an drei Figuren in zwei Raeumen

Nicht erfuellt. Auswertung der Stufendumps der drei Raeume mit Aufnahmen
(`harness/saum_schritte_vergleich.py`, hier wiederholt):

```
Raum   Stufe      geaendert   davon vorher fast weiss
44     Kostueme        552              10
30     Vordergrund     524             336
13     alle Stufen       0               0
```

Die 336 fast weissen Punkte in Raum 30 liegen in drei Flecken im oberen Bildbereich
(x 330 bis 353, y 0 bis 39; x 690 bis 713, y 0 bis 19; x 440 bis 455, y 2 bis 17). Im Bild
sind das die Kerzen auf dem haengenden Holzleuchter, also ein Raumobjekt. Die beiden
Figuren des Raums, Guybrush oben links und die gruene Figur in der Mitte, aendern sich
nicht. Der Satz im Bericht, dort verschwinde ein heller Rand "an einer Figur, die aus der
Objektschicht kommt", ist damit falsch: es ist ein Objekt, keine Figur.

In Raum 44 aendern sich 552 Punkte, davon 10 fast weiss. Der Bericht sagt selbst, dass der
Testrahmen dort keinen weissen Saum traegt. Raum 13 zeigt ueber alle Stufen null
Differenz.

Ergebnis: keine einzige Figur mit belegtem weissem Rand vorher und sauberer Kante nachher.
Verlangt sind drei Figuren in zwei Raeumen an Haaren, Haenden und Kleidungskanten.

### Kriterium 3, Vorher-Nachher-Ausschnitt als PNG

Die Dateien sind vorhanden:

```
reports/vergleich/weisser_saum_vorher_nachher.png       Raum 44, Kopf
reports/vergleich/weisser_saum_raum30_vorher_nachher.png Raum 30, Objekt
reports/vergleich/weisser_saum_raum13_vorher_nachher.png Raum 13
```

Nur das Bild aus Raum 30 zeigt einen Unterschied, und dort an einem Objekt. Die beiden
anderen Blaetter zeigen denselben Bildinhalt ohne sichtbare Aenderung, taugen also nicht
als Nachweis. Keines der drei Blaetter nennt Frame oder Kameraposition, der gezeigte
Unterschied laesst sich damit keinem Messlauf zuordnen. Fuer Raum 44 liegt nur ein
gemessener Frame vor, und der unterscheidet sich in 10 fast weissen Punkten.

### Was fuer die Freigabe fehlt

1. Zahl der weissen Randpixel je Frame vorher und nachher als Tabelle, nicht nur als Summe
   ueber 150 Frames. Die Datei `reports/weisser-saum/pruef_frames_150.csv` ist ein Anfang,
   sie deckt aber nur die Textur, nicht das gezeichnete Bild.
2. Drei Figuren in zwei Raeumen, je ein Ausschnitt an Haaren, Haenden und Kleidungskanten,
   vorher mit sichtbarem weissem Rand und nachher ohne. Die Figuren in Raum 30 und 44
   reichen dafuer, es fehlt die Aufnahme an einer Stelle, an der die HD-Textur die Figur
   ueberhaupt ueber einen Vorwaermtreffer zeichnet.
3. Die Raeume mit dem groessten Saum fehlen in der Messung: `LFLF_0013_AKOS_0063` (158.972
   rohe Saumpunkte), `LFLF_0011_AKOS_0051` (36.998), `LFLF_0035_AKOS_0192`. Fuer Raum 11
   gibt es gar keine Aufnahme, in Raum 13 landete ein anderes Kostuem im Bild.
4. Der Satz zur Figur aus der Objektschicht in Raum 30 ist zu berichtigen, die geaenderten
   Punkte sitzen auf dem Kerzenleuchter.

Eigene Aufnahmen der Gegenprobe:

```
reports/vergleich/saum30_vollbild_markiert.png   Raum 30, Saumstellen rot markiert
reports/vergleich/saum30_oben.png                Raum 30, Ausschnitt 4x vorher/nachher
reports/vergleich/saum44_vollbild_markiert.png   Raum 44, Saumstellen rot markiert
reports/vergleich/saum44_alle_figuren.png        Raum 44, Figur 4x vorher/nachher
```

## Objekt-Pfad Raum 44: kein HD-Objekt vorhanden, Kameraversatz beim Zeichnen richtig

Auftrag war zu pruefen, ob der Objektpfad denselben Fehler traegt wie die Kostueme, also den
Kameraversatz abzieht, obwohl das Komposit spaltengenau kopiert. Ergebnis vorweg: in Raum 44
zeichnet der Objektschritt gar nichts, weil es fuer die drei Raumobjekte keine HD-Textur gibt.
Der Abzug im Objektpfad ist gemessen richtig. Gefunden wurde ein anderer Fehler derselben
Klasse: die Sichtbarkeitspruefung fuer Objekte liest Raumspalten, wo Pufferspalten noetig
sind, und verwirft dadurch in scrollenden Raeumen HD-Objekte.

### Was Raum 44 an Objekten hat

```
ROOM OBJ, Raum 44 (hd_state.log)
obj 848  pos=(0,0)      sz=248x503
obj 849  pos=(600,168)  sz=352x304
obj 850  pos=(512,168)  sz=88x144
```

Keine HD-Textur fuer diese drei: `hd/object_map.json` hat 560 Eintraege, keiner nennt Raum 44,
und `hd/objects` enthaelt keine Datei mit Praefix `0044`. Folge im Objektschritt:

```
step2.5 objects: loaded=0 skipped=0 culled=1     (das eine ist das Inventarobjekt)
Stufe 3 gegen Stufe 2: 0 von 307.200 Punkten verschieden, maximale Differenz 0
```

Der Objektschritt schreibt in Raum 44 kein einziges Pixel, eine falsche Lage aus diesem Pfad
kann dort also nicht entstehen. Magenta-Anteil Raum 44 (HD_TINT_8BIT, feste Kamera, drei
Messpunkte im Lauf): 0,95 / 0,95 / 0,95 Prozent.

### Kamerafenster gemessen: Komposit beginnt bei Raumspalte 46, der 8-Bit-Puffer bei 0

Sonde `HD_OFFSET_PROBE` in `renderHDComposite` (Umgebungsvariable, nach der Messung wieder
entfernt): fuer jeden fuenften Punkt wird die Palettenfarbe des 8-Bit-Puffers mit dem
HD-Hintergrund an derselben Spalte und an Spalte plus Kameraversatz verglichen. Raum 44,
sdLeft=46, xstart=46, _screenStartStrip=5, 11.844 Stichproben je Bild:

```
F=59   ohne Kameraversatz 10.061 Treffer   mit Kameraversatz 3.795
F=99   ohne 10.062                         mit 3.797
F=139  ohne 10.074                         mit 3.798
F=199  ohne 10.060                         mit 3.796
```

85 gegen 32 Prozent: die 8-Bit-Spalte sx zeigt denselben Rauminhalt wie die HD-Spalte sx,
nicht wie sx+46.

Vorlagenabgleich (sechs Ausschnitte aus `hd/backgrounds/0044_armsdlr.png`, Graustufen-NCC):
jede Vorlage liegt im 8-Bit-Bild auf ihrer eigenen Raumspalte (40->40, 150->150, 300->300,
420->420, 520->520, 600->600, NCC 0,81 bis 0,99), im Komposit dagegen 46 Spalten tiefer
(150->104, 300->254, 420->374, 520->474, 600->554, NCC 0,99 bis 1,00). Damit ist beides
gemessen: Kompositspalte c zeigt Raumspalte c+46, Pufferspalte c zeigt Raumspalte c. Das
Fenster im HD-Hintergrund ist richtig, und die 8-Bit-Ebene wird in Schritt 2 um eine
Kamerabreite zu weit rechts eingeklebt: waagerecht wird `vs->getBasePtr(0, ...)` gelesen,
senkrecht dagegen korrekt `sy + sdTop`.

### Der Abzug im Objektpfad ist richtig

Objekte werden mit `xPos = od.x_pos - sdLeft` gezeichnet (gfx.cpp, Objektschritt), Figuren
seit 133450b2 mit `actorPos.x` ohne Abzug. Mit dem gemessenen Fenster (Komposit beginnt bei
Raumspalte 46) sitzt ein HD-Objekt an Kompositspalte x-46 auf Raumspalte x, also dort, wo der
HD-Hintergrund denselben Inhalt zeigt. Gegenprobe in Raum 61 (Hotelbar, Kamera per
HD_SCROLL_TEST auf 56): die beiden gezeichneten HD-Objekte `hotelbar-hand` (obj 1005,
pos 424,240) und `hotelbar-glass` (obj 1006, pos 380,248) ergeben gegenueber dem
HD-Hintergrund null veraenderte Punkte (Stufe 2 gegen Stufe 3: 0 von 307.200, maximale
Differenz 0). Sie liegen pixelgenau auf ihrer eigenen Darstellung im Hintergrund.
Abzug entfernt (`xPos = od.x_pos`, Testbau): dieselbe Szene zeichnet 0 Objekte
(`loaded=0 culled=14`). Das ist kein Beleg fuer eine bessere Lage, sondern ein Ausfall.

### Gefundener Fehler: Sichtbarkeitspruefung liest Raumspalten statt Pufferspalten

Die beiden Pruefungen vor dem Zeichnen (Kastenabgleich und Texturabgleich im Objektschritt)
rechneten `od.x_pos + xx` und lasen damit 8-Bit-Punkte eine Kamerabreite neben dem Objekt.
Das Zeichnen selbst und die Fehlt-Maske (Zeile 1734) rechnen richtig in Pufferspalten.
Gemessen in Raum 61, gleiche Objekte, nur die Kamera anders:

```
Kamera 0  (sdLeft=0)   step2.5 objects: loaded=2 skipped=1 culled=11
Kamera 56 (sdLeft=56)  step2.5 objects: loaded=0 skipped=1 culled=8
Kamera 56, Spalte auf od.x_pos - sdLeft korrigiert: loaded=2 skipped=1 culled=8
```

Der Ausfall haengt allein an der Kameraposition. Sichtbar aendert die Korrektur in Raum 61
nichts (die beiden Objekte sind im HD-Hintergrund enthalten, 0 veraenderte Punkte), in Raum 44
ebenfalls nichts (keine HD-Objekte). Deshalb nicht committet; der Quellbaum enthielt waehrend
der Messung ausserdem unfertige fremde Aenderungen. Der Eingriff, zwei Zeilen:

```cpp
const int sx  = od.x_pos - sdLeft + xx;    // Kastenabgleich, vorher od.x_pos + xx
const int sx8 = od.x_pos - sdLeft + xx;    // Texturabgleich, vorher od.x_pos + xx
```

### Was offen bleibt, mit Messweg

1. Schritt 2 sollte die 8-Bit-Ebene waagerecht ab Pufferspalte `sdLeft` lesen, analog zu
   `sy + sdTop` senkrecht. Das ist nach den obigen Zahlen die Ursache fuer Inhalte, die um
   eine Kamerabreite neben dem HD-Hintergrund stehen: Figuren ohne HD-Kostuem, Schatten,
   8-Bit-Reste von Objekten, in Raum 44 gerade auch die Kanonen und Bootsteile an den
   Raendern. Eigene Aufgabe, weil die Aenderung alle Ebenen gleichzeitig verschiebt und eine
   eigene Messreihe braucht (Fenster 46 in Raum 44, 56 in Raum 61 mit Kamera).
2. Die drei Raumobjekte in Raum 44 haben keine HD-Textur; solange das so ist, kommen sie
   allein aus dem HD-Hintergrund. Wer sie als eigene Ebene will, muss sie extrahieren.
3. Der Satz in 133450b2, der Kameraversatz sei im Komposit schon erledigt und duerfe nicht
   abgezogen werden, gilt fuer den Hintergrund, nicht fuer die 8-Bit-Ebene; die Messung oben
   trennt die beiden Ebenen.

### Dateien

```
Aufnahmen Raum 44 (vor jeder Aenderung)  /opt/data/kanban/workspaces/t_24d94474/raum44_vorher
Aufnahmen Raum 61 mit Kamera 56          /opt/data/kanban/workspaces/t_24d94474/A_61_alt
dito mit korrigierter Spalte             /opt/data/kanban/workspaces/t_24d94474/B_61_neu
dito ohne Kameraversatz beim Zeichnen    /opt/data/kanban/workspaces/t_24d94474/C_61_ohne_abzug
Bild Objektpositionen                    projects/comi-hd/reports/vergleich/raum44_objektpositionen.png
Ausschnitt 1:1 um Objekt 849             projects/comi-hd/reports/vergleich/raum44_objektpositionen_ausschnitt.png
Messskripte                              projects/comi-hd/harness/objektpfad/
```

Hinweis zum Stand: die Messungen liefen mit `release/linux/scummvm` (13:20, Stand HEAD) und
mit Testbauten um 14:07 und 14:18. Der Quellbaum wurde ab 14:23 von einer anderen Aufgabe
geaendert, der Binarystand in `scummvm/fork` ist deshalb nicht mehr HEAD.

Bildlegende zu `raum44_objektpositionen.png` (Aufnahme 1280x960, also 2x Spielpixel):
gruen ist der Kasten, an dem der HD-Objektschritt zeichnen wuerde (Raumspalte minus
Kameraversatz), rot derselbe Kasten um den Kameraversatz versetzt, also die Lage, die die
8-Bit-Ebene im Komposit einnimmt. In Raum 44 bleibt der gruene Kasten leer, weil es keine
HD-Textur gibt; die rote Lage zeigt den gemessenen Versatz von 46 Spielpixeln.

Sonde zum Nachmessen (in `renderHDComposite` hinter der Berechnung von `sdLeft`/`sdTop`,
nach der Messung wieder entfernen):

```cpp
if (getenv("HD_OFFSET_PROBE") && _hdBackgroundSurface.getPixels()) {
    static int probeN = 0;
    if (++probeN % 20 == 0) {
        int tr[2] = {0, 0}, proben = 0;
        for (int sy = 4; sy < visH - 8; sy += 5) {
            const byte *prow = (const byte *)vs->getBasePtr(0, sy + sdTop);
            for (int sx = 4; sx < visW - 8; sx += 5) {
                const uint8 idx = prow[sx];
                const int pr = _currentPalette[idx * 3];
                const int pg = _currentPalette[idx * 3 + 1];
                const int pb = _currentPalette[idx * 3 + 2];
                for (int hyp = 0; hyp < 2; hyp++) {
                    const int roomX = sx + (hyp ? sdLeft : 0);
                    const int hx = roomX * scale + scale / 2;
                    const int hy = (sy + sdTop) * scale + scale / 2;
                    if (hx < 0 || hy < 0 || hx + 1 >= (int)_hdBackgroundSurface.w ||
                        hy + 1 >= (int)_hdBackgroundSurface.h)
                        continue;
                    const byte *p = (const byte *)_hdBackgroundSurface.getBasePtr(hx, hy);
                    if (MAX(ABS((int)p[0] - pr), MAX(ABS((int)p[1] - pg), ABS((int)p[2] - pb))) <= 48)
                        tr[hyp]++;
                }
                proben++;
            }
        }
        hdPrintf("OFFSETPROBE frame=%d sdLeft=%d xstart=%d proben=%d ohne=%d mit=%d",
                 _hdFrameCount, sdLeft, (int)vs->xstart, proben, tr[0], tr[1]);
    }
}
```

## Schattenflaeche an allen Kostuemen: 814 Frames in 64 Saetzen

Aufgabe: die Regel aus dem Guybrush-Fall (Schattenflaeche in der Alphamaske auf 0) auf alle
Kostuempngs unter `hd/costumes/` anwenden, nicht nur auf `LFLF_0001_AKOS_0002`.

### Vorgehen und Sicherung

```
hd/costumes/                 25.302 PNG in 445 Saetzen  (Stand vor dem Lauf)
hd/costumes_backup2/         Sicherung, 25.302 Dateien, Groesse und mtime je Datei
                             geprueft, Stichprobe md5-gleich
Werkzeug                     projects/comi-hd/harness/schatten_alle_kostueme.py
Aufnahme/Stichprobe          projects/comi-hd/harness/schatten_stichprobe.py
Nachpruefung                 projects/comi-hd/harness/schatten_nachpruefung.py
Trefferliste                 kanban t_9f018d32 / treffer_scan_alle.csv
```

Die Engine laedt aus `release/linux/hd/costumes` (eigene Kopie, 4,4 GB, nicht verlinkt).
Dort wurde dieselbe Regel getrennt angewandt, damit die RGB-Staende der Kopie unberuehrt
bleiben; die Alphawerte stimmen danach in beiden Verzeichnissen ueberein (geprueft).

### Welche Regel, und warum nicht die 8-Bit-Regel

Die Regel aus dem Guybrush-Fall leitet die Schattenfarbe je Frame aus der 8-Bit-Vorlage ab
(haeufigste dunkle Farbe im unteren Band). Ueber alle Frames mit Vorlage gemessen (13.831
Frames, davon 9.302 mit Kandidatenfarbe) ist das nicht tragfaehig:

```
Frames, die dadurch ueber 20 % ihrer Figur verlieren   1.064  (11,4 %)
Verteilung: 0-1 % 984, 1-5 % 3.693, 5-20 % 3.561, 20-50 % 975, ueber 50 % 89
Beispiel LFLF_0051_AKOS_0258_aframe_50: die abgeleitete Farbe (155,50,2) sitzt in
  28.986 Pixeln ueber das ganze Cel verteilt (y 3 bis 919) - das Kostuem ist braun,
  kein Schatten.
```

Deshalb arbeitet der Rollout HD-only, ohne Vorlage, und mit Farbe plus Form:

```
1. unteres Band y >= 0,80 h, nur deckende Pixel (Alpha > 200)
2. haeufigste quantisierte Farbe dort (4-Bit-Stufen), Mittelwert ihrer Pixel
3. Kandidatenflaeche: deckende Pixel mit Farbabstand <= 40 (Summe RGB), begrenzt auf y >= 0,65 h
4. uebernommen nur wenn die Flaeche den letzten Bildrand beruehrt, Hoehe <= 0,30 h,
   Breite >= 0,40 w, Fuellung der Bounding-Box >= 0,50
5. Farbfamilie der Schattenflaeche: R 140..205, G 38..62, B 0..12
   (gemessen: alle 814 uebernommenen Flaechen liegen in R 151..198, G 41..58, B 0..8)
```

Punkt 4 trennt flache Bodenflaechen von Figurteilen, Punkt 5 trennt sie von Kostuemfarben.
Ohne Punkt 5 bleiben 63 Treffer stehen, die kein Schatten sind, darunter
`LFLF_0025_AKOS_0150_aframe_8` mit (69,126,40) und 60 Prozent der Figur (gruen),
`LFLF_0053_AKOS_0269_aframe_36` mit (215,92,0) (orange) und
`LFLF_0055_AKOS_0284_aframe_211` mit (255,227,99) (hellgelb). Mit Punkt 5 verliert kein
einziger Frame mehr als 28,6 Prozent seiner Figur.

### Zahlen

```
Frames geprueft                       25.302
Treffer der Formregel                     877
davon in der Schattenfarbe und geaendert  814  in 64 Saetzen, 34 Raeumen
davon ausserhalb der Farbfamilie           63  nicht angetastet
entfernte Pixel                    11.980.977  (Median 15.233 je Frame, max 134.663)
Anteil der Figur, der entfernt wurde  Median 0,101, p90 0,136, max 0,286
Raeume mit den meisten Treffern      13 (96), 28 (76), 64 (67), 26 (56), 57 (54)
```

Nachpruefung ueber alle 814 geaenderten Dateien (Pixelvergleich gegen `hd/costumes_backup2/`):

```
RGB veraendert                             0 Dateien
Alpha ungleich 0 an geaenderten Punkten     0 Dateien
Alphawerte weichen von release/linux ab     0 Dateien
zweiter Lauf der Regel auf der Datei        0 neue Treffer (idempotent)
unterste deckende Zeile ueber der Fusszeile 0 Frames (Fuesse in allen 814 erhalten)
```

Nebenbefund: `LFLF_0001_AKOS_0002_aframe_348` (Guybrush, Raum 1) trug die Schattenflaeche
noch (Farbe 165/53/2), der frueherere Lauf hatte ihn nicht erfasst; er ist jetzt mit
behandelt.

### Stichprobe: 20 Frames aus 16 Saetzen

`projects/comi-hd/reports/stichprobe_schatten/stichprobe.txt` (Zahlen je Frame) und
`stichprobe20.png` (Sammelbild vorher|nachher, entfernte Flaeche gruen umrandet), Einzelbilder
`*_vorher_nachher.png`. Deckkraft vorher/nachher zum Beispiel:

```
LFLF_0013_AKOS_0064_aframe_71   174.977 -> 165.496   entfernt   9.481   5,4 %  Fuesse ja
LFLF_0026_AKOS_0155_aframe_24   179.380 -> 161.423   entfernt  17.957  10,0 %  Fuesse ja
LFLF_0035_AKOS_0192_aframe_17   170.580 -> 166.211   entfernt   4.369   2,6 %  Fuesse ja
LFLF_0016_AKOS_0087_aframe_187   83.688 ->  73.009   entfernt  10.679  12,8 %  Fuesse ja
```

### Aufnahmen aus drei Raeumen

```
projects/comi-hd/reports/vergleich/schatten_raum13_nachher.png   (96 Treffer im Raum)
projects/comi-hd/reports/vergleich/schatten_raum30_nachher.png   (4 Treffer)
projects/comi-hd/reports/vergleich/schatten_raum44_nachher.png   (1 Treffer)
Rohbilder      projects/comi-hd/work/schatten_aufnahme/raum{13,30,44}/h*.ppm
Befehl         harness/schatten_aufnahme.sh 13 30 44
```

### Was offen bleibt

1. Ein A/B im laufenden Spiel (unbehandelte gegen behandelte Texturen, Pixelvergleich der
   Bildfolgen) ist nicht gelungen: zwei Laeufe desselben Raums zeigen 13 gegen 13 Bilder mit
   Unterschieden ueber das ganze Bild, also nicht denselben Animationsstand. Die Aenderung
   ist deshalb je Datei gemessen (Alpha, Fuesse, Idempotenz), die Aufnahmen oben zeigen den
   Lauf mit behandelten Texturen, nicht den Vergleich.
2. Die Regel findet nur Schatten in der gemessenen Farbfamilie. Ein anders gefaerbter
   Schatten (dunkler in dunklen Raeumen) wird nicht angefasst; das ist die sichere Richtung
   (lieber stehen lassen als Figur wegnehmen), aber es ist eine Luecke.
3. 45,3 Prozent der Frames (11.471) haben keine 8-Bit-Vorlage in
   `projects/comi-hd/work/extract-fix4/costumes`. Sie sind nur ueber die HD-Regel abgedeckt;
   eine Gegenprobe gegen die Vorlage ist dort nicht moeglich.
4. Der 8-Bit-Rest unter Guybrush (Abschnitt "Was offen bleibt: die 8-Bit-Ebene malt den
   Schatten weiter") bleibt bestehen. Die HD-Textur ist jetzt in allen 64 Saetzen frei von
   der Flaeche, gezeichnet wird an diesen Stellen weiterhin die 8-Bit-Fassung, solange die
   Regel im `alpha == 0`-Zweig nicht eingeschraenkt ist.


## Gegenprobe Kanonen Raum 44: 46 Punkte waagerecht, 0 senkrecht (comi-pruef, 25.10.)

Auftrag war, nach dem Fix im Objekt-Pfad zu pruefen, ob die 8-Bit-Kanone auf der HD-Kanone
sitzt (Ziel 0 bis 1 Spielpunkt, also 0 bis 0,5 Kompositpunkte) und ob keine neue Dopplung
entstanden ist. Ergebnis vorweg: der Objekt-Pfad ist in Raum 44 nicht die Stelle, an der
etwas zu holen oder zu verderben ist, weil er dort nichts zeichnet. Die Kanone sitzt
46 Spielpunkte daneben, und zwar waagerecht die Kamerabreite, senkrecht genau. Die Ursache
ist Schritt 2 (offene Aufgabe `t_f072e2ac`), nicht der Objekt-Pfad.

### Messaufbau

Ein Lauf, ein Bildstand, damit sich Stufen und 8-Bit-Puffer nicht auseinanderziehen:

```
Binary     projects/comi-hd/work/engine/scummvm-d67 (13:45, Objekt-Pfad unveraendert)
Raum 44, Kamera 46:  hdgeom scale=4 camX=184 camY=0 room=952x480 comp=2560x1920 xstart=46
Schalter   HD_JUMP_ROOM=44 HD_DUMP_STEPS=1 HD_DUMP_SEQ=1 HD_TRACE_DRAW=1 HD_EXIT_AFTER=160
Aufnahme   kanban/workspaces/t_cf9ce439/vorher_ohne_tint (Stufen 1 bis 4, 54 r/h-Paare)
           kanban/workspaces/t_cf9ce439/vorher (dito mit HD_TINT_8BIT=1, fuer die Ortskarte)
```

Ohne `HD_TINT_8BIT`, weil die Einfaerbung die Palettenfarbe im Komposit veraendert und
damit jeden exakten Farbvergleich unbrauchbar macht. Der erste Lauf mit Einfaerbung ergab
deshalb 0 Prozent Farbgleichheit an allen Stellen; der zweite zeigt 100 Prozent.

### Zahlen

```
Objektschritt (Stufe 2 gegen 3)              0 Punkte von 307.200
HD-Texturen fuer die drei Raumobjekte        hd/objects: 982 Dateien, keine mit 0044
                                             object_map.json: kein Eintrag 0044
8-Bit-Ebene eingeklebt (Stufe 2 gegen 1)     31.655 Punkte = 10,3 %
eingeklebte Punkte mit Farbe des Puffers
  an derselben Spalte gelesen                100,0 %  (11.181 geprueft)
  46 Spalten weiter links gelesen            12,3 %
Puffer gegen Raumbild, Vorlagensuche
  Krug/Theke (Raumspalte 452)                +0 Spalten, NCC 0,982   (bei -46: 0,092)
  Boot hinten (96)                           +0 Spalten, NCC 0,985   (bei -46: 0,300)
  Theke mitte (250)                          +0 Spalten, NCC 0,988   (bei -46: 0,005)
Ueberklebt je Kasten, richtige Stelle / eine Kamerabreite rechts
  Kanonen-/Krugkasten (Raum 512..600)         9,6 % / 33,7 %
  Person rechts (Raum 600..640)              20,5 % / 91,4 %
  Figur (Raum 340..400)                       9,4 % / 42,2 %
  Kanonenrad rechter Rand (Raum 592..640,
    Zeilen 352..448)                          0,0 % / 87,9 %
Kostuemschritt (Stufe 4 gegen 3)             16.715 Punkte, dichteste Spalten 340..399
```

Die drei Zeilen mit 100 Prozent und mit 0 Spalten sind der Kern: der Kompositpunkt bekommt
die Farbe des Pufferpunkts derselben Spalte (also wird gelesen, wo geschrieben wird), und
der Puffer fuehrt Raumspalten. Damit landet der 8-Bit-Inhalt auf Kompositspalte gleich
Raumspalte, waehrend der HD-Hintergrund an dieser Stelle Raumspalte plus Kamera zeigt.
Der Versatz ist die Kamerabreite: 46 Punkte waagerecht, 0 senkrecht, weil senkrecht
`sy + sdTop` gelesen wird und `sdTop` in Raum 44 null ist.

### Sichtpruefung

`reports/vergleich/raum44_kanone_vorher.png`: oben der Komposit mit gruenem Kasten auf der
HD-Kanone (466..554) und rotem Kasten eine Kamerabreite rechts (512..600), rechts daneben
derselbe Ausschnitt ohne 8-Bit-Ebene. Im Komposit liegen zwei Fassungen derselben Stelle
uebereinander, im reinen HD-Bild ist jede einmal da. `reports/vergleich/
raum44_kanone_rand_vorher.png` zeigt denselben Vergleich am Kanonenrad am rechten Rand:
links das Rad einmal, rechts das Rad plus eine versetzte, angeschnittene Kopie, dazu der
Steinblock und das Gewaechs doppelt. Das ist die Dopplung, die die Karte meint, und sie
kommt aus Schritt 2. `reports/vergleich/raum44_figur_vorher.png` zeigt den Figurenbereich
(Spalten 300..440): die 8-Bit-Figur erscheint nur im Bild mit 8-Bit-Ebene, und zwar einmal
und nicht als Doppelgaenger, weil das HD-Kostuem an derselben Stelle gezeichnet wird (siehe
Punkt 3 unten).

### Berichtigung einer frueheren Messung

Der fruehere Befund in dieser Sache (dx = -1 Kompositpunkt, "in sich stimmig") war falsch.
Damals wurde der r-Frame gegen den Komposit mit einem Suchradius von plus/minus 10 Punkten
verglichen; der tatsaechliche Versatz ist 92 Kompositpunkte, also weit ausserhalb. Was als
Versatz von 1 Punkt gemessen wurde, war das Rauschen der Farbunterschiede. Mit weiter Suche
und exaktem Farbvergleich ist das Bild eindeutig.

### Was daraus fuer den naechsten Schritt folgt

1. Der Objekt-Pfad braucht in Raum 44 keine Aenderung; er zeichnet dort null Punkte, und
   wo er zeichnet (Raum 61), sitzt er nach der Messung von `t_24d94474` pixelgenau.
2. Schritt 2 ist die Stelle (`t_f072e2ac`). Nach dem Umbau muss diese Messung den Versatz 0
   zeigen, und zwar auf beiden Achsen.
3. Zusatz, der beim Umbau mitgeprueft werden muss: Figur (8-Bit-Ebene) und HD-Kostuem
   liegen heute beide auf denselben Kompositspalten 340..399, also beide 46 Punkte rechts
   des Hintergrundinhalts. Sie fallen nur deshalb zusammen, weil beide den Kameraversatz
   nicht abziehen. Wird die 8-Bit-Ebene kuenftig 46 Punkte weiter links eingeklebt, steht
   das HD-Kostuem 46 Punkte rechts davon, solange der Kostuemweg den Abzug nicht wieder
   zieht. Diese Wechselwirkung ist der Grund, warum der Kostuemweg in derselben Messreihe
   mitlaufen muss.

### Dateien

```
Sichtbilder   projects/comi-hd/reports/vergleich/raum44_kanone_vorher.png
              projects/comi-hd/reports/vergleich/raum44_kanone_rand_vorher.png
              projects/comi-hd/reports/vergleich/raum44_figur_vorher.png
Messskripte   projects/comi-hd/harness/objektpfad/gegenprobe44.py      (Zahlen + Sichtbild)
              projects/comi-hd/harness/objektpfad/kanone_zahlen.py     (Kanonenkasten)
              projects/comi-hd/harness/objektpfad/paste_herkunft.py    (Farbgleichheit)
              projects/comi-hd/harness/objektpfad/puffer_raumspalte_weit.py
              projects/comi-hd/harness/objektpfad/figur_lage.py        (Kostuem gegen Figur)
              projects/comi-hd/harness/objektpfad/kanone_sichtbild.py
              projects/comi-hd/harness/objektpfad/rand_sichtbild.py
              kanban/workspaces/t_cf9ce439/lauf44.sh                   (Messlauf)
Rohdaten      kanban/workspaces/t_cf9ce439/vorher_ohne_tint
```

Nachher-Messung offen: sie braucht den Schritt-2-Umbau aus `t_f072e2ac`. Der Messweg oben
ist dafuer unveraendert anwendbar, ein zweiter Lauf mit der neuen Binary genuegt.

## Schritt 2 liest die 8-Bit-Ebene jetzt ab der Fensterspalte (Raum 44, 46 px)

Der in "Objekt-Pfad Raum 44" offen gelassene Punkt 1 ist gebaut: die 8-Bit-Ebene wird in
`renderHDComposite` waagerecht ab `sdLeft` gelesen, genau wie senkrecht ab `sdTop`. Vorher las
jede Stelle ab Pufferspalte 0, das sichtbare Fenster beginnt aber bei `sdLeft` (Raum 44: 46).

### Beleg, dass Pufferspalte 0 die Raumspalte 0 ist

Drei Ausschnitte aus dem 8-Bit-Puffer (Spalten 0..119, 250..389, 500..639) wurden im
HD-Raumbild gesucht, mit oertlicher Mittelwertfreiheit gegen den Helligkeitsverlauf:

```
Ausschnitt   0..119   bester Treffer Raumspalte   0  NCC 0,6591  (Nachbar +1: 0,4564)
Ausschnitt 250..389   bester Treffer Raumspalte 250  NCC 0,6380  (Nachbar -1: 0,3897)
Ausschnitt 500..639   bester Treffer Raumspalte 500  NCC 0,8486  (Nachbar -1: 0,6023)
```

Zusaetzlich in-engine (Sonde mit vier Hypothesen, Raum 44, Bild 80, sdLeft=46, 11.625 Proben):
Pufferspalte = Raumspalte 9.876 Treffer (85 Prozent), Spalte+46 3.720 (32 Prozent),
Spalte+40 4.005 (34 Prozent), Spalte+6 7.111 (61 Prozent). Die 8-Bit-Ebene steht also in
Raumspalten, das Fenster ist um den Kameraversatz dagegen versetzt.

### Was umgestellt ist

`sdX = sdLeft` und `visX = MIN(visW, vs->w - sdX)`. Ab `sdX` gelesen wird an allen Stellen, die
das Fenster betreffen: Vorlagenaufnahme (`hdRefreshCleanBackground`), Selbstheilungspruefung der
Vorlage, Vordergrundschleife (visRow/cleanRow), Objekt-Sichtbarkeit und Fehlt-Maske, die beiden
Objektvergleiche, Inventarbereich, Figuren-Rueckfall, Schriftpruefung. Die Vorlage liegt damit
in Fensterspalten, `_hdCleanXStart` bleibt der Fensteranfang im Raum (der Streifenweg in
`drawRoomBackground` rechnet schon immer so). `hd_ref.ppm` ist jetzt das Fensterbild, also das,
was der Bildschirm zeigt. Die rechten `sdLeft` Spalten haben keinen Pufferinhalt (der Puffer
haelt Raumspalten 0..639, das Fenster braucht 46..685); dort bleibt der HD-Hintergrund stehen.

### Messwerte nach dem Umbau

Eingeklebte Pixel sind die Pixel, die sich zwischen Stufe 1 und Stufe 2 unterscheiden. Geprueft
wird, ob ihre Farbe an derselben Bildstelle der 8-Bit-Vorlage entspricht (Toleranz 24).

```
Raum 44, Bild 80:   11.755 eingeklebt (3,8 Prozent), gleiche Bildstelle 11.755 von 11.755 (100,0 Prozent)
                    Gegenprobe Vorlage +40 Spalten 739 (6,3), -40 Spalten 748 (6,4)
Raum 44 vorher:      5,5 Prozent gleiche Bildstelle, beste Gegenprobe +40 Spalten 32,9 Prozent
Raum 61, Kamera 56:     17 eingeklebt, 17 von 17 deckungsgleich
Raum 13/47:          Stufen 2, 3, 4 pixelgleich zu vorher (0 abweichende Punkte)
Raum 30:             208 abweichende Punkte (0,017 Prozent, Animationsphase; xstart 0, gleicher Codepfad)
8-Bit-Anteil Raum 44 (HD_TINT_8BIT): 10,9 Prozent vorher, 3,8 Prozent nachher
```

Der Rueckgang des 8-Bit-Anteils ist die Folge der Ausrichtung: vorher galt fast das ganze Bild
als Vordergrund, weil die Vordergrundpruefung den Puffer gegen eine um 46 Spalten versetzte
Vorlage stellte. Was jetzt noch eingeklebt wird, sitzt deckungsgleich (100 Prozent), und die
HD-Ebene bleibt stehen, wo sie hingehoert.

Aufnahmen und Messskripte: `projects/comi-hd/work/messung_schritt2/`,
`projects/comi-hd/harness/objektpfad/` (ausschnitt_lage.py, deckung_ref.py, ab_vergleich.py,
spaltenlage_raum.py).

## Beweisvideo Raum 44: 6,6 Prozent des Bildes sind 8 Bit, verteilt ueber das ganze Bild

Auftrag war, statt Einzelbildern einen laengeren Lauf aufzunehmen und je Bild den sichtbaren
8-Bit-Anteil zu messen, weil die gelieferten Standbilder den Fehler nicht zeigten, den der
Spieler sieht (Dopplungen links am Boot, falsch stehende Person rechts, Kanonen).

### Messaufbau

```
Binary      release/linux/scummvm, 25.10. 13:20, sha256 25b2c5b5...
            Kopie mit eigenen Aufnahmepfaden: work/engine/scummvm-bw4, sha256 43c887cd...
            (harness/beweis_binary.py, sonst loeschen parallele Aufgaben die Bildfolge)
Lauf        HD_JUMP_ROOM=44 HD_FIXED_DELTA=100 HD_EXIT_AFTER=700
            HD_DUMP_SEQ=1 HD_TINT_8BIT=1 HD_TRACE_DRAW=1, Raum 44 bestaetigt (bw4room.txt)
Umfang      200 Bilder, das ist die Obergrenze der Engine (hdSeqNo < 200), also 600
            Kompositionen; bei 100 ms Zeitschritt sind das 60 s Spielzeit, Laufzeit 143 s
Werkzeug    harness/beweis_lauf.sh, harness/beweis_auswertung.py, harness/beweis_zahlen.py
```

Je Bild liegen zwei Aufnahmen aus demselben Lauf vor: `h*.ppm` (HD-Komposit, 2 Dumppixel je
Spielpixel) und `r*.ppm` (die 8-Bit-Ebene desselben Bildes in Palettenfarben). Damit wird der
sichtbare 8-Bit-Anteil auf zwei Wegen gemessen:

1. Signalfarbe: `HD_TINT_8BIT` faerbt jedes Pixel der 8-Bit-Vordergrundebene magenta. Exakt.
2. Palettenfarbe: die Stufe 2.6b schreibt danach 8-Bit-Punkte in echter Palettenfarbe ueber
   den HD-Hintergrund. Diese Punkte sind nicht magenta. Erkannt wird die Flaeche, indem der
   2x2-Block des Komposits mit dem Pixel der 8-Bit-Aufnahme verglichen wird; die Stufe
   schreibt genau den Palettenwert dieses Pixels.

Gegenprobe der zweiten Groesse gegen den Engine-Zaehler im Protokoll (`step2.6b ui-overlay:
pixels=`, 22 Zeilen im Lauf):

```
Engine-Zaehler            19.336 / 19.346 / 19.645 Punkte je Bild
auf das 8-Bit-Fenster
  (594 von 640 Spalten)    17.956 erwartet
aus den Bildern gezaehlt   17.424 im Mittel = 97,0 %
```

### Zahlen (185 Bilder mit geladener HD-Ebene)

```
8-Bit sichtbar gesamt   min 6,37   median 6,58   max 6,73   Mittel 6,60  Prozent der Flaeche
  Signalfarbe (Tint)    min 0,81   median 0,92   max 0,97   Mittel 0,93
  Palettenfarbe (2.6b)  min 5,53   median 5,67   max 5,78   Mittel 5,67
Palettenpunkte je Bild  16.993 / 17.422 / 17.754
Flaechen ueber 60 Spielpixel je Bild   41 bis 46
groesste Einzelflaeche  9.132 Dumppunkte = 2.283 Spielpixel, Streifen x 594..603, y 141..371
```

Die 15 Bilder vor dem Sprung (Bildnummern 0 bis 14) zeigen den dunklen Moment nach
`startScene(44)`, in dem die HD-Ebene noch nicht geladen ist; dort ist das Bild die
8-Bit-Fassung selbst (rund 70 Prozent Palettenfarbe) und die Zahl sagt nichts aus. Sie sind in
der CSV als `hd_geladen=nein` markiert und in den Statistiken nicht enthalten.

### Warum die Standbilder den Fehler nicht zeigten

Der sichtbare 8-Bit-Anteil ist nicht eine grosse Dopplung an einer Stelle, sondern ein
Flickenmuster ueber das ganze Bild: 5,67 Punkte Palettenfarbe plus 0,92 Punkte Signalfarbe.
Die groesste zusammenhaengende Flaeche ist der bekannte Randstreifen (x 594..603), der Rest
sind 41 bis 46 kleine Flaechen auf Texturkanten: Takelage, Wellen, Figur, Theke, Banner,
Schilder. In einem Standbild sieht das wie Textur aus, markiert ist es eindeutig. Der
Kernbefund fuer die Messmethode: wer nur die Signalfarbe misst, sieht 0,92 Prozent und
unterschaetzt den sichtbaren 8-Bit-Anteil um den Faktor 7.

### Bezug zum Versatz von 46 Spalten

Der Befund oben (Abschnitt "Gegenprobe Kanonen Raum 44") erklaert die Lage: Schritt 2 klebt
die 8-Bit-Ebene spaltengenau in den Komposit, waehrend der HD-Hintergrund dort Raumspalte
plus Kamera zeigt. In Raum 44 sind das 46 Spielpixel waagerecht, 0 senkrecht. Deshalb steht
jede 8-Bit-Flaeche eine Kamerabreite neben ihrem HD-Gegenstueck, und deshalb sind es viele
kleine Flaechen und nicht eine: nur wo die 8-Bit-Vorlage Struktur hat (Kanten, duenne
Details), faellt die versetzte Kopie auf. Die Zahl hier ist der Ist-Stand vor dem Umbau von
Schritt 2 (`t_f072e2ac`) und damit die Vorher-Zahl fuer dessen Nachmessung.

### Was die Zahlen nicht zeigen

1. Der Sprunglauf haelt die Kamera bei 46 (in 22 der 24 `hdgeom`-Zeilen camX 184, xstart 46;
   die zwei Zeilen davor gehoeren zum Zustand vor dem Sprung), der Vordergrund bleibt bei
   32.534 bis 33.467 Punkten (10,6 bis 10,9 Prozent, davon 23.976 bis 25.414 Objekt, 8.038
   sonst, 9 bis 520 Figur). Andere Kamerapositionen von Raum 44 werden mit diesem Verfahren
   nicht erfasst. `HD_SCROLL_TEST` erzeugt laut frueherem Befund einen kuenstlichen Zustand
   und bleibt aussen vor.
2. Die Szene steht weitgehend: zwischen zwei Bildern aendern sich im Median 1,69 Prozent der
   Punkte, der 8-Bit-Anteil bleibt dabei in dem engen Band 6,37 bis 6,73 Prozent. Acht Bilder
   liegen bei 6,73 Prozent, die naechsten vier bei 6,72, es gibt also kein "schlimmstes"
   Bild. Die drei Beispielbilder sind deshalb 20 Bilder (6 s Spielzeit) auseinandergelegt,
   statt drei Mal denselben Zustand zu zeigen.
3. Die Palettenfarbe ist nur im 8-Bit-Fenster pruefbar (594 von 640 Spalten). Im 46 Pixel
   breiten Streifen rechts davon wird nur die Signalfarbe erfasst.
4. Die Abschaltprobe (`HD_NO_ACTORS=1 HD_NO_OBJECTS=1`) taugt nicht als Anteilsmass: zwei
   Laeufe mit identischer Einstellung unterscheiden sich schon in 1,07 Prozent der
   8-Bit-Punkte, weil die Bewegungsphase nicht reproduzierbar ist. Sie wird deshalb nur als
   Blinkvergleich fuers Auge verwendet, nicht als Zahl.

### Dateien

```
Video, alle 200 Bilder, 20 fps       projects/comi-hd/reports/vergleich/raum44_beweis.mp4
                                     (1280x960, 10,0 s, 3,7 MB)
Blinkvergleich normal gegen ohne     projects/comi-hd/reports/vergleich/raum44_beweis_blinken.mp4
  8-Bit-Figuren/-Objekte             (185 Paare, 18,5 s; Schalterprobe, keine Messung)
Drei markierte Standbilder           projects/comi-hd/reports/vergleich/raum44_beweis_{1,2,3}.png
Zahlen je Bild                       projects/comi-hd/work/raum44_beweis_lang/bilder.csv
Zusammenfassung                      projects/comi-hd/work/raum44_beweis_lang/zusammenfassung.json
Rohbilder h/r                        projects/comi-hd/work/raum44_beweis_lang/raw/ (400 Dateien)
Markierte Einzelbilder des Videos    projects/comi-hd/work/raum44_beweis_lang/markiert/
Protokolle des Laufs                 .../hd_state.log, .../hd_fg.log, .../stdout.log
Werkzeuge                            projects/comi-hd/harness/beweis_binary.py
                                     projects/comi-hd/harness/beweis_lauf.sh
                                     projects/comi-hd/harness/beweis_auswertung.py
                                     projects/comi-hd/harness/beweis_zahlen.py
```

Die Markierung im Video: halbtransparentes Gelb auf jedem sichtbaren 8-Bit-Punkt, gelbe
Kontur und rote Kaesten mit Nummer auf den acht groessten Flaechen, Kopfzeile mit beiden
Anteilen, Fusszeile mit Spielpixel-Koordinaten der beiden groessten Flaechen.
