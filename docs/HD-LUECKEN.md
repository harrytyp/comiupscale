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

Nachtrag 25.10.2026: dieser Abschnitt ist widerlegt, siehe "Objektweg Raum 61: die Spalten
sind richtig, der CULL verwirft das Objekt" am Ende dieser Datei. Pufferspalte ist
Raumspalte, beide Pruefungen lesen bereits die richtige Spalte; die vorgeschlagenen zwei
Zeilen wuerden sie eine Kamerabreite daneben stellen.

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

## Z-Reihenfolge im Komposit: Wasser hat keine eigene Ebene

Frage war, an welcher Stelle im Komposit eine Wassertextur ueber ein Objekt geschrieben wird.
Ergebnis: es gibt keine Wasser-Ebene und keinen Zeichenschritt, der Wasser nach den Objekten
malt. Wasser kommt ausschliesslich mit der 8-Bit-Ebene ins Bild, und die wird an genau zwei
Stellen in das Komposit geschrieben: Schritt 2 (vor den Objekten) und Schritt 2.6b (nach
Objekten und Kostuemen). Was tatsaechlich ueber HD-Inhalt liegt, ist die 8-Bit-Ebene aus
Schritt 2, und in Raeumen, die breiter sind als der Bildschirm, liegt sie zusaetzlich um eine
Kamerabreite falsch.

### Reihenfolge, in der renderHDComposite schreibt (gfx.cpp)

```
1  HD-Hintergrund, Fenster um camX/camY        1650 bis 1689   Stufendump 1_hintergrund
2  8-Bit-Ebene als Vordergrund (hier das Wasser) 1784 bis 1933   Stufendump 2_vordergrund
2.5 HD-Objekte, Reihenfolge wie die Engine      2007 bis 2659   Stufendump 3_objekte
    (object.cpp:644 laeuft rueckwaerts ueber die Objekttabelle,
     gfx.cpp:2156 laeuft dieselbe Richtung, das ist deckungsgleich)
2.5b Inventarobjekte aus der Blast-Queue        2582 bis 2658
2.6 HD-Kostueme, nach sortKey                   2660 bis 3149
2.6b 8-Bit-Ebene erneut, nach Objekten und Kostuemen  3150 bis 3254
2.7 HD-Schrift                                  3257 bis 3308   Stufendump 4_kostueme
2.8/2.8b/2.9 Verben-Flaeche, Inventaricon, Cursor  3310 bis 3432
3  Uebergabe an die Grafik                      3432
```

Zwischen Schritt 2 und 2.5 gibt es keinen weiteren Schreiber, und nach 2.5 nur 2.6b als
Pfad, der 8-Bit-Inhalt malt. Damit kann Wasser aus Schritt 2 keine Objekte ueberdecken,
sondern nur den Hintergrund. Ein Wasser-punkt, der nach dem Objektschritt ins Bild kommt,
kann ausschliesslich aus 2.6b stammen.

### Gemessen: kein Wasser nach dem Objektschritt

Drei Laeufe, je ein Bild, Stufendumps (`HD_DUMP_STEPS=1`), Vergleich der Stufen:

```
Raum 41 shipcom2  xstart 0    Schritt 1->2 48.008 Punkte (3,91 %), davon wasserfarben 35.936
                              Schritt 2->3           0 Punkte
                              Schritt 3->4           0 Punkte
                              Schritt 2.6b      13.519 Punkte je Bild, davon anders als Stufe 2: 0
Raum 43 shipcom4  xstart 0    Schritt 1->2 61.019 Punkte (4,97 %), davon wasserfarben 50.695
                              Schritt 2->3           0 Punkte
                              Schritt 3->4           0 Punkte
                              Schritt 2.6b      15.206 Punkte je Bild, davon anders als Stufe 2: 0
Raum 44 armsdlr   xstart 46   Schritt 1->2 134.404 Punkte (10,94 %)
                              Schritt 2->3           0 Punkte (keine HD-Objekte, siehe oben)
                              Schritt 3->4 120.051 Punkte (Kostueme)
                              Schritt 2.6b      19.346 Punkte je Bild
```

2.6b schreibt in den Schiffskarten also 13.519 beziehungsweise 15.206 Punkte je Bild und
aendert gegenueber Stufe 3 nichts: dieselben Punkte, dieselben Farben wie in Schritt 2. Die
8-Bit-Ebene kommt dort vollstaendig aus Schritt 2, also von VOR den Objekten. Eine
Wassertextur ueber einem Objekt kann in diesen Raeumen nicht entstehen.

Zwei Unterschiede zwischen Schritt 2 und 2.6b bleiben im Code offen, beide ohne Messbeleg fuer
eine sichtbare Wirkung:

1. Schritt 2 ueberspringt Palettenindex 255 (`gfx.cpp:1859`), 2.6b hat diese Ausnahme nicht
   (`gfx.cpp:3200 bis 3250`). Ein Punkt mit Index 255, der sich von der Vorlage
   unterscheidet, wird also erst nach den Objekten gemalt. Raeume 41 und 43 zeigen dafuer
   null Punkte, Raum 42 hat 3.679 Punkte Unterschied zwischen Stufe 3 und Stufe 4; ob sie
   aus dieser Ausnahme oder aus den Kostuemen stammen, ist nicht getrennt gemessen.
2. 2.6b ueberspringt den Kasten gezeichneter Figuren, 2.6 nicht.

### Der belegte Fall: die 8-Bit-Ebene deckt den HD-Hintergrund zu

`hdRefreshCleanBackground` (gfx.cpp:1399 bis 1415) erneuert die Vergleichsvorlage nur ueber
`MIN(visW, vs->w - vs->xstart)` Spalten (`gfx.cpp:1406`). Rechts davon steht alte Vorlage,
`_hdCleanValid` meldet trotzdem 1 (das `memset` in `gfx.cpp:1413` setzt `visW*visH` Bytes
zusammenhaengend, nicht je Zeile). Schritt 2 erklaert diese Spalten damit zu Vordergrund und
legt die 8-Bit-Ebene, Wasser eingeschlossen, ueber den HD-Hintergrund.

```
Raum 42 shipcom3, xstart 332, Fenster deckt 308 von 640 Spalten
  links (Vorlage frisch)      591.360 Punkte, uebermalt  1,5 %
  Streifen (Vorlage alt)      637.440 Punkte, uebermalt 69,9 %, davon wasserfarben
                              435.488 Punkte (68,3 % der Streifenflaeche)
Raum 44 armsdlr, xstart 46
  links (Vorlage frisch)    1.140.480 Punkte, uebermalt  4,2 %
  Streifen (Vorlage alt)       88.320 Punkte, uebermalt 97,9 % (86.452), wasserfarben 0
```

Raum 42 ist die Seeschlacht: 435.488 Punkte blockiges 8-Bit-Wasser ueber dem HD-Bild, und die
Kante zwischen frischer und alter Vorlage ist im Bild als senkrechter Streifen zu sehen. Raum
44 zeigt dieselbe Bauart bei kleinerem Versatz, dort liegt im Streifen Stein und Holz, kein
Wasser.

### Was die Zahlen nicht zeigen

1. Die Wasserfarbe wird ueber den Farbton erkannt (Blau deutlich ueber Rot). Das faengt auch
   blaue Kleidung: die groesste zusammenhaengende Fundstelle in Raum 67 liegt auf Guybrushs
   Hemd, nicht auf Wasser (Sichtpruefung des markierten Ausschnitts). Die Wasserzahlen sind
   deshalb eine Obergrenze, und ein einzelner Fundpunkt beweist nichts; belastbar ist erst die
   Zuordnung zu einem Zeichenschritt, und die kommt aus den Stufendumps, nicht aus der Farbe.
2. Die Stufendumps sind 2x2 gemittelt (1280x960 aus 2560x1920). Feine 8-Bit-Anteile werden
   dadurch kleiner gemessen als sie sind.
3. Welche Szene der Nutzer genau gesehen hat, steht nicht in der Aufgabe. Gemessen sind Raum
   42, 41, 43, 44 im Detail und 20 Wasserraeume im Ueberblick (Reihe in
   `work/zorder/reihe.csv`, je ein Bild). In keiner dieser Reihen schrieb ein Schritt nach den
   Objekten nennenswert Wasser auf ein Objekt (hoechster Wert 3.185 Punkte, Raum 78, dort
   zeichnet eine Objekttextur in Bildschirmgroesse).

### Was ein Fix messen muesste

Richtung: die Vorlage in `hdRefreshCleanBackground` ueber alle 640 Spalten fuellen (der
8-Bit-Inhalt ist dort nachweislich richtig) oder die Spalten rechts von
`vs->w - vs->xstart` als ungueltig markieren, damit Schritt 2 dort nichts uebermalt. Dazu das
`memset` der Gueltigkeitsmaske je Zeile setzen. Messlatte: Streifenanteil in Raum 42 von 69,9
auf unter 5 Prozent und in Raum 44 von 97,9 auf unter 5 Prozent, Magenta-Anteil Raum 44
(jetzt 0,95 Prozent) unveraendert, und die vorher sauberen Raeume 41 und 43 erneut messen. Der
erste Teil ist als Aufgabe t_f072e2ac bereits offen.

### Dateien

```
Vorher/Nachher Raum 42 (Streifen)   projects/comi-hd/reports/vergleich/raum42_schiff_hd.png
                                    .../raum42_schiff_komposit.png
                                    .../raum42_schiff_markiert.png
Vorher/Nachher Raum 44 (Streifen)   .../raum44_streifen_hd.png
                                    .../raum44_streifen_komposit.png
                                    .../raum44_streifen_markiert.png
Stufenlaeufe, je ein Verzeichnis    projects/comi-hd/work/zorder/{j44,j44na,b41,b43,r042}/
Reihe ueber 20 Wasserraeume         projects/comi-hd/work/zorder/reihe.csv
Werkzeuge                           projects/comi-hd/harness/zorder_lauf.py      (isolierter Lauf)
                                    projects/comi-hd/harness/hd_dump_umleiten.c  (LD_PRELOAD, eigene Dumps)
                                    projects/comi-hd/harness/zorder_stufen.py    (Stufenvergleich)
                                    projects/comi-hd/harness/zorder_wasser_ueber.py
                                    projects/comi-hd/harness/zorder_streifen_beleg.py
                                    projects/comi-hd/harness/zorder_reihe.py     (Reihenmessung)
```

Die Engine ist unveraendert; `git status` in den Quellen zeigt nur die Aenderungen der anderen
Aufgaben. Die Aufnahmen laufen ueber `hd_dump_umleiten.so`, weil die Engine ihre Dumps fest
nach `work/dumps/` schreibt und parallele Laeufe sich sonst dieselbe
`hd_step_2_vordergrund.ppm` ueberschreiben (gemessen: zwei Laeufe, dieselbe Datei).

## Baseline der HD-Positionierung: fuenf Raeume vor der Aenderung

Stand 25.10.2026. Vermessen wurde der Versatz zwischen 8-Bit-Silhouette und HD-Kostuemflaeche
in den Raeumen 3, 9, 15, 44 und 86, je Akteur, mit beiden Zeichenwegen, mit und ohne
Skalierung, in gescrolltem und ungescrolltem Zustand. Dazu der magenta_check dieser Raeume.
Es wurde kein Code geaendert; alle Zahlen gelten fuer die Release-Binary vom 25.10. 13:20
(md5 33ad6cdd568f652ea5da6dec3b3a8803). Spaetere Commits stecken nicht darin, weder 627a8d62
(13:47) noch 12f1a869 (15:25, "Read the 8-bit layer from the camera column in step 2").
Die Baseline liegt damit vor genau der Aenderung, um die es geht.

### Messplatz

Ein Lauf je Raum mit einer Privatkopie der Release-Binary, deren Aufnahmepfade auf das Praefix
`bl` umgeschrieben sind (`harness/baseline_binary.py`, gleiche Laenge der Pfade wegen
Stringtisch). Damit schreiben parallele Messungen anderer Aufgaben nicht in dieselben Dateien.

```
HD_JUMP_ROOM=<raum> HD_FIXED_DELTA=20 HD_EXIT_AFTER=120 HD_DUMP_STEPS=1
HD_TRACE_DRAW=1 HD_TINT_8BIT=1 HD_SPY=1
Bild 119 ist der Dump; alle Werte gelten fuer dieses Bild.
```

Der feste Zeitschritt macht den Lauf reproduzierbar: die Wiederholung von Raum 44 und Raum 9
ergibt in allen zehn Eintraegen dieselben Werte bis auf die letzte Stelle
(`harness/baseline_wiederholung_pruefen.py`, `reports/vergleich/baseline/versatz_wiederholung.csv`).

Ausgewertet mit `harness/baseline_auswertung.py`:

- HD-Flaeche = |Stufe 4 minus Stufe 3|, also genau die Pixel, die der Kostuem-Schritt setzt.
- 8-Bit-Silhouette = Magenta in Stufe 2 (`HD_TINT_8BIT`).
- Versatz per Kreuzkorrelation im Fenster des Eintrags, Suchradius 12 Spielpixel
  (6 bei Kleinstfiguren), positiv = die HD-Flaeche muss nach rechts bzw. unten,
  steht also links bzw. oberhalb der 8-Bit-Silhouette.
- Belastbar ist ein Eintrag nur, wenn die HD-Flaeche zu mindestens 70 Prozent auf der
  8-Bit-Silhouette landet und beide Flaechen hoechstens Faktor 4 auseinanderliegen.
  Die zweite Zahl der Deckungsspalte ist die Gegenrichtung; sie ist bei Figuren mit
  sehr kleiner HD-Flaeche niedrig, weil das Fenster dann nur wenige 8-Bit-Punkte hat.

### Ergebnis je Raum, Figur und Zeichenweg

Versatz in Spielpixeln. Skalierung ist die Blitbreite gegen die Breite des Kostuem-PNG
(100 Prozent = unskaliert). Scrollen nennt den Kameraanfang des Puffers (`xstart`) und die
Raumbreite; `nein (0/640)` heisst also ungescrolltes Bild in einem 640 Punkte breiten Raum.

```
Raum  Figur              Zeichenweg      Skalierung  Scrollen          dx     dy     Deckung HD/8Bit  belastbar
---------------------------------------------------------------------------------------------------------------
3     -                  -               -           unbekannt         -      -      -                nein, kein HD-Hintergrund (HD: no bg for room 3)
9     ai=1  akos 0002    gliedmassen     76,2 %      nein (0/640)      +0,5   +0,5   0,99/0,72        ja
9     ai=1  akos 0002    gliedmassen     76,3 %      nein (0/640)      +0,0   +1,0   0,98/0,67        ja
9     ai=2  akos 0025    gliedmassen     100,0 %     nein (0/640)      +0,0   +0,0   0,98/0,73        ja
9     ai=2  akos 0025    gliedmassen     100,0 %     nein (0/640)      +0,0   +0,0   0,98/0,82        ja
9     ai=12 akos 0026    rueckfall-cel0  100,0 %     nein (0/640)      +0,0   +0,0   0,96/0,94        ja
15    ai=1  akos 0002    gliedmassen     3,9 %       nein (0/2096)     +0,5   +0,0   1,00/0,46        ja
15    ai=1  akos 0002    gliedmassen     -           nein (0/2096)     -      -      -                nein, eine Seite fast leer
15    ai=4  akos 0075    gliedmassen     100,0 %     nein (0/2096)     +0,0   +0,0   0,60/0,76        nein, Deckung schwach
15    ai=4  akos 0075    gliedmassen     100,0 %     nein (0/2096)     +0,0   +1,5   0,97/0,76        ja
15    ai=17 akos 0083    komplett        100,0 %     nein (0/2096)     +0,0   +0,0   0,44/0,99        nein, Deckung schwach
44    ai=1  akos 0002    gliedmassen     78,3 %      ja (46/952)       +0,5   +0,0   0,93/0,88        ja
44    ai=1  akos 0002    gliedmassen     78,3 %      ja (46/952)       +0,5   +1,0   0,96/0,69        ja
44    ai=4  akos 0251    gliedmassen     100,0 %     ja (46/952)       +0,0   +2,0   0,98/0,71        ja
44    ai=4  akos 0251    gliedmassen     -           ja (46/952)       -      -      -                nein, Flaechen passen nicht zusammen (0,39)
44    ai=17 akos 0253    komplett        -           ja (46/952)       -      -      -                nein, Flaechen passen nicht zusammen (0,18)
86    ai=1  akos 0399    gliedmassen     -           nein (0/1376)     -      -      -                nein, Flaechen passen nicht zusammen (0,35)
86    ai=1  akos 0399    gliedmassen     67,4 %      nein (0/1376)     +0,5   +0,0   0,98/0,73        ja
86    ai=3  akos 0424    komplett        100,0 %     nein (0/1376)     +0,0   +0,0   0,96/0,96        ja
86    ai=4  akos 0426    rueckfall-cel0  100,0 %     nein (0/1376)     +0,0   +0,0   0,87/1,00        ja
86    ai=5  akos 0012    komplett        50,9 %      nein (0/1376)     +0,0   +0,0   0,87/0,66        ja
86    ai=19 akos 0437    rueckfall-cel0  -           nein (0/1376)     -      -      -                nein, eine Seite fast leer
86    ai=20 akos 0438    rueckfall-cel0  100,0 %     nein (0/1376)     +0,0   +0,0   0,90/0,80        ja
```

15 von 17 Eintraegen sind belastbar. In x liegt der Versatz zwischen +0,0 und +0,5 Spielpixeln,
in y zwischen +0,0 und +2,0. Getrennt nach Zeichenweg: gliedmassen 10, komplett 2,
Rueckfall auf Cel 0 3. Ein Unterschied zwischen den Zeichenwegen ist nicht erkennbar:
gliedmassen, komplett und der Rueckfall liegen alle im selben Band. Guybrush (akos 0002)
hat in Raum 9 und Raum 44 denselben Betrag (+0,5/+0,5 und +0,5/+1,0), in Raum 15 als
stark verkleinerte Figur ebenfalls (+0,5/0).

### Skalierung

Die gemessenen Skalierungen reichen von 3,9 bis 100,0 Prozent. Der kleinste Wert ist Guybrush in
Raum 15: 13x33 HD-Punkte aus einem 332x856 grossen Kostuem, also 3,9 Prozent, und der Versatz
bleibt dort bei dx +0,5 und dy 0. Ungeskaliert (100 Prozent) liegen die uebrigen Eintraege
ebenfalls bei 0 bis +2 Punkten. Ein eigener Skalierungsfehler ist damit in dieser Messung
nicht sichtbar.

### Scrollen

Nur Raum 44 liefert ein gescrolltes Bild: `xstart = 46` bei 952 Punkten Raumbreite. Raum 9 ist
640 Punkte breit und kann nicht scrollen. Die Raeume 15 (2096) und 86 (1376) sind breit genug,
aber der Sprung setzt den Ego so, dass das Fenster bei 0 steht; ein gescrolltes Bild dieser
beiden Raeume ist mit dem Sprung nicht zu erzeugen. Das ist die offene Stelle dieser Baseline,
nicht ein Messfehler: in Raum 44 aendert der gescrollte Zustand den Versatz nicht
(dx 0 bis +0,5, wie in den ungescrollten Raeumen), der Kameraterm wirkt dort also heute nicht
auf den Kostuemweg.

### Sonderfaelle, die keine Position sind

- **Raum 3 ist nicht messbar.** Es gibt keinen HD-Hintergrund (`hd/backgrounds` fuehrt
  0001_logo, 0002_thx, 0004_chapter1, aber keine 0003); der Lauf meldet `HD: no bg for room 3!`,
  die Raumgroesse steht als `0x480`, `xstart` als 65276, und der Ego steht mit y = -792
  ausserhalb des Bildes. 8-Bit-Vordergrund 0,00 Prozent, HD-Flaeche 0,45 Prozent, kein
  Eintrag mit beiden Flaechen.
- **Durchsichtige Ueberlagerungskostueme** (`akos 0083` in Raum 15, `akos 0253` in Raum 44)
  sind 896x1388 HD-Punkte gross und decken fast nichts. Das Verhaeltnis 8-Bit-Flaeche zu
  HD-Flaeche ist dort 0,39 und 0,18; solche Eintraege werden nicht als Versatz gewertet.
- **Der Rueckfall auf Cel 0** in Raum 86 (`ai=19`, `akos 0437`) zeichnet 72x60 HD-Punkte ohne
  Gegenstueck im 8-Bit-Bild; die 8-Bit-Flaeche ist dort null.
- **Gespiegelte Figuren** kommen in diesen fuenf Aufnahmen nicht vor; alle Eintraege liegen
  auf dem Anker fuer ungespiegelt.

### magenta_check vor der Aenderung

`harness/baseline_magenta.py`, gleiche Binary-Kopie, eigener Aufnahmeordner, 240 Bilder je
Raum, Mitte der Bilderfolge:

```
Raum  jetzt      Referenz (Build 10:07)  Unterschied
----------------------------------------------------
3     0,0 %     nicht enthalten         kein Vergleichswert
9     0,02 %    nicht enthalten         kein Vergleichswert
15    0,01 %    0,86 %                  -0,85 Punkte
44    0,95 %    3,37 %                  -2,42 Punkte
86    0,03 %    8,02 %                  -7,99 Punkte
```

Raum 86 ist der groesste Sprung. Er kommt nicht aus dieser Messung, sondern aus der
Release-Binary selbst: die Referenzwerte stammen vom Build 10:07 (HEAD ca595c97), die hier
gemessene Binary ist vom 13:20 und enthaelt unter anderem 133450b2 (Kostueme in
Pufferkoordinaten). Fuer Raum 3 sagt die Null nichts aus, weil dort nichts gezeichnet wird
(siehe oben).

### Dateien

```
Messlaeufe     projects/comi-hd/work/baseline/runs/raum{3,9,15,44,86}/
               projects/comi-hd/work/baseline/wiederholung/raum{9,44}/
Binary-Kopie   projects/comi-hd/work/baseline/binary/scummvm-bl
Werkzeuge      projects/comi-hd/harness/baseline_binary.py
               projects/comi-hd/harness/baseline_lauf.sh
               projects/comi-hd/harness/baseline_alle.sh
               projects/comi-hd/harness/baseline_auswertung.py
               projects/comi-hd/harness/baseline_magenta.py
               projects/comi-hd/harness/baseline_bilder.py
               projects/comi-hd/harness/baseline_wiederholung_pruefen.py
               projects/comi-hd/harness/baseline_abschnitt.py
Zahlen         projects/comi-hd/reports/vergleich/baseline/versatz.csv
               projects/comi-hd/reports/vergleich/baseline/versatz_wiederholung.csv
               projects/comi-hd/reports/vergleich/baseline/magenta.csv
Bilder         projects/comi-hd/reports/vergleich/baseline/raum{3,9,15,44,86}_sichtblatt.png
               projects/comi-hd/reports/vergleich/baseline/raum{3,9,15,44,86}_komposit.png
```

## Nachmessung Schritt 2: 0 Punkte gegen den Hintergrund, 46 Punkte auf dem Kostuemweg (comi-pruef, 25.10.)

Auftrag war, nach dem Umbau aus `t_f072e2ac` denselben Messlauf zu wiederholen: sitzt die
8-Bit-Ebene jetzt auf dem HD-Hintergrund, auf beiden Achsen, und ist keine neue Dopplung
entstanden. Ergebnis vorweg: der Versatz gegen den HD-Hintergrund ist weg (98,9 Prozent der
eingeklebten Punkte lesen die Pufferspalte 46 statt 0), und der HD-Kostuemweg ist jetzt die
Stelle, die 46 Punkte daneben liegt. Dazu kommt ein 8-Bit-Objekt am rechten Rand (Person,
Objekt 849), das gar nicht mehr eingeklebt wird.

### Messaufbau

Zwei Laeufe, je ein Bildstand, ohne `HD_TINT_8BIT` (die Einfaerbung macht jeden exakten
Farbvergleich unbrauchbar):

```
Binary nachher  scummvm/fork/scummvm, 25.10. 15:25, sha256 769b848c... (Commit 12f1a869)
Binary vorher   release/linux/scummvm, 25.10. 13:20, sha256 25b2c5b5... (ein Commit davor;
                laut git log hat seit 12:00 nur 12f1a869 scummvm/fork angefasst)
Aufruf          HD_JUMP_ROOM=<raum> HD_FIXED_DELTA=20 HD_EXIT_AFTER=120
                HD_DUMP_STEPS=1 HD_DUMP_SEQ=1 HD_DUMP_REF=1, timeout -k 5 240
Aufnahme         work/nachmesse_schritt2/nachher_raum44, .../vorher_raum44
                 (je vier Stufen, hd_ref, 40 h/r-Paare, Protokoll)
Raum 44          hdgeom: scale=4 camX=184 camY=0 room=952x480 comp=2560x1920 xstart=46
```

Beide Laeufe benutzen eine Kopie der Binary mit eigenen Aufnahmepfaden
(`harness/objektpfad/na_nachmesse_binary.py`, Praefixe `k44` und `k4a`), weil die Pfade im
Binary fest verdrahtet sind und im selben Verzeichnis parallel laufende Aufgaben sich sonst
die Bilder loeschen. Zwei Fallen dabei: die Engine legt das seq-Verzeichnis nicht an und
schreibt ohne es stillschweigend nichts, und die Stufendateien heissen nach dem Patchen
`<praefix>stufe1_hintergrund.ppm` (der Unterstrich von `hd_step_` faellt weg).

### Spaltenherkunft: 46, nicht 0

`paste_herkunft.py` sucht s in 0..80 und vergleicht `s2[y,x]` mit `r[y,x-s]`. Nach dem Umbau
liegt die Quelle rechts der Kompositspalte, das waere s = -46 und damit ausserhalb des
Bereichs. Deshalb `harness/objektpfad/na_herkunft_bereich.py`, das direkt d sucht mit
`s2[y,x] == r[y,x+d]` (d = Quellspalte minus Kompositspalte) und beide Achsen prueft:

```
                                   nachher                vorher
eingeklebt (Stufe 1 gegen 2)   11.412 = 3,71 %        32.191 = 10,48 %
d = +46 (Fensterspalte)         98,9 / 97,5 / 95,4 %     3,3 %
d = 0 (gleiche Spalte)           2,7 /  2,8 /  2,8 %    98,7 / 96,9 / 94,5 %
d = +40                          27,5 %                   3,7 %
d = -46                           0,1 %                   3,4 %
senkrecht bestes dy              0 (98,9 %)               0 (98,7 %)
```

Drei Pufferbilder je Lauf (`r00039`, `r00038`, `r00036`); die Restluemmel unter 100 Prozent
kommen daher, dass die Bildfolge jede dritte Komposition schreibt, die Stufen aber jedes
Bild, die beiden Bilder also zwei Kompositionen auseinanderliegen. Exakt ohne diesen Abstand:
Stufe 2 gegen `hd_ref` desselben Bildes 100,0 Prozent bei d = 0, und `hd_ref` gegen
`r00039` 99,8 Prozent bei 46 Spalten Versatz. Die Kette ist damit geschlossen: der Komposit
liest die Pufferspalte, die 46 Spalten rechts von seiner eigenen Spalte liegt.

### Ueberklebt je Kasten (gegenprobe44.py)

`harness/objektpfad/na_gegenprobe.py` mit denselben Kaesten und Kamera 46:

```
                                     richtig        eine Kamerabreite rechts
                                     nachher/vorher     nachher/vorher
Kanone (Objekt 850)                  28,5 / 11,6 %      14,9 / 35,2 %
Bootsteile links (Objekt 848)         0,5 /  0,6 %       0,1 /  0,6 %
Person rechts (Objekt 849)            0,0 / 20,0 %       0,0 / 91,4 %
Figur Guybrush (Raum 366)            42,2 /  9,4 %       5,0 / 42,2 %
Objektschritt (Stufe 2 gegen 3)          0 / 0 Punkte
Kostuemschritt (Stufe 3 gegen 4)    25.184 / 18.439 Punkte
```

Kanone und Figur sind die zwei Kaesten, die die Abnahme verlangt: richtig deutlich ueber dem
Vorherwert, eine Kamerabreite rechts deutlich darunter. Der Kasten "Person rechts" erfuellt
die Abnahme nicht, und zwar nicht wegen eines Versatzes: dort wird ueberhaupt nichts mehr
eingeklebt (0,00 Prozent in beiden Lagen). Die Spaltenverteilung zeigt, dass der rechte Rand
komplett leer ausgeht:

```
Band                       nachher      vorher
500..549                    11,92 %      5,53 %
550..599                     0,00 %     22,02 %
600..649                     0,00 %     93,18 %
554..594 (Person richtig)    0,00 %     12,65 %
600..640 (Person +46)        0,00 %     93,18 %
```

Die Person ist eine 8-Bit-Objektdarstellung ohne HD-Textur (Objekt 848/849/850 haben laut
`t_cf9ce439` keine). Sie liegt in der Vergleichsvorlage, weil die Vorlage nach dem Zeichnen
der Raumobjekte aufgenommen wird; mit nun ausgerichteter Vorlage gilt sie als Hintergrund und
wird nicht mehr eingeklebt, und die Fehlt-Maske greift nicht, weil ihre Sichtbarkeitspruefung
gegen dieselbe Vorlage laeuft (null Unterschied, also "nicht sichtbar"). Vorher wurde sie
eingeklebt, weil die versetzte Vorlage fast das ganze Bild als Vordergrund auswies
(8-Bit-Anteil 10,48 statt 3,71 Prozent).
Im Sichtbild heisst das: vorher steht die Person da (46 Punkte zu weit rechts), nachher fehlt
sie. Das ist keine Dopplung, aber eine Luecke an derselben Stelle.

### Kostuemweg: jetzt 46 Punkte daneben

`na_gegenprobe.py` vergleicht in der Region Spalten 250..470, Zeilen 150..400 die Spalten von
8-Bit-Ebene (Stufe 2 gegen 1) und Kostuemschritt (Stufe 4 gegen 3):

```
                              nachher                     vorher
8-Bit-Spalten q05/med/q95     296 / 321 / 349            342 / 367 / 396
Kostuem-Spalten q05/med/q95   345 / 376 / 463            341 / 387 / 466
bester Versatz 8 Bit/Kostuem  +46 (Korrelation 0,931)     -2 (Korrelation 0,671)
Ueberlappung bei dx=0            386 Punkte               1.696 Punkte (bester Wert)
Ueberlappung bester Versatz    5.145 bei dx=-46           -
```

Die 8-Bit-Figur ist mit dem Umbau 46 Punkte nach links gewandert (Median 367 auf 321), der
HD-Kostuemschritt bleibt an seiner Stelle (Median 387 auf 376, also 11 Punkte durch die andere
Animationsphase, waehrend die 8-Bit-Figur 46 wandert). Beide Flaechen deckten sich vorher
(Ueberlappung 1.696 Punkte bei dx=0, das war der beste Wert), jetzt decken sie sich erst bei
46 Punkten Versatz (5.145 Punkte, bei dx=0 nur 386). Damit steht die im Auftrag genannte
Gegenrichtung: der Kostuemweg
muss den Kameraversatz wieder abziehen, sonst liegt das HD-Kostuem eine Kamerabreite neben
der 8-Bit-Figur. Im Sichtbild `reports/vergleich/raum44_nachmesse_schritt2_figur.png` stehen
zwei Guybrush nebeneinander, im Vorherbild einer.

### Raeume ohne Kameraversatz

`na_herkunft_bereich.py`, neues Binary, dieselben Schalter:

```
Raum 13   eingeklebt  4.131 = 1,34 %   d=0: 86,2 %   d=+46: 0,7 %
Raum 30   eingeklebt  1.820 = 0,59 %   d=0: 97,7 %   d=+46: 0,0 %
Raum 47   eingeklebt  2.870 = 0,93 %   d=0: 100,0 %  d=+46: 0,3 %
```

Alle drei Raeume haben `xstart=0` und `camX=0` (`hdgeom`), lesen also ab Spalte 0 wie vorher.
Raum 13 liegt mit 86,2 Prozent unter 100, weil die Bildfolge dort zwei Kompositionen hinter
dem Stufenbild liegt (Animationsphase), nicht wegen eines Versatzes.

### Nebenbefund: der Komposit zeigt ein anderes Fenster als die 8-Bit-Ebene

Beim Pruefen, welche Raumspalte in Pufferspalte 0 steht, kam heraus, dass der Komposit
insgesamt 46 Spalten weiter rechts steht als der 8-Bit-Bildschirm:

```
Puffer (r00039) gegen HD-Raumbild 0044   Gipfel dx=0,   NCC 0,6076   (dx=46: 0,1732)
Puffer gegen Kompositstufe 1             Gipfel dx=46,  NCC 0,8412   (dx=0:  0,2114)
```

Pufferspalte 0 ist also Raumspalte 0, Kompositspalte 0 ist Raumspalte 46
(`srcBgX = camX = 184` bei Faktor 4). Der Umbau hat die 8-Bit-Ebene an den HD-Hintergrund
herangezogen, nicht den HD-Hintergrund an die 8-Bit-Ebene; im Spiel zeigt der HD-Modus damit
ein um eine Kamerabreite anderes Fenster als der 8-Bit-Modus. Ob `hdWindowLeft` in diesem
Zustand (Raumsprung per `HD_JUMP_ROOM`, `xstart` 46, `camX` 184) den richtigen Wert liefert,
ist mit diesem Lauf nicht entschieden; die Pufferspalte 0 ist jedenfalls Raumspalte 0, gemessen
an drei unabhaengigen Treffern (NCC 0,61 gegen 0,17).

### Dateien

```
Laeufe          projects/comi-hd/work/nachmesse_schritt2/{nachher,vorher}_raum44,
                .../nachher_raum13, .../nachher_raum30, .../nachher_raum47
Zahlen          je Lauf herkunft.json, gegenprobe.json
Sichtbilder     projects/comi-hd/reports/vergleich/raum44_nachmesse_schritt2_{kanone_rand,
                figur,rand}.png
Werkzeuge       harness/objektpfad/na_nachmesse_binary.py, na_nachmesse_lauf.sh,
                na_herkunft_bereich.py, na_gegenprobe.py, na_verteilung.py,
                na_puffer_shift.py, na_rand.py, na_sicht.py
```

### Was offen bleibt

1. Kostuemweg (und damit auch der Objektweg, in Raum 44 nicht messbar weil ohne HD-Textur):
   muss den Kameraversatz abziehen, sonst 46 Punkte Dopplung in der Gegenrichtung.
2. Objekte ohne HD-Textur, die in der Vergleichsvorlage liegen (Person rechts, Objekt 849):
   werden nicht mehr gezeichnet. Entweder HD-Textur oder die Fehlt-Maske muss ihre
   Sichtbarkeit anders bestimmen als gegen die Vorlage, die sie selbst enthaelt.
3. Fensterlage: ob der HD-Hintergrund um `camX` versetzt gehoert, ist mit diesem Lauf nicht
   entschieden (siehe Nebenbefund).

## Universelle Kostuemposition: eine Formel, sdLeft und sdTop (t_29af929e, 25.10.2026)

Stand: `12f1a869` plus die Aenderung dieser Karte. Der HD-Kostuemanker in Schritt 2.6
(`gfx.cpp:2915-2976`) rechnet jetzt in Raumkoordinaten, mit demselben Fensteranfang wie
Hintergrund, Objekte und 8-Bit-Ebene:

```
vorher   drawY = pos.y - elevation - (_roomHeight > _screenHeight ? camera._cur.y : 0)
         hdCX  = (pos.x + limbDrawX * sclX / 255) * hdW / visW
nachher  drawX = pos.x - sdLeft
         drawY = pos.y - elevation - sdTop
         hdCX  = (drawX + limbDrawX * sclX / 255) * hdW / visW
```

`sdLeft`/`sdTop` sind `gfx.cpp:1588` und `1603`, dieselben zwei Werte, aus denen die
Hintergrundkopie (`1673-1686`, `srcBgX = camX`), die Objekte (`1751-1752`, `2274-2275`) und seit
`12f1a869` die 8-Bit-Ebene (`1828`) lesen. Es kommt keine neue Groesse dazu; der Sonderfall
`_roomHeight > _screenHeight` faellt weg, weil `sdTop` in normalen Raeumen 0 ist. Es gibt
weiterhin genau eine Positionierungsstelle: beide Zeichenwege (complete-character ueber
`_hdRelX/_hdRelY`, per-limb ueber `_hdLimbDrawX/Y`, dazu der Rueckfall auf Cel 0) fuellen nur
`drawX/drawY` der Eintraege und laufen danach durch dieselbe Zeile. Keine Raum-, Figuren- oder
Kostuemnummer steht in der Rechnung.

### Messung vorher gegen nachher

Beide Laeufe aus demselben Objektbaum, nur `gfx.cpp` verschieden (`vorher` md5
b1b2108c3f92344d87d7d6759864b206, `nachher` 8fa4b0d41d9094a283cad90cb58f5258), je Raum ein
Lauf, Bild 119, Versatz per Kreuzkorrelation (`harness/baseline_auswertung.py`):

```
Raum  Lage                      vorher                                nachher
3     kein HD-Hintergrund       0 bel.                                0 bel. (Raum 87 geladen)
9     640x480, sdLeft 0         5 bel. dx +0,0..+0,5 dy +0,0..+1,0     5 bel. identisch
15    2096x480, sdLeft 0        2 bel. dx +0,0..+0,5 dy +0,0..+1,5     2 bel. dx +0,0..+0,5 dy +0,0..+2,0
44    952x480, sdLeft 46        0 bel. Deckung 0,10..0,29             3 bel. dx +0,0..+0,5 dy +0,0..+2,0 Deckung 0,92..0,98
86    1376x480, sdLeft 0        5 bel. dx +0,0..+0,5 dy +0,0           5 bel. identisch
77    640x987, sdTop 507        0 bel. Kostuem am oberen Rand          2 bel. dx +0,0..+0,5 dy +0,0..+0,5
40    1200x1200, Kamera laeuft  0 bel.                                1 bel. (nicht verwertbar, s. unten)
```

Der Anker selbst im Protokoll des Zeichenschritts:

```
Raum 44, actor 1, costume 0002, cel 22:  hd=(1340,576) vorher  ->  hd=(1156,576) nachher
                                          (-184 HD = -46 Spielspalten = sdLeft)
Raum 77, actor 9, costume 0380, cel 3:   hd=(536,4)    vorher  ->  hd=(536,964)  nachher
                                          (+960 HD = +240 Spielpixel = halbe Bildschirmhoehe,
                                           camera._cur.y war die Fenstermitte, sdTop ist der Anfang)
```

Magenta-Anteil (8-Bit-Ebene, die durch die HD-Ebene durchscheint; kleiner ist besser):

```
Raum  vorher  nachher  Baseline 13:20
9     0,02    0,02     0,02
15    0,01    0,01     0,01
44    2,09    0,12     0,95
86    0,03    0,03     0,03
```

Die 2,09 statt 0,95 in Raum 44 sind der Zustand nach `12f1a869`: solange beide Ebenen gemeinsam
verschoben waren, verdeckte die Dopplung sich selbst.

### Was diese Messung nicht belegt

- Raum 40: die beiden Laeufe landen in verschiedenen Kamerapositionen (`xstart` 0 gegen 241,
  `camY` 24/92/0), der einzige belastbare Eintrag ist der Rueckfall auf Cel 0 bei einem Akteur
  oberhalb des Fensters (`hd=(1116,-264)`), sein `dy` 9,0 ist nicht als Rechenfehler lesbar.
  Fuer die senkrechte Haelfte traegt Raum 77.
- Raum 3 bleibt nicht messbar (kein HD-Hintergrund, Raum 87 geladen), wie in der Baseline.
- Gespiegelt und zugleich skaliert ist weiterhin nicht gemessen; die Aenderung beruehrt den
  Spiegelanker (`2974`) nicht.
- Je Raum ein Bild. Andere Momente, andere Kamera, Zwischensequenzen sind nicht abgedeckt.
- Die Pufferkonvention (Pufferspalte = Raumspalte) ist weiter nur aus `12f1a869` belegt.

### Dateien

```
Werkzeuge   harness/positionierung_binary.py, positionierung_lauf.sh,
            positionierung_alle.sh, positionierung_magenta.py, positionierung_magenta_lauf.sh
Laeufe      projects/comi-hd/work/positionierung/runs/{vor,nach}_raum{3,9,15,40,44,77,86}
Zahlen      work/positionierung/versatz.csv, magenta_vor.csv, magenta_nach.csv
Bericht     projects/comi-hd/reports/positionierung-fix.md
```


## Kostuemweg auf der 8-Bit-Figur: Gegenprobe und Referenzfrage (comi-bau, 25.10.)

Auftrag aus `t_e8142b29`: nach dem Umbau aus `12f1a869` lag der HD-Kostuemweg eine
Kamerabreite neben der 8-Bit-Figur. Die Code-Aenderung ist inzwischen als `82ca6baa`
committet (Karte `t_29af929e`, Abschnitt darueber); dieser Abschnitt ist die unabhaengige
Gegenprobe dazu aus der Sicht der beiden sichtbaren Ebenen, plus die Entscheidung der in der
Karte offenen Frage, welche Ebene die Referenz ist.

Ergebnis vorweg: in Raum 44 decken sich 8-Bit-Figur und HD-Kostuem wieder bei dx = 0
(1.685 Punkte Ueberlappung, im Sichtbild ein Guybrush), die Raeume 13, 30 und 47 bleiben bei
d = 0, der 8-Bit-Anteil in Raum 44 bleibt bei 11.412 Punkten (3,71 Prozent).

### Welche Ebene die Referenz ist

HD-Hintergrund und eingeklebte 8-Bit-Ebene zeigen an derselben Kompositspalte denselben
Rauminhalt. Damit war der Kostuemweg die einzige Ebene mit falschem Ursprung, und der Abzug
ist die richtige Richtung. Die Alternative aus der Karte (Fensterlage von Hintergrund und
Schritt 2 korrigieren) ist damit widerlegt.

`harness/objektpfad/paste_auf_hintergrund.py` vergleicht die eingeklebten 8-Bit-Punkte
(Stufe 2 gegen 1) mit dem HD-Hintergrund an derselben Kompositspalte und sucht den
Spaltenversatz mit dem kleinsten Median-Farbabstand. Beide Ebenen zeigen dieselbe Szene, nur
einmal in Palettenfarben; steht die 8-Bit-Ebene auf der falschen Raumstelle, waechst der
Abstand.

```
Raum 44, 11.412 eingeklebte Punkte   Median-Farbabstand (kleiner ist besser)
d = +0    91,0  (bester Wert)        d = +40   107,0
d = -6    98,0                       d = +50   112,0
d = +6    95,0                       d = +70   108,0
```

Der Umbau aus `12f1a869` ist damit gegen eine unabhaengige Groesse bestaetigt: die 8-Bit-Ebene
sitzt auf dem Hintergrundinhalt, nicht eine Kamerabreite daneben. Die Pufferspalte traegt in
diesem Zustand dieselbe Raumspalte wie die Kompositspalte (Pufferspalte 0 = Raumspalte 0,
gemessen im Abschnitt "Nachmessung Schritt 2"), deshalb liest Schritt 2 ab `sdLeft`, und der
Kostuemanker muss denselben Wert abziehen. Der 8-Bit-Zeichner rechnet genauso
(`_actorX = _pos.x - xstart`, `actor.cpp:2572`); in Raum 44 steht `xstart` = `sdLeft` = 46
(`hdgeom`).

Was die Messung nicht entscheidet: ob die Fensterlage in einem echten Spielverlauf mit
laufender Kamera genauso aussieht. Der Sprunglauf hat einen Puffer, der 1:1 zum Raum steht,
waehrend Objekt- und Figurenzeichnung `xstart` abziehen; dieser Zustand ist kuenstlich. Ein
echter Spielverlauf mit scrollender Kamera fehlt weiterhin.

### Raum 44, Kamera 46, beide Ebenen gegeneinander

`harness/objektpfad/na_gegenprobe.py` mit Kamera 46, Region Spalten 250 bis 470, Zeilen 150
bis 400, dieselben Schalter wie in der Nachmessung. Der Vergleich ist ein anderer als der in
`t_29af929e`: dort Kostuem gegen 8-Bit-Silhouette pixelweise je Figur, hier die beiden
Differenzmasken (Stufe 2 gegen 1 und Stufe 4 gegen 3) gegeneinander.

```
                                   mit Fix        ohne Fix (nachher)
8-Bit-Spalten q05/med/q95          296/321/349    296/321/349
Kostuem-Spalten q05/med/q95        295/339/452    345/376/463
bester Versatz 8 Bit/Kostuem       -1 (0,778)     +46 (0,931)
Ueberlappung bei dx=0              1.685          386
bester 2D-Versatz                  dx=0 dy=0      dx=-46 dy=0
                                   (1.685)        (5.145)
Kostuem mit 8-Bit darunter (5x5)   62,3 %         11,3 %
8-Bit unter Kostuem                28,4 %          6,5 %
```

Der Vorher-Stand (Lauf vor `12f1a869`) hatte 1.696 Punkte bei dx = 0. Die 11 Punkte Differenz
sind die Animationsphase, die schon in der Nachmessung im Kostuemschritt stand (Spaltenmedian
387 im Vorherlauf gegen 376 im Nachherlauf); die 8-Bit-Spalten sind in allen drei Laeufen
dieselben. Ueber das ganze Bild statt nur der Figurenregion liegt der beste Versatz bei
dx = +1 (3.948 gegen 3.832 Punkte bei dx = 0), also im Rahmen des einen Spielpixels, das die
frueheren Messungen schon als Rest hatten.

Beleg, dass das Kostuem ueber der 8-Bit-Silhouette liegt und nicht darunter: in den Spalten
280 bis 360 aendert der Kostuemschritt 2.859 der 6.741 8-Bit-Punkte (42 Prozent). Waere die
Reihenfolge umgekehrt, waere dort 0.

Die Punktzahl des Kostuemschritts (Stufe 4 gegen 3) faellt in Raum 44 von 25.184 auf 9.730.
Das ist ein Artefakt der Maske, kein Verlust an Flaeche: gezaehlt wird nur, was sich aendert,
und wo das Kostuem jetzt auf der 8-Bit-Silhouette liegt (Kostuem mit 8-Bit darunter 11,3 auf
62,3 Prozent), ist der Farbunterschied klein. Die Lage beschreibt die Ueberlappung, und die
ist bei dx = 0 am groessten.

Sichtbild `reports/vergleich/raum44_kostfix_figur.png` (Komposit mit Fix, nur 8-Bit-Ebene,
Komposit ohne Fix, HD-Hintergrund): ein Guybrush im Feld mit Fix, zwei im Feld ohne Fix.
`reports/vergleich/raum44_kostfix_kanone_rand.png` zeigt denselben Kanonenkasten wie in der
Nachmessung (28,5 Prozent richtig, 14,9 eine Kamerabreite rechts), also keine neue Baustelle
am Rand.

### Raeume ohne Kameraversatz

`na_herkunft_bereich.py`, Binary mit eigener Kopie der Aenderung, dieselben Schalter:

```
Raum 13   eingeklebt 4.131 = 1,34 %   d=0: 86,2 / 77,3 / 48,9 %   d=+46: 0,7 %
Raum 30   eingeklebt 1.840 = 0,60 %   d=0: 98,3 %                 d=+46: 0,0 %
Raum 47   eingeklebt 2.870 = 0,93 %   d=0: 100,0 %                d=+46: 0,3 %
```

Alle drei Raeume haben `camX = 0` und `xstart = 0`, die Aenderung ist dort wirkungslos. Die
drei Zahlen fuer Raum 13 sind die drei ausgewerteten Pufferbilder; das erste ist mit 86,2
Prozent genau der Wert aus der Nachmessung, die beiden anderen liegen zwei beziehungsweise
drei Kompositionen daneben (Animationsphase).

### Kontrolllauf mit der Binary aus dem Commit

Die Zahlen oben stammen aus einer Binary mit eigener Kopie der Aenderung
(`scummvm-k46`, Arbeitsbaum 15:58). Zur Kontrolle danach der Baum auf `82ca6baa`, neu
gebaut (`scummvm/fork/scummvm`, 16:22, sha256 `b6ad6b62...`) und Raum 44 mit eigener
Messbinary wiederholt (`kost_raum44_commit`): 8-Bit 5.926 Punkte, Kostuem 3.667 Punkte,
Ueberlappung bei dx=0 1.685, bester 2D-Versatz dx=0 dy=0, Kostuem mit 8-Bit darunter 62,3
Prozent, Kanonenkasten 28,5/14,9, Figur 42,2/5,0. Punktgleich mit dem Lauf aus der eigenen
Kopie, die Aenderung im Commit ist also dieselbe Rechnung.

### Objektweg (Schritt 2.5)

Der Objektweg zeichnet mit `xPos = od.x_pos - sdLeft` (unveraendert seit `t_24d94474`); der
Umbau aus `12f1a869` hat in diesem Pfad nur die 8-Bit-Lesestellen der beiden
Sichtbarkeitspruefungen umgestellt. In Raum 61 mit `HD_SCROLL_TEST` und Kamera 56
(`sdLeft` = 56, `xstart` = 56) zeichnet der Objektschritt trotzdem 0 Punkte, gemessen ueber
die Stufe 3 gegen 2:

```
8-Bit-Ebene       17 Punkte, Quelle d=+56 (64,7 Prozent), d=0 0,0 Prozent
Objektschritt      0 Punkte
Zeichenprotokoll   0 "DRAW objekt", 108 "SKIP obj=188/189 verdeckt"
```

Damit ist der Objektweg in diesem Zustand nicht messbar, weder als Deckungs- noch als
Versatzprobe. Dazu passt, dass beide Sichtbarkeitspruefungen heute dieselbe Pufferspalte
lesen, eine Kamerabreite neben dem Objekt: Zeile 2440 rechnet `sx = od.x_pos - sdLeft + xx`
und liest bei `getBasePtr(sdX + sx, ...)`, also Pufferspalte `sdX + od.x_pos - sdLeft + xx`,
und im Sprunglauf ist `sdX == sdLeft`, damit bleibt `od.x_pos + xx`; Zeile 2469 rechnet
`sx8 = od.x_pos + xx` und liest bei `getBasePtr(0, ...)`, also dieselbe Spalte. `t_24d94474`
hat in Raum 61 bei Kamera 56 gemessen, dass mit `od.x_pos + xx` kein Objekt laedt und mit
`od.x_pos - sdLeft + xx` zwei, und beide liegen dann pixelgenau im Hintergrund (0 veraenderte
Punkte). Diese zwei Zeilen sind nicht committet; der Widerspruch zu meiner Hintergrundprobe
(Pufferspalte = Raumspalte in Raum 44) ist erst mit der Strip-Ablage zu loesen (xstart gegen
`xstart & ~7`), siehe Folgekarte zu diesem Befund.

### Senkrechte Achse

In den hohen Raeumen, die ich dafuer aufgenommen habe, gab es kein Bild mit HD-Kostuem und
8-Bit-Figur zugleich, deshalb traegt hier die Messung aus `t_29af929e` (Raum 77, `sdTop` 507:
Anker `hd=(536,4)` vorher, `hd=(536,964)` nachher, also 240 Spielpixel nach unten, Deckung
0,89/0,94). Meine Laeufe, damit die Zahlen nicht als Luecke gelesen werden:

```
Raum 79   Raum 640x2044, camY 832 (sdTop 208)   8-Bit 0 Punkte, Kostuem 0 Punkte
Raum 77   Raum 640x987,  camY 896 (sdTop 224)   8-Bit 10 Punkte, Kostuem 44 Punkte
Raum 82   Raum 640x997,  camY 864 (sdTop 216)   8-Bit 11.831 Punkte, Kostuem 0 Punkte
```

In Raum 77 liegen die 9 gemeinsamen Punkte bei dx=0 dy=0; bei dieser Punktzahl ist das keine
Messung, sondern nur kein Widerspruch.

### Messaufbau

```
Binary           scummvm/fork/scummvm, 25.10. 15:58, sha256 63502a42... (Arbeitsbaum auf
                 12f1a869 mit eigener Kopie der Aenderung), Kontrolllauf 16:22,
                 sha256 b6ad6b62... (Baum auf 82ca6baa)
Messbinary       projects/comi-hd/work/engine/scummvm-k46 und scummvm-k48 (Praefixe k46,
                 k48, na_nachmesse_binary.py; eigene Aufnahmepfade)
Aufruf           HD_JUMP_ROOM=<raum> HD_FIXED_DELTA=20 HD_EXIT_AFTER=120
                 HD_DUMP_STEPS=1 HD_DUMP_SEQ=1 HD_DUMP_REF=1, timeout -k 5 240,
                 fuer Raum 61 zusaetzlich HD_SCROLL_TEST=1
Raum 44          hdgeom: scale=4 camX=184 camY=0 room=952x480 comp=2560x1920 xstart=46
Raum 61          hdgeom: scale=4 camX=224 camY=0 room=1024x480 comp=2560x1920 xstart=56
```

Die Laeufe sind mit einem Warteschritt gestartet, der auf fremde `scummvm`-Prozesse wartet
(Projektregel: ein Prozess); waehrend der Messreihe lief zeitweise trotzdem ein zweiter
Prozess einer anderen Aufgabe. Die Zahlen sind deshalb gegen die Nachmessung gestellt und
stimmen dort ueberein, wo sie muessen (Raum 13 86,2 Prozent, Raum 47 100,0 Prozent,
8-Bit-Anteil Raum 44 11.412 Punkte, Kanonenkasten 28,5/14,9).

### Dateien

```
Laeufe          projects/comi-hd/work/nachmesse_schritt2/kost_raum44, kost_raum44_commit,
                kost_raum13, kost_raum30, kost_raum47, kost_raum61_scroll,
                kost_raum61_trace, kost_raum77_scroll, kost_raum79_scroll,
                kost_raum82_scroll
Zahlen          je Lauf gegenprobe.json, herkunft.json, objektweg.json,
                paste_auf_hintergrund.json, kost_versatz_2d.json
Sichtbilder     projects/comi-hd/reports/vergleich/raum44_kostfix_{figur,kanone_rand}.png
Werkzeuge       harness/objektpfad/{na_gegenprobe,na_herkunft_bereich,na_sicht,
                paste_auf_hintergrund,objekt_weg_gegenprobe,kost_versatz_2d,
                kost_querschnitt}.py, na_nachmesse_binary.py, na_nachmesse_lauf.sh
```

### Was offen bleibt

1. Objektweg: in Raum 61 wird bei Kamera 56 kein HD-Objekt gezeichnet, weil beide
   Sichtbarkeitspruefungen noch in der alten Spalte lesen (`od.x_pos + xx`). Mit
   `od.x_pos - sdLeft + xx` zeichnen zwei Objekte und liegen pixelgenau. Zwei Zeilen, eigener
   Beleg noetig (Raum 61, Kamera 0 gegen Kamera 56).
2. Fensterlage in einem echten Spielverlauf mit laufender Kamera: offen. Der Sprunglauf hat
   einen Puffer, der 1:1 zum Raum steht, und `xstart` = `sdLeft`; ob das beim Scrollen im
   Spiel auch gilt, entscheidet erst eine Aufnahme mit laufendem Ego.

## Objektweg Raum 61: die Spalten sind richtig, der CULL verwirft das Objekt (t_8040c289)

Die Folgekarte zu Punkt 1 oben hat die fehlende Messung nachgeholt. Ergebnis: die beiden
Sichtbarkeitspruefungen lesen die richtige Pufferspalte, die zwei Zeilen aus t_24d94474
duerfen nicht angewendet werden. Der Ausfall in Raum 61 hat eine andere Ursache.

### Pufferspalte ist Raumspalte, auch bei laufender Kamera

Rohpuffer (`r*.ppm`, Pufferspalte 0 = Bildspalte 0) gegen `0061_hotelbar.png` (auf 1x
verkleinert), Graustufen-NCC, Kamera 56, zwei Laeufe (16:14 ohne Sonde, 16:47 mit Sonde):

```
Pufferspalte 120..280 -> Raumspalte 120  Versatz +0  NCC 0,989  (Nachbar -1/+1: 0,881/0,871)
Pufferspalte 300..460 -> Raumspalte 300  Versatz +0  NCC 0,775
Pufferspalte 440..580 -> Raumspalte 440  Versatz +0  NCC 0,741
```

Die HD-Objektdatei `0061_hotelbar-hand_0000.png` im Rohpuffer gesucht, ganzes Bild:

```
bester Treffer  Pufferspalte 424  Zeile 240  NCC 0,915   (= od.x_pos, od.y_pos)
Kontrolle       Pufferspalte 368  Zeile 240  NCC 0,191   (= od.x_pos - sdLeft, Spalte der Karte)
```

Das 8-Bit-Objekt steht also auf Pufferspalte 424, seiner Raumspalte. `sx = od.x_pos - sdLeft
+ xx` bei `getBasePtr(sdX + sx)` und `sx8 = od.x_pos + xx` bei `getBasePtr(0) + sx8` landen
beide auf `od.x_pos + xx`, weil `sdX == sdLeft`; das ist die gemessene richtige Spalte.

### In-engine nachgemessen (Sonde HD_OBJCHK, wieder entfernt)

Lauf 16:47, eigenes Binary aus `82ca6baa`, `HD_JUMP_ROOM=61 HD_SCROLL_TEST=1
HD_FIXED_DELTA=20 HD_EXIT_AFTER=140`, Kamera 0 ab Bild 44, Kamera 56 ab Bild 90. Je Bild und
Objekt die Zahlen der drei Instanzen, dazu die Spalte der Karte als Gegenprobe:

```
Kamera 0   Objekt 1005 pos (424,240)  cull vis=336 thr=2  kasten diff=21/80  textur 93 %
Kamera 56  dasselbe Objekt            cull vis=336 thr=2  kasten diff=21/80  textur 93 %  karte 55 %
```

Kastenabgleich und Texturabgleich sind kamerafest (identische Zahlen bei sd=0 und sd=56). Die
Spalte der Karte senkt den Texturabgleich im selben Bild von 93 auf 55 Prozent: sie liest
nachweislich den falschen Bildinhalt. Dass sie in t_24d94474 "loaded=2" ergab, liegt allein
daran, dass 55 Prozent ueber der Schwelle von 35 liegen.

### Der Ausfall kommt aus dem CULL-Schritt

Der CULL (gfx.cpp:2287) zaehlt im Objektkasten die Pufferpixel, die sich von
`_hdCleanBackground` unterscheiden, und verwirft unter 2 Pixeln. Je Kameraposition, 140
Bilder, Objekt 1005:

```
sd=0     13 Bilder   0 culled  13 gezeichnet
sd=4..9   3 Bilder   0 culled   3 gezeichnet
sd=10..52 12 Bilder 10 culled   2 gezeichnet
sd=56    68 Bilder  54 culled  14 gezeichnet
```

Auf den verworfenen Bildern ist `sampled=80` (alle Stichproben hatten eine gueltige Vorlage)
und `vis=0`: Puffer und Vorlage stimmen im ganzen Kasten ueberein, die Vorlage enthaelt das
Objekt also selbst. Sie entsteht in `redrawBGAreas` nach `drawRoomObjects` ueber
`hdRefreshCleanBackground()` und soll laut Kommentar dort den Hintergrund samt den
Raumobjekten enthalten. Fuer ein Raumobjekt, dessen HD-Textur aus dem Hintergrund geschnitten
ist, ist "kein Unterschied zur Vorlage" der Normalfall und kein Beweis fuer Unsichtbarkeit.
Gezeichnet wird nur das Bild, in dem die Vorlage aus anderem Grund nicht mehr passt (1 von 5).
Bei stillstehender Kamera laeuft `redrawBGAreas` nicht, die Vorlage bleibt die vom
Raumbetreten, deshalb dort 0 culled.

### Warum die Abnahme der Karte so nicht messbar ist

Stufe 3 gegen Stufe 2 im letzten Bild: 0 von 1.228.800 Punkten verschieden. Die Texturen sind
aus dem Hintergrund geschnitten, gezeichnet und nicht gezeichnet sehen im Komposit gleich aus.
"0 veraenderte Punkte" belegt daher nichts. Und "0 DRAW objekt" ist die falsche Protokollzeile:
`DRAW objekt` (gfx.cpp:2636) schreibt nur der Inventarpfad 2.5b, Raumobjekte schreiben `VERIFY`
und zaehlen in `step2.5 objects: loaded=`.

### Dateien

```
Messskript offline  projects/comi-hd/harness/objektpfad/objekt_pufferspalte_raum61.py
Laufskript          projects/comi-hd/harness/objektpfad/objpfad_t8040_lauf.sh
Bericht             projects/comi-hd/reports/objektpfad-sichtbarkeit-raum61.md
Laufdaten           projects/comi-hd/work/nachmesse_objpfad_t8040/trace_k50
Vergleichslauf      projects/comi-hd/work/nachmesse_schritt2/kost_raum61_trace
```

Offen und als eigene Aufgabe gefuehrt: der CULL darf fuer Raumobjekte nicht aus "Puffer
gleich Vorlage" auf Unsichtbarkeit schliessen. Kein Pixelunterschied, weil die Texturen aus
dem Hintergrund kommen; sichtbar wird es erst bei Objekten mit eigener HD-Zeichnung.

## Unabhaengige Verifikation des Kostuemankers ueber fuenf Raeume (comi-pruef, 25.10.2026)

Karte `t_0eaca6e2`. Auftrag: den Fix aus `82ca6baa` unabhaengig pruefen, Raeume 3, 9, 15, 44
und 86, beide Zeichenwege, scrollende und stehende Raeume, mit und ohne Skalierung, Zielwert
0 bis 1 Spielpixel je Akteur, dazu `magenta_check` vorher und nachher.

### Aufbau

Nicht die Binaries der Umsetzung uebernommen, sondern selbst gebaut, in einem eigenen
Arbeitsbaum `/opt/data/local/comi-hd-verify` (`git worktree add --detach ... 82ca6baa`), mit
dem Objektbaum aus dem Bau der Umsetzung als Startpunkt:

```
nachher   Quellstand 82ca6baa (Fix in gfx.cpp:2918-2925)     md5 9ebd7e8a74b56cdf381b274234d8a5cd
vorher    derselbe Baum, gfx.cpp aus 12f1a869 (ohne Fix)      md5 424a741de31348840e5ae7d666be501b
```

Beide Binaries unterscheiden sich nur in `gfx.cpp`; jede bekam per
`harness/positionierung_binary.py` ein eigenes Aufnahmepraefix (`vn`, `vv`, fuer die
Magenta-Laeufe `mn`, `mv`), damit sich parallele Laeufe nicht in dieselben Dateien schreiben.

Messung wie in der Umsetzung: ein Lauf je Raum (`HD_JUMP_ROOM`, `HD_FIXED_DELTA=20`,
`HD_DUMP_STEPS=1`, `HD_TINT_8BIT=1`), Auswertung `harness/baseline_auswertung.py`
(Kreuzkorrelation HD-Kostuemflaeche gegen 8-Bit-Silhouette). Alle Zahlen gelten fuer Bild 119.
`dx`/`dy` in Spielpixeln, positiv heisst: die HD-Flaeche steht rechts beziehungsweise unterhalb
der 8-Bit-Silhouette. "Deckung" ist der Anteil der HD-Flaeche, der nach dem Versatz auf der
Silhouette liegt; belastbar ab 0,70.

### Messtabelle nachher (Bild 119)

```
Raum  Fenster          ai  akos  cel  Zeichenweg        Blit       Skal%   dx   dy   Deckung
9     640x480, x 0      1  0002   34  gliedmassen       116x198     76,3   0,0  1,0  0,98
9     640x480, x 0      1  0002   22  gliedmassen       253x654     76,2   0,5  0,5  0,99
9     640x480, x 0     12  0026    0  Rueckfall cel 0  1168x644    100,0   0,0  0,0  0,96
9     640x480, x 0      2  0025  192  gliedmassen       232x376    100,0   0,0  0,0  0,98
9     640x480, x 0      2  0025    5  gliedmassen       352x644    100,0   0,0  0,0  0,98
15    2096x480, x 0    17  0083   15  komplett          896x1388    100,0   0,0  0,0  0,44 (nb)
15    2096x480, x 0     1  0002   22  gliedmassen        13x33       3,9   0,5  0,0  1,00
15    2096x480, x 0     4  0075   68  gliedmassen       232x232    100,0   0,0  1,5  0,97
15    2096x480, x 0     4  0075   67  gliedmassen       624x396    100,0   0,0  0,0  0,60 (nb)
44    952x480, x 46     4  0251    8  gliedmassen       204x220    100,0   0,0  2,0  0,98
44    952x480, x 46     1  0002   34  gliedmassen       119x203     78,3   0,5  1,0  0,96
44    952x480, x 46     1  0002   22  gliedmassen       260x671     78,3   0,5  0,0  0,92
44    952x480, x 46     4  0251   11  gliedmassen       616x432    100,0   0,0  0,0  0,51 (nb)
44    952x480, x 46    17  0253   15  komplett          712x1388    100,0   -    -    Flaechen 0,28 (nb)
86    1376x480, x 0    20  0438    0  Rueckfall cel 0   672x544    100,0   0,0  0,0  0,90
86    1376x480, x 0     5  0012    2  komplett          348x193     50,9   0,0  0,0  0,87
86    1376x480, x 0     4  0426    0  Rueckfall cel 0   620x1072   100,0   0,0  0,0  0,87
86    1376x480, x 0     3  0424   10  komplett          732x644    100,0   0,0  0,0  0,95
86    1376x480, x 0     1  0399   31  gliedmassen       259x402     67,4   0,5  0,0  0,98
```

Alle 15 belastbaren Eintraege liegen zwischen 0,0 und 2,0 Spielpixeln, keiner darueber.
Dreizehn davon liegen bei 0 bis 1 Pixel; zwei liegen darueber, und zwar in `dy`: Raum 44,
ai 4, cel 8 mit 2,0 und Raum 15, ai 4, cel 68 mit 1,5. Beide sind der bekannte Rest der
Rasterung: 2 Spielpixel sind 8 HD-Punkte, und die Kreuzkorrelation laeuft auf dem 2-fach
gezoomten Komposit.

Abdeckung der geforderten Faelle:

```
beide Zeichenwege   komplett: 15 (ai 17), 86 (ai 5, ai 3); gliedmassen: 9, 15, 44, 86 (ai 1)
Rueckfall cel 0     9 (ai 12), 86 (ai 20, ai 4)
mit Skalierung      9 (ai 1, 76 Prozent), 44 (ai 1, 78 Prozent), 86 (ai 5 51, ai 1 67 Prozent)
ohne Skalierung     9 (ai 12, ai 2), 15 (ai 4, ai 17), 44 (ai 4), 86 (ai 20, ai 4, ai 3)
Figuren             Guybrush (ai 1), ai 2, 3, 4, 5, 12, 17, 20
```

Der einzige `komplett`-Fall im gescrollten Raum 44 (ai 17, akos 0253) ist nicht belastbar: die
HD-Flaeche ist mit 712x1388 mehr als dreimal so gross wie die 8-Bit-Silhouette (Verhaeltnis
0,28). Er steht in der Tabelle, traegt aber keine Aussage.

### Vorher gegen nachher

```
Raum 44, Fenster 46 (gescrollt)      vorher                        nachher
ai 4, akos 0251, cel 8               dx 0,0  dy 12,0  Deck 0,12   dx 0,0  dy 2,0  Deck 0,98
ai 1, akos 0002, cel 22              dx 0,0  dy  3,0  Deck 0,10   dx 0,5  dy 0,0  Deck 0,92
```

Im Vorher-Lauf sind nur zwei Eintraege messbar, beide mit Deckung 0,10 bis 0,12: Kostuem und
Silhouette liegen eine Fensterbreite auseinander, die Kreuzkorrelation findet keine gemeinsame
Flaeche. Im Nachher-Lauf sind es drei belastbare Eintraege mit 0,92 bis 0,98. Das ist derselbe
Befund wie in der Umsetzung, mit eigenem Lauf und eigener Binary.

Die Raeume 9, 15 und 86 stehen bei `xstart` 0. Dort ist der Fix rechnerisch wirkungslos
(`sdLeft` = `sdTop` = 0), und beide Laeufe liefern dieselben Zahlen bis auf die letzte Stelle;
das ist die Gegenprobe, dass die Aenderung nichts anderes verschiebt.

### Scrollende Raeume: was messbar ist und was nicht

Der Fensteranfang ist in diesen Laeufen nur in Raum 44 von null verschieden (`xstart` 46). Um
einen groesseren Versatz zu bekommen, zwei weitere Wege probiert, beide ohne verwertbares
Ergebnis:

```
Lauf                                   xstart  Ergebnis
Raum 44, Ego laeuft per FIFO zur Kanone   268  8-Bit-Ebene 0,00 Prozent, alle Eintraege leer
Raum 44, derselbe Lauf kuerzer            268  8-Bit 0,61 Prozent, Flaechenverhaeltnis 0,10..0,23
Raum 15, HD_SCROLL_TEST, 260 Bilder       248  8-Bit 0,06 Prozent, keine Silhouette
Raum 44, HD_SCROLL_TEST                   0    3 Eintraege 0..2 px, aber ohne Fensterversatz
```

Sobald das Fenster weit verschoben ist, pastet der Komposit fast keine 8-Bit-Ebene mehr
(0,06 bis 0,61 statt 1,92 bis 3,84 Prozent), die Magenta-Methode hat dann keine Silhouette
mehr, gegen die sie korrelieren koennte. Das ist eine Grenze des Messaufbaus, kein Befund
ueber den Fix: die 8-Bit-Ebene ist dort vollstaendig von HD bedeckt. Der gescrollte Fall
stuetzt sich deshalb auf Raum 44 bei `xstart` 46, den einzigen in diesen fuenf Raeumen
natuerlich verschobenen Fensteranfang.

### magenta_check vorher und nachher

`harness/positionierung_magenta.py` (derselbe Ablauf wie `harness/magenta_check.py`, nur mit
Binary und Aufnahmeordner als Parameter), 80 Bilder je Raum, Wert aus der Bildmitte:

```
Raum  vorher  nachher
3     0,00    0,00
9     0,02    0,02
15    0,01    0,01
44    2,09    0,12
86    0,03    0,03
```

Raum 44 faellt von 2,09 auf 0,12 Prozent, die vier anderen Raeume stehen still. Im ersten
Nachher-Lauf von Raum 9 stand als Maximum der drei Stichproben 3,91 Prozent; der
Wiederholungslauf ueber alle 80 Bilder ergab Median, Mittel und Maximum 0,02 Prozent. Der
Ausreisser ist damit einmalig und nicht reproduzierbar, und Raum 9 hat keinen
Fensterversatz, aus dem er kommen koennte.

### Raum 3

Raum 3 ist kein Raum mit HD-Material: `hd/backgrounds` hat `0001_logo`, `0002_thx`,
`0004_chapter1`, aber kein `0003`, und `hd/costumes` enthaelt keinen Satz `LFLF_0003`. Der
Sprung landet folgerichtig nicht in Raum 3, sondern im Startraum 87 (Protokoll:
`geladener Raum 87`, `Roomgroesse 0x480`), es gibt dort keine HD-Flaeche und damit keinen
Versatz zu messen. Zur Kontrolle dieselbe Binary mit den Nachbarraeumen: Raum 2 und Raum 4
laden normal (je 152 Zeichenzeilen, vier Stufenbilder), nur Raum 3 nicht. Der Befund ist
derselbe wie in der Baseline (`docs/HD-LUECKEN.md`, Abschnitt Baseline der HD-Positionierung).

### Sichtbilder

```
Basis projects/comi-hd/reports/vergleich/nachher/
raum03_komposit.png        Raum 3, Startraum 87, keine HD-Flaeche
raum09_komposit.png        Raum 9, Komposit nach dem Fix
raum09_deckung.png         5 Akteure, HD gruen, 8 Bit rot, beide weiss
raum15_komposit.png        Raum 15 (2096 breit)
raum15_deckung.png         ai 1 und ai 4, beide gliedmassen
raum44_komposit.png        Raum 44, Fenster 46
raum44_deckung.png         3 belastbare Akteure
raum44_vorher_nachher.png  derselbe Ausschnitt, vorher 46 px daneben
raum86_komposit.png        Raum 86
raum86_deckung.png         5 Akteure, beide Zeichenwege in einem Bild
```

In den Deckungsbildern ist links die ganze Szene mit eingezeichneten Akteurkaesten zu
sehen, danach je Akteur ein Feld: Die HD-Flaeche ist gruen, die 8-Bit-Silhouette rot und
die Ueberlappung weiss eingezeichnet, ueber der auf 45 Prozent abgedunkelten Szene. Die
erste Fassung dieser Bilder war bis auf die Beschriftung schwarz, Ursache und Neurechnung
stehen im Abschnitt "Deckungsbilder: falscher Koordinatenraum" am Ende dieses Dokuments.
Ein systematischer Versatz waere ein gruener und ein roter
Saum an derselben Kante. Ueber jedem Feld stehen Raum, Akteur, Kostuem, Cel, Zeichenweg und
die gemessenen dx/dy.

### Ergebnis

Alle 15 belastbaren Eintraege in den Raeumen 9, 15, 44 und 86 liegen bei 0 bis 2 Spielpixeln;
13 davon bei 0 bis 1, die zwei Ausnahmen bei 1,5 und 2,0 Pixeln in `dy`. Beide Zeichenwege,
skalierte und unskalierte Kostueme, stehende und der eine gescrollte Raum sind darunter. Kein
einziger Fall zeigt den Fensterversatz von 46 Pixeln, den der Vorher-Lauf in Raum 44 hat
(Deckung dort 0,10 bis 0,12 gegen 0,92 bis 0,98 nachher). Raum 3 ist ohne HD-Hintergrund
nicht messbar, tiefere Scrollstellungen sind mit der Magenta-Methode nicht messbar (die
8-Bit-Ebene ist dort vollstaendig bedeckt). Der Zielwert 0 bis 1 Pixel ist damit in 13 von 15
belastbaren Faellen erreicht und in keinem Fall um mehr als 1 Pixel verfehlt.

### Entscheidung: committet

Geprueft wurde die Karte Punkt fuer Punkt gegen die Rohzahlen in `work/verify/`:

```
Kriterium                       Befund
fuenf Raeume                    3, 9, 15, 44, 86 gelaufen. Raum 3 hat kein HD-Material und
                                ist nicht messbar (Sprung landet in Raum 87, Raeume 2 und 4
                                laden als Gegenprobe normal), die vier anderen sind gemessen.
beide Zeichenwege               gliedmassen 10 belastbare Eintraege, komplett 2 (nur Raum 86:
                                ai 5 cel 2 und ai 3 cel 10, je dx 0, dy 0, Deckung 0,87 und
                                0,95), Rueckfall cel 0 3
Zielwert 0 bis 1 px             13 von 15 belastbaren Eintraegen. Die zwei Ausnahmen liegen in
                                dy bei 1,5 und 2,0 px (Raum 15 ai 4 cel 68, Raum 44 ai 4 cel 8),
                                keine Verfehlung ueber 2,0 px.
magenta_check keine Regression  Raum 44 2,09 auf 0,12 Prozent. Raeume 3, 9, 15, 86 unveraendert
                                (0,00 / 0,02 / 0,01 / 0,03). Der Ausreisser in Raum 9 (max 3,91
                                Prozent im Sammellauf) wiederholt sich nicht: eigener Lauf ueber
                                80 Bilder, `work/verify/magenta/raum9_nach.csv` Mitte 0,02 und
                                max 0,02, derselbe Wert wie im Vorher-Lauf.
```

Entscheidung: committet. Drei Gruende:

1. Gegen 12f1a869 (8-Bit-Ebene liegt schon am Fensteranfang, Kostuem noch nicht) ist der
   Fehler belegt weg: Raum 44 Deckung 0,10 bis 0,12 auf 0,92 bis 0,98, dy 3 bis 12 auf 0 bis
   2, magenta 2,09 auf 0,12 Prozent.
2. Gegen die Baseline-Binary von 13:20 (vor 12f1a869) ist magenta in Raum 44 ebenfalls
   besser: 0,95 auf 0,12 Prozent. Die Baseline-Versatzwerte (dx 0 bis 0,5, dy 0 bis 2) sind
   kein Gegenbeleg, weil dort HD-Flaeche und 8-Bit-Dump gemeinsam verschoben waren (der
   8-Bit-Dump war bei xstart 46 rechts beschnitten); erst nachdem 12f1a869 die 8-Bit-Ebene
   auf den Fensteranfang gezogen hat, wird der Versatz sichtbar.
3. Raeume ohne Kamera liefern vorher und nachher dieselben Zahlen bis auf die letzte Stelle,
   die Aenderung verschiebt also nichts anderes.

Was der Commit nicht behauptet: 0 bis 1 px flaechendeckend. Zwei Eintraege liegen bei 1,5 und
2,0 px, Raum 3 ist ohne HD-Material nicht messbar, und Scrollstellungen tiefer als xstart 46
sind mit dieser Methode nicht messbar. Diese Grenzen bleiben offen.

Inhalt des Commits: `docs/HD-LUECKEN.md` mit diesem Abschnitt und den sieben Abschnitten der
Vorarbeiten, die aus demselben Grund uncommittet lagen. Der Fix selbst steckt schon in
`82ca6baa` (main). Die drei fremden, uncommitteten Code-Aenderungen im Arbeitsbaum (`gfx.cpp`
CULL fuer Raumobjekte, `hd_costume_manager.cpp`, `hd_object_manager.cpp`) gehoeren zu anderen
Karten und bleiben unberuehrt.

### Dateien

```
Arbeitsbaum   /opt/data/local/comi-hd-verify (82ca6baa, detached)
Binaries      projects/comi-hd/work/verify/binary/{scummvm-nach,scummvm-vor,scummvm-vn,scummvm-vv,scummvm-mn,scummvm-mv}
Laeufe        projects/comi-hd/work/verify/runs/{nach,vor}_raum{3,9,15,44,86},
              nach_raum44_walk, nach_raum44_walk150, nach_raum44_scroll, vor_raum44_scroll,
              nach_raum15_scroll, nach_raum15_scroll2, nach_raum86_scroll, kontrolle_raum{2,3,4}
Zahlen        projects/comi-hd/work/verify/versatz.csv, work/verify/scroll15_86.csv,
              work/verify/versatz_walk44.csv, work/verify/magenta/{nach,vor}.csv
Werkzeuge     projects/comi-hd/harness/verify_bilder.py, verify_vergleich.py,
              verify_lauf_walk.sh, verify_magenta_frames.py
Sichtbilder   projects/comi-hd/reports/vergleich/nachher/
```

## Vier Einzelbilder aus Raum 44: welche Stufe was zeigt (Aufgabe t_3e0c153d)

Die vier Bilder der Nutzerabnahme (`frage_A1..A4.png`) stammen aus einem Blatt, das
`harness/objektpfad/na_sicht.py` aus zwei Laeufen gebaut hat: drei Felder aus dem Lauf
`work/nachmesse_schritt2/nachher_raum44` (Fassung 12f1a869), ein Feld aus
`work/nachmesse_schritt2/vorher_raum44` (Fassung davor). Es sind keine vier
verschiedenen Bilder des Spiels, sondern vier Aufbaustufen aus zwei Fassungen derselben
Szene, aufgenommen im letzten Bild des jeweiligen Laufs (F=119, Kamera 46). Genau das
erklaert die unterschiedlichen Befunde, ohne dass sich Figur, Cel, Zeichenweg oder
Bildzustand unterscheiden muessten.

```
Feld  Datei         Lauf              Stufe  Inhalt
A1    n4            nachher_raum44    4     HD-Hintergrund + 8-Bit-Ebene + Kostueme
A2    n2            nachher_raum44    2     HD-Hintergrund + 8-Bit-Ebene
A3    v4            vorher_raum44     4     wie A1, aber Fassung vor 12f1a869
A4    n1            nachher_raum44    1     nur HD-Hintergrund
```

### Die eine Ursache: der Anker der Kostueme

Beide Zeichenwege (complete character und per-limb) laufen in Schritt 2.6 durch dieselbe
Ankerzeile (`gfx.cpp`, `hdCX = (drawX + limbDrawX * sclX / 255) * hdW / visW` mit
`drawX = pos.x - sdLeft`). Vor 12f1a869 klebte die 8-Bit-Ebene in Schritt 2 ab
Pufferspalte 0, der HD-Hintergrund dagegen ab dem Fensteranfang `sdLeft` (in Raum 44 die
46). Vor 82ca6baa fehlte `sdLeft` zusaetzlich im Kostuemanker. Damit gab es drei
Zustaende, und die vier Felder zeigen genau diese drei:

```
Fassung                    8-Bit-Figur   HD-Kostuem    Versatz   Bild
vor 12f1a869                x 335         x 335          0        beide 46 Punkte rechts der richtigen Stelle (A3)
12f1a869 bis 82ca6baa       x 289         x 335        +46        Figur doppelt (A1), 8 Bit allein richtig (A2)
ab 82ca6baa (jetzt)         x 289         x 289          0        eine Figur, an der richtigen Stelle
```

Die richtige Stelle ist x 289 in Kompositkoordinaten: Raumspalte 335 minus Fensteranfang
46. Sie folgt aus derselben Rechnung, mit der Hintergrund, Objekte und 8-Bit-Ebene
eingeklebt werden.

### Zahlen je Fall

Gemessen auf den Stufendumps des jeweiligen Laufs, Figurfenster 8-Bit-Pixel 270..450 x
170..380, zusammenhaengende Flaechen ab 300 Punkten. "8-Bit-Figur" ist die Flaeche, die
Stufe 2 gegenueber Stufe 1 hinzufuegt, "HD-Kostuem" die Flaeche, die Stufe 4 gegenueber
Stufe 3 hinzufuegt.

```
Lauf              Figur (8 Bit)                 HD-Kostuem                    Versatz   sichtbar
nachher_raum44    19.967 Punkte x 289,0..354,5   18.319 Punkte x 335,0..399,5   +46,0    zwei Figuren (A1)
   F=119          Fusskante 311,5
vorher_raum44     19.984 Punkte x 335,0..400,5    3.918 Punkte x 335,0..386,0     0,0    eine Figur, 46 zu weit rechts (A3)
   F=119          Fusskante 311,5
jetzt (82ca6baa)  19.967 Punkte x 289,0..354,5    3.881 Punkte x 289,0..340,0     0,0    eine Figur (Sichtpruefung)
   F=139          Fusskante 311,5
```

Die Ueberdeckung folgt aus den Kaesten und dem Rechteck, das der Lauf protokolliert
(`blit=260x671` bei `8bit=(289,144)`, also 65 x 168 Achtbitpunkte). Die Spalte
"HD-Kostuem" in der Tabelle oben ist die Menge der Punkte, deren Farbe sich zwischen
Stufe 3 und Stufe 4 aendert. Liegt das Kostuem deckungsgleich auf der 8-Bit-Figur,
aendern sich nur die Punkte, deren Farbe abweicht, deshalb faellt diese Flaeche in den
Faellen A3 und jetzt kleiner aus als die Figur. Die Lage kommt deshalb aus dem
protokollierten Rechteck, nicht aus der Farbflaeche.

```
Fall  Kostuemrechteck (8 Bit)   Figur (8 Bit)      Ueberdeckung der Figur
A1    x 335..400, y 144..312     x 289..354,5       19,5 von 65,5 Spalten = 30 Prozent
A3    x 335..400, y 144..312     x 335..400,5       65,0 von 65,5 Spalten = 99 Prozent
A2/A4 keine Stufe 2.6 im Dump   x 289..354,5       nicht anwendbar
```

A2 ist damit kein Fehler, sondern die Stufe vor Schritt 2.6: der Dump entsteht, bevor
irgendein HD-Kostuem gezeichnet wird, deshalb ist dort nur 8 Bit zu sehen, und zwar an
der richtigen Stelle (x 289). A4 entsteht sogar vor Schritt 2 (8-Bit-Ebene), deshalb
kann dort keine Figur stehen; der Dump in `gfx.cpp` liegt direkt hinter der
Hintergrundkopie. Nur A1 und A3 zeigen einen echten Fehler, und beide sind derselbe:
ein Anker ohne Fensterversatz.

### Je Bild: Akteur, akos, cel, Zeichenweg, Positionen

Lauf `jetzt`, Bild F=139, Kamera 46, Skalierung 4, Komposit 2560x1920. Die Zeilen
kommen aus `HD_TRACE_DRAW=1` (`DRAW kostuem ...`), die Flurstufe aus dem Eintrag selbst.
"Zeichenweg" ist `complete`, wenn der Akteur in diesem Bild genau einen Eintrag hat,
sonst `per-limb` mit der Zahl der Eintraege.

```
Aktor  akos  cel  Zeichenweg    HD-Position   8-Bit-Pos   Blit        Flaeche geladen
1      2     22   per-limb(2)   (1156,576)    (289,144)   260x671     ja
1      2     34   per-limb(2)   (1224,396)    (306,99)    119x203     ja
4      251   32   complete      (1568,804)    (392,201)   648x524     ja
17     253   5    complete      (-184,532)    (-46,133)   712x1388    ja
```

Summenzeile des Laufs: `step2.6 costumes: loaded=5 skipped=77 (noCostume=77 noCel=0
noHdCostume=0 loadFail=0)` bei F=90 und F=120, `hd_costume_loadfail.log` wurde nicht
angelegt, keine `off-screen`-Warnung in 140 Bildern. Beide Zeichenwege stehen im selben
Bild in derselben Liste: die Spielfigur (akos 2) ueber zwei Glieder, die beiden anderen
Akteure ueber je einen Eintrag. Ein Unterschied in der Positions- oder Deckungslogik
zwischen den Wegen ist damit nicht zu sehen; es gibt nur die eine Ankerzeile.

Dieselben vier Felder in der Fassung 12f1a869 (Lauf `nachher_raum44`, Zeilen bei F=90,
weil dieser Lauf ohne `HD_TRACE_DRAW` lief): ai=1 akos 2 cel 22 bei `(1340,576)`, also
8-Bit x 335, cel 34 bei `(1408,396)`, Skalierung 200, Flaeche 332x856 und 152x260.
Die Spielfigur hat dort dieselben Cels und denselben Zeichenweg wie im Lauf `jetzt`;
nur der Anker liegt 46 Punkte anders. Die beiden Nebenakteure stehen in einer anderen
Animationsphase (akos 251 mit cel 8 und 11 statt cel 32, akos 253 mit cel 16 statt
cel 5), fuer den Versatz der Figur spielen sie keine Rolle.

Die Stufendumps werden in jedem Bild ueberschrieben, gehoeren also zum letzten Bild des
Laufs; der Bildindex kommt aus den `F=`-Zeilen des Zustandsprotokolls. `HD_DUMP_SEQ`
blieb in beiden Laeufen leer, weil die Aufnahme in diesem Zustand nicht scharf war
(`_hdCaptureArmed`), fuer die Zuordnung wird es nicht gebraucht.

### Was die Hypothese nicht bestaetigt

Die Vermutung war, je nach Zeichenweg (complete gegen per-limb) und je nach Zustand
(cel, Skalierung) greife eine andere Positions- und Deckungslogik. Dagegen sprechen:

1. Die vier Felder sind Stufen derselben Szene, nicht vier Bilder mit wechselnden
   Zustaenden. Figur, akos, Cel und Skalierung sind in allen Feldern dieselben.
2. Der Versatz ist in A1 exakt 46 Punkte, also genau der Fensteranfang `sdLeft` und
   nicht ein Cel- oder Gliedversatz von 3 bis 8 Punkten.
3. Complete und per-limb laufen durch dieselbe Zeile; im Lauf `jetzt` liegen beide Wege
   im selben Bild vor, und beide sitzen auf der 8-Bit-Figur.

### Was hier nicht gemessen wurde

1. Nur Kameraposition 46. Andere Stellen in Raum 44 und die Raeume 40 bis 43, 77, 79, 82
   mit senkrechtem Versatz sind nicht nachgemessen; der Anker ist derselbe, die Zahlen
   fehlen.
2. Gespiegelte und skalierte Akteure kommen in Raum 44 nicht vor (Skalierung 200 bei
   der Spielfigur ist ungespiegelt). Der Zweig `mirror ? hdCX - blitW : hdCX` bleibt
   ungemessen.
3. Akteur 17 steht mit x -46 teilweise links ausserhalb; an ihm laesst sich kein
   vollstaendiger Versatz ablesen.
4. Der 8-Bit-Rest, der trotz deckendem Kostuem stehen bleibt (Alpha 0 mit 8-Bit-Inhalt
   darunter, Stufe 2.6b ausserhalb der Akteurkaesten), ist ein eigener Befund und hier
   nicht gemessen; Zahlen dazu in `docs/REGEL1-8BIT-FUELLUNG.md` (6.102 Punkte je Bild
   aus Regel 1, 16.852 Punkte aus Stufe 2.6b).

### Dateien

```
Bilder der Abnahme, markiert      projects/comi-hd/reports/vergleich/fall_A1.png
                                  .../fall_A2.png, .../fall_A3.png, .../fall_A4.png
A1 in der Fassung ab 82ca6baa     projects/comi-hd/reports/vergleich/fall_A1_jetzt.png
Quelle der vier Felder            projects/comi-hd/reports/vergleich/frage_A.png, frage_A1..A4.png
                                  projects/comi-hd/reports/vergleich/raum44_nachmesse_schritt2_figur.png
Lauf jetzt (140 Bilder)           projects/comi-hd/work/fall44/jetzt/ (hd_step_1..4.ppm, hd_state.log,
                                  hd_ref.ppm, hd_actor_probe.log, hd_cost_bounds.log)
Lauf 12f1a869                     projects/comi-hd/work/nachmesse_schritt2/nachher_raum44/
Lauf davor                        projects/comi-hd/work/nachmesse_schritt2/vorher_raum44/
Messung und Bilder                projects/comi-hd/harness/fall_auswertung.py
Tabelle je Bild                   projects/comi-hd/harness/fall_frame.py
Lauf und Warten                   projects/comi-hd/harness/fall_lauf.sh, fall_warten.sh
Binary des Laufs                  projects/comi-hd/work/engine/scummvm-f44 (Fork-Bau 16:45, HEAD 82ca6baa)
```

## Deckungsbilder: falscher Koordinatenraum, Raum 44 war schwarz (Aufgabe t_599ebbfa)

### Befund

`projects/comi-hd/reports/vergleich/nachher/raum44_deckung.png` ist bis auf die
Beschriftungszeile schwarz. Nachgemessen an der ausgelieferten Datei: 288 x 446 Punkte,
mittlere Helligkeit 4,36, nicht schwarze Punkte 15,74 Prozent, davon gruen 0, rot 0,
weiss 0 und gelb 489 Punkte. Es sind also alle drei Felder leer, gezeichnet wurde nur der
gelbe Text. Dasselbe Muster in kleinerem Umfang bei `raum09_deckung.png` (Helligkeit
16,45), `raum15_deckung.png` (17,49) und `raum86_deckung.png` (22,29); brauchbar war
keines der vier.

### Erste Ursache: hd_box und blit wurden nicht durch die Skala geteilt

`gfx.cpp` protokolliert die HD-Position und den Blit in Kompositpunkten. Die Stufendumps
sind um `skala = Dumpbreite / 640` kleiner, in diesen Laeufen Faktor 2 (Dump 1280 breit,
Spiel 640). `harness/baseline_auswertung.py` rechnet das richtig (`hx = e["hx"] / skala`),
`harness/verify_bilder.py` nicht: es hat `e["hd_box"]` und `e["blit"]` roh als
Dumpkoordinaten benutzt. Damit lag jedes Fenster auf dem doppelten Ort und war doppelt so
gross, traf also neben dem Akteur.

Belegt an den drei belastbaren Akteuren aus `work/verify/runs/nach_raum44` (Dump 1280 x 960,
skala 2, Rand 48 Punkte):

```
Akteur      box (roh)     Fenster wie im Skript    Maskenpunkte      Fenster geteilt   hd     8bit   beide
ai=4  cel=8   1944, 724        0 x 284              hd 0    8bit 0        198 x 206   15366  14452  14451
ai=1  cel=34  1224, 396      104 x 299              hd 0    8bit 0        155 x 197    8152   7798   7656
ai=1  cel=22  1156, 576      172 x 432              hd 0    8bit 0        226 x 431   26027  25412  24052
```

Ueber alle vier Raeume (15 belastbare Eintraege) blieben 11 Fenster ohne einen einzigen
Maskenpunkt; die uebrigen vier trafen zufaellig einen Teil des Akteurs, was die Reste in
Raum 9 und 86 erklaert.

### Zweite Ursache: die Bauart war ohnehin kein Raumnachweis

Die Felder wurden auf einen schwarzen Grund gezeichnet, nur die beiden Masken und die
Ueberlappung. Auch mit richtigen Fenstern zeigt so ein Bild eine Silhouette, nicht den
Raum. Fuer ein Nachweisbild ist das die falsche Bauart, unabhaengig vom Rechenfehler.

### Korrektur und Wiederholung

`harness/verify_bilder.py` ist geaendert:

1. `hd_box` und `blit` werden durch `skala` geteilt, bevor zugeschnitten wird.
2. Das Blatt beginnt mit der ganzen Szene (Komposit Stufe 4, 640 breit), Akteurkaesten
   gelb eingezeichnet und beschriftet. Damit steht der Raum mit Figuren und Objekten
   im Bild.
3. Je Akteur folgt ein Feld: die auf 45 Prozent abgedunkelte Szene, darueber die
   HD-Flaeche gruen, die 8-Bit-Silhouette rot, die Ueberlappung weiss. Die Szene bleibt
   unter den Masken erkennbar.
4. Leere Fenster werden ausgelassen und gemeldet, statt als schwarze Felder zu erscheinen.
5. Am Ende prueft das Skript die mittlere Helligkeit und endet mit Rueckgabewert 1, wenn
   ein Bild unter 20 liegt.

Neu gerechnet aus denselben Laeufen; die Komposits sind in der Dateigroesse gleich den
ausgelieferten (1.827.185 / 1.267.758 / 1.197.503 / 1.580.984 Bytes), die Laeufe sind also
dieselben (Binary `work/verify/binary/scummvm-nach`, md5 9ebd7e8a, Arbeitsbaum 82ca6baa):

```
Bild                     Punkte      Helligkeit   Schwelle 20   Felder
raum44_deckung.png       1237 x 494     93,87       bestanden     Szene + 3 Akteure
raum09_deckung.png       2170 x 494     90,87       bestanden     Szene + 5 Akteure
raum86_deckung.png       2417 x 646     59,45       bestanden     Szene + 5 Akteure
raum15_deckung.png        966 x 494     99,63       bestanden     Szene + 2 Akteure
```

Gegenprobe, dass die Masken wirklich auf den Akteuren liegen (Fenster wie im korrigierten
Skript): fuer ai=1 cel=22 in Raum 44 liegen 24.052 Punkte gleichzeitig in beiden Masken,
das sind 92,4 Prozent der HD-Flaeche und 94,7 Prozent der 8-Bit-Flaeche. In Raum 9 sind es
bei ai=2 cel=5 50.208 von 51.003 (98,4 Prozent), in Raum 86 bei ai=5 cel=2 9.213 von
10.522 (87,6 Prozent). Diese Werte passen zu den Deckungen in `versatz.json` (0,87 bis
0,98), die aus derselben Messung stammen.

Die Zahlen der Verifikation selbst waren nie falsch: `baseline_auswertung.py` teilt die
Rohkoordinaten durch die Skala, deshalb sind dx/dy und die Deckungswerte in `versatz.json`
von diesem Fehler nicht betroffen. Falsch war allein das Bild, das aus denselben Dumps
gezeichnet wurde.

### Kein neuer Spielaufruf

Waehrend dieser Arbeit lief bereits ein Messlauf einer anderen Karte (`scummvm-v44`,
PID 956530, `timeout 400`). Es gilt ein Spielprozess gleichzeitig, deshalb wurde keine
eigene Runde gestartet, sondern aus den dokumentierten Stufendumps neu gerechnet. Die
Bilder sind damit eine Auswertung vorhandener Rohdaten, kein neuer Messlauf.

### Was hier nicht gemessen wurde

1. Raeume mit belastbaren Eintraegen sind 9, 15, 44 und 86. Raum 3 hat kein HD-Material
   (Abschnitt oben), dort gibt es kein Deckungsbild, nur den Komposit.
2. Das linke Feld ist der Komposit des Laufs, keine Videoaufnahme und kein Mitschnitt
   mehrerer Bilder.
3. Scrollstellungen tiefer als xstart 46 bleiben mit der Magenta-Methode nicht messbar
   (8-Bit-Ebene vollstaendig bedeckt), das betrifft auch die Deckungsbilder.

### Dateien

```
Neu gerechnet   projects/comi-hd/reports/vergleich/nachher/raum{03_,09_,15_,44_,86_}*.png
Bild E ersetzt  projects/comi-hd/reports/vergleich/frage_E.png
Alte Fassung    projects/comi-hd/reports/vergleich/nachher/raum{09,15,44,86}_deckung_kaputt.png
                projects/comi-hd/reports/vergleich/frage_E_kaputt.png  (nicht geloescht)
Bildgenerator   projects/comi-hd/harness/verify_bilder.py   (korrigiert)
Helligkeit      projects/comi-hd/harness/bild_helligkeit.py  (Schwelle 20, Exit 1)
Farbflaechen    projects/comi-hd/harness/deckung_farben.py   (gruen/rot/weiss, Ueberdeckung)
Fensterprobe    projects/comi-hd/harness/deckung_diagnose.py (roh gegen geteilt, je Akteur)
Laufuebersicht  projects/comi-hd/harness/lauf_uebersicht.py
Laeufe          projects/comi-hd/work/verify/runs/nach_raum{9,15,44,86}/
```
