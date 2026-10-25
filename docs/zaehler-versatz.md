# Versatz zwischen 8-Bit- und HD-Figur in Raum 44

Stand 25.10.2026, gemessen auf dem Fork-Binary mit md5 `7dda6a1f26fc0bafca458ead80ac370a`
(Bau von 10:07, also der Stand **vor** dem Hotspot-Fix). Kein Build, keine Quellaenderung.

## Ergebnis

Die HD-Zeichnung der Spielfigur steht in Raum 44 **46 Spielpixel links** der 8-Bit-Zeichnung
derselben Figur. Senkrecht ist kein Versatz messbar (0 bis 1 Pixel). Die zweite Figur im Bild
(Kostuem 0251) zeigt denselben Versatz. Beide Silhouetten sind gleich gross, es ist also eine
reine Verschiebung und keine Skalierung.

| Groesse | 8-Bit-Figur | HD-Figur | Differenz |
|---|---|---|---|
| Kasten, Spielpixel | x 335 bis 400, y 100 bis 311 | x 289 bis 353, y 99 bis 311 | **-46,0 / -1,0** |
| Ausdehnung, Spielpixel | 65 x 211 | 64 x 212 | 1 x 1 |
| Flaeche, Stufendump 1280x960 | 26908 px | 29093 px | 2185 px |
| beste Ueberlagerung | - | HD-Maske um **+46,5 / 0,0** Spielpixel verschieben | 25962 von 31452 px deckungsgleich (82,5 %) |

Umgerechnet: **92 Dumppixel** (Stufendumps, 2x Spielpixel) oder **184 Pixel** in der
HD-Komposition (2560x1920, 4x Spielpixel), jeweils nach links.

Zweite Figur im Bild, gleiche Messung: Ueberlagerung **+46,0 / +0,5 Spielpixel**, 13551 von
17313 px deckungsgleich (78,3 %). Der Kasten dieser Figur taugt nicht als Mass, weil ihre
8-Bit-Flaeche am Rand der 594 Pixel breiten Aufnahme abgeschnitten ist und ihre HD-Flaeche
zwei Gliedmassen in einem Kasten zusammenfasst.

Sichtbar wird der Versatz als doppelte Figur: die Vereinigung beider Zeichnungen
(Stufe 4 minus Stufe 1) ist **111 Spielpixel breit**, die Figur selbst 65. Tafel:
`/opt/data/projects/comi-hd/work/raum44_versatz2/bilder/raum44_doppelte_figur.png`
(links nur HD-Figur, rechts beide Zeichnungen).

## Vorgehen (Vorgabe aus `HANDOFF-doppelasset.md`, Schritt 1 bis 5)

### Schritt 1: Frame-Nummerierung in `work/dumps/hd_seq`

Ein Lauf schreibt je Aufnahme zwei Bilder im selben Codeblock (`gfx.cpp`, `HD_DUMP_SEQ`):
`h000NN.ppm` (HD-Komposition, 1280x960) und `r000NN.ppm` (8-Bit-Bildschirm). Die Indizes
gehoeren also paarweise zusammen. Gemessen ueber drei Laeufe (normal, `HD_NO_ACTORS=1`, mit
`HD_TINT_8BIT=1`), jeweils 80 Paare:

| Indizes | Raum | r-Bild | Bedeutung |
|---|---|---|---|
| 0 bis 14 | 87 (Startraum) | 640x480, 921615 Byte | vor dem Sprung, bildschirmbreit |
| 15 bis 79 | 44 | 594x480, 855375 Byte | `594 = 640 - xstart(46)` |

Damit ist die frueher benutzte Annahme, `h00040.ppm` sei das 40. Bild des Laufs, irrig: die
Indizes zaehlen nur die Aufnahmen (jedes dritte Bild), und in einem nicht geraeumten Ordner
liegen Reste frueherer Laeufe mit anderen Bildbreiten. Die r-Bilder sind in Raum 44 **kein
Vollbild**: Raum 44 ist laut Protokoll 952x480 gross
(`HD: loaded bg for room 44 (3808x1920) scale=4 (room 952x480)`), das Fenster ist 640 breit,
und `xstart` steht im Protokoll 202 Mal auf **46**. Die r-Aufnahme enthaelt deshalb nur die
linken 594 der 640 sichtbaren Spalten. Fuer Positionen ist sie in diesem Raum nur brauchbar,
solange die Figur links von Spalte 594 steht.

**Falle, die den ersten Anlauf unbrauchbar machte:** die Engine schreibt auf feste Pfade in
`work/dumps`. Parallel laufende Aufgaben (Regressionslauf ueber 25 Raeume) haben dieselben
Dateien ueberschrieben; im ersten Versuch lagen 42 und 64 Bilder mit gemischten Breiten in den
Ordnern. Fuer die Messung wurden deshalb Binary-Kopien mit gepatchten Aufnahmepfaden benutzt
(`harness/versatz_binary_patch.py`, gleiche Textlaenge, sonst verschiebt sich der Stringtisch).

### Schritt 2 und 3: zwei Laeufe, Differenz

```
HD_JUMP_ROOM=44 HD_FIXED_DELTA=20 HD_DUMP_SEQ=1 HD_DUMP_STEPS=1 HD_EXIT_AFTER=240 HD_TRACE_DRAW=1
HD_JUMP_ROOM=44 ... zusaetzlich HD_NO_ACTORS=1
```

Beide Laeufe enden bei Bild 240, die Stufendumps stammen aus Bild 239 (Protokoll: F von 0 bis
239, 920 bzw. 392 `DRAW kostuem`-Zeilen). Kontrolle, dass beide Laeufe denselben Zustand zeigen:
Stufe 1 (Hintergrund) ist in beiden **0 Pixel** unterschiedlich, Stufe 2 und 3 unterscheiden
sich in genau 46861 Pixeln (der 8-Bit-Figur), Stufe 4 in 166598 Pixeln.

Die Differenz wurde auf den **Stufenbildern** gebildet, nicht auf den r-Bildern: 8-Bit-Figur
ist `hd_step_2_vordergrund` (mit Figuren) minus `hd_step_2_vordergrund` (ohne Figuren),
also 46861 px = 3,81 Prozent des Bildes. Damit liegen 8-Bit- und HD-Zeichnung von vornherein
im selben Koordinatensystem.

### Schritt 4: HD-Flaeche

- `hd_step_4_kostueme` minus `hd_step_1_hintergrund` (Aufgabenstellung): **189640 px**. Darin
  stecken Hintergrundobjekte, 8-Bit-Vordergrund und Kostueme; die Spielfigur bildet mit der
  8-Bit-Figur einen gemeinsamen Block von 54207 px, 111 Spielpixel breit.
- `hd_step_4_kostueme` minus `hd_step_3_objekte` (nur der Kostuemschritt): **66420 px**, darin
  die Spielfigur mit 29093 px und die zweite Figur mit 23819 px.

### Schritt 5: beide Flaechen ins gleiche Koordinatensystem

Nicht mehr noetig: beide Masken kommen aus derselben Komposition, der Faktor ist 2 (Dumppixel
je Spielpixel) beziehungsweise 4 zur Komposition. Der Versatz wurde zweifach bestimmt, ueber
den Kasten und ueber die Verschiebung, die die HD-Maske am besten auf die 8-Bit-Maske legt
(Suche ueber plus/minus 120 Dumppixel, Bewertung: Anzahl deckungsgleicher Pixel).

Gegenprobe mit einem unabhaengigen Verfahren (Lauf mit `HD_TINT_8BIT=1`, das den
8-Bit-Vordergrund magenta einfaerbt): 8-Bit-Figur magenta bei Spielpixel 335 bis 400,
HD-Kostuem 289 bis 354. Also **ebenfalls 46 Pixel**, gleiche Richtung.

## Richtung: welche Zeichnung liegt falsch

Belegt ist nur die Relativlage. Was dazu aus den Daten folgt:

- Die Engine zeichnet das HD-Kostuem genau dorthin, wo ihre Formel es berechnet. Die
  `DRAW kostuem`-Spur nennt fuer die Spielfigur zwei Gliedmassen, `hd=(1224,396)` (oberes,
  geteilt durch 4 also Spielpixel 306,99) und `hd=(1156,576)` (unteres, Spielpixel 289,144).
  Der gemessene HD-Kasten beginnt genau bei 289. Die HD-Zeichnung folgt ihrem Code.
- Der Betrag **46 ist genau der Kamera-Fensteranfang `xstart` dieses Bildes** (Protokoll:
  `xstart=46`, Raumbreite 952, Fenster 640). Das ist der auffaelligste Zahlenzusammenhang:
  die HD-Zeichenposition rechnet in `renderHDComposite` mit `drawX = actorPos.x - sdLeft`,
  `sdLeft` kommt aus `hdWindowLeft()` und ist hier 46. Entweder wird das Fenster auf der
  HD-Seite einmal zu viel abgezogen, oder die 8-Bit-Ebene wird beim Zusammensetzen mit dem
  Fensteranfang gelesen. Die Messung allein entscheidet das nicht.
- Der Hintergrund ist ebenfalls nicht deckungsgleich: Kantenkorrelation zwischen dem
  8-Bit-Bildschirm und `hd_step_1_hintergrund` ergibt das Maximum bei **+40 Spielpixel**
  (Korrelation 0,38; bei 0 nur 0,10; Raster 4 Pixel). Das ist nah an 46, aber nicht genau
  genug, um es gleichzusetzen. Ob das HD-Hintergrundbild von Raum 44 selbst versetzt ist
  oder die Ebene versetzt gelesen wird, ist eine eigene Messung.

Fuer die Bestaetigung der Richtung fehlt ein Versuch mit bewegtem Fenster: laeuft die Figur
(Raumwechsel oder Kamerafahrt), dann muss der Versatz entweder mit `xstart` wandern (dann ist
es das Fenster) oder konstant bleiben (dann ist es der Cel-Hotspot aus `_hdLimbDrawX`).

## Offene Punkte

1. **Versuch mit bewegtem Fenster** (siehe oben), damit die Ursache feststeht.
2. **Zweite Figur**: ihr 8-Bit-Kasten ist am Rand der 594-Spalten-Aufnahme abgeschnitten.
   Fuer sie ist nur der Ueberlagerungswert belastbar, nicht der Kasten.
3. **Hintergrund von Raum 44**: Versatz des HD-Hintergrundbildes gegen das Raumbild messen
   (eigene Messung, nicht Teil dieser Aufgabe).

## Werkzeuge und Dateien

| Datei | Zweck |
|---|---|
| `harness/versatz_binary_patch.py` | Binary-Kopien mit eigenen Aufnahmepfaden (kein Streit um `work/dumps`) |
| `harness/versatz_laeufe2.sh` | die beiden Messlaeufe, feste Zeitbasis, gleiche Bildzahl |
| `harness/versatz_lauf_tint.sh` | Lauf mit `HD_TINT_8BIT=1` fuer die Gegenprobe |
| `harness/versatz_schritte.py` | 8-Bit-Figur aus der Laufdifferenz, HD-Flaeche aus den Stufen |
| `harness/versatz_fein.py` | Feinmessung je Figur (Ueberlagerung, Kaesten) |
| `harness/versatz_tint.py` | Gegenprobe mit `HD_TINT_8BIT=1` |
| `harness/versatz_hintergrund.py` | Kantenkorrelation 8-Bit-Bildschirm gegen HD-Hintergrund |

Daten: `work/raum44_versatz2/{mit,ohne,tint}` (Bilder, Stufen, Protokolle, `versatz_*.json`).
Tafeln: `work/raum44_versatz2/bilder/raum44_doppelte_figur.png`,
`work/raum44_versatz2/markiert_schritte.png` (rot 8-Bit-Figur, blau HD-Kostuem, gruen
Ueberdeckung).

## Nachvollziehen

```bash
cd /opt/data/projects/comi-hd
/opt/data/local/comi-hd-repo/.venv-upscale/bin/python harness/versatz_binary_patch.py
bash harness/versatz_laeufe2.sh                      # mit und ohne HD_NO_ACTORS
/opt/data/local/comi-hd-repo/venv/bin/python3 harness/versatz_schritte.py \
    work/raum44_versatz2/mit work/raum44_versatz2/ohne work/raum44_versatz2/markiert_schritte.png
/opt/data/local/comi-hd-repo/venv/bin/python3 harness/versatz_fein.py \
    work/raum44_versatz2/mit work/raum44_versatz2/ohne
```
