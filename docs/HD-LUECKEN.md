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
