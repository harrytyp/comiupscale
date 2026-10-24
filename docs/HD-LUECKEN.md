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
