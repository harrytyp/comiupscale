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
