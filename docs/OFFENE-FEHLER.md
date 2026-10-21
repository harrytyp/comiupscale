# Offene Fehler aus der Sichtprüfung (Priorität, mit Fundstellen)

Diese vier Fehler hat die Einzelbild-Messung nicht gefunden. Sie brauchen Bildfolgen
und einen Vergleich der Ebenen-Offsets, nicht ein Bildpaar.

## 1. Gemischte Szene in der Banjo-Sequenz

Symptom: Banjo-Modell in HD, dahinter ein kaputter Himmel, davor eine Spielszene am
Hotel — zwei Szenen in einem Bild.

Verdacht: waehrend einer Sequenz wird der HD-Hintergrund des Raums weiter gezeichnet,
obwohl das Spiel gerade einen anderen Hintergrund zeigt (Video oder Sonderbild). Der
Hintergrund wird nur in `ScummEngine::initRoomSubBlocks`/`room.cpp:318` beim Raumwechsel
getauscht, nicht bei einem Szenenwechsel innerhalb des Raums.

Fundstellen: `room.cpp:310-340` (Laden je Raum), `gfx.cpp` `renderHDComposite` Step 1
(Hintergrund-Kopie mit `camX/camY`).

## 2. Streifen-Offsets statt einem Kamera-Offset

Symptom: In Raum 41 fehlt der Querbalken ueber dem Wasser und die Wasserkante franst
aus; in Raum 82 scrollt das Wasser mit, waehrend es im Original stillsteht.

Ursache: ScummVM setzt den Hintergrund bei V7+ aus Streifen zusammen, die sich getrennt
verschieben koennen (`Gdi::_scrollFeedStrips`, `scrollScreen`). Die HD-Komposition nutzt
genau einen Offset fuer den gesamten Hintergrund (`vs->xstart * scale`).

## 3. Flimmern: 8-Bit-Rueckfall unter Cutscenes

Symptom: Guybrush flackert in 8 Bit unter einer Sequenz, in der er nicht sichtbar sein soll.

Ursache: der Rueckfall zeichnet die 8-Bit-Figur, wenn fuer das aktuelle Cel kein HD-Bild
vorliegt (`hdActorDrawn`, Step 2.6 in `gfx.cpp`). In einer Sequenz wechselt das Cel jedes
Bild, also hat ein Bild ein HD-Cel und das naechste nicht.

Regel: hat eine Figur ueberhaupt ein HD-Kostuem, darf kein 8-Bit-Rueckfall greifen.

## 4. Loecher innerhalb der Segel

Symptom (Sichtpruefung): die Segel sind innen loechrig, nicht am Rand beschnitten.

Ursache: die Rueckholung des Hintergrunds an durchsichtigen Kostuem-Pixeln (eingebaut fuer
Raum 89, Figur unter dem grossen Hand-Kostuem) greift auch INNEN in einer zusammenhaengenden
HD-Flaeche. Ueberall dort, wo das 8-Bit-Bild an dieser Stelle keinen Vordergrund erkennt,
wird ein Loch in die HD-Flaeche gestanzt.

Richtig: die Rueckholung darf nur am AEUSSEREN Rand einer HD-Flaeche greifen. Vor dem
Stanzen pruefen, ob das Pixel von geschlossener HD-Flaeche umgeben ist ("ist es ein
Randpixel?"), und nur dann durchlassen. Das trennt "Figur unter dem Kostuem retten" von
"Loecher ins Segel stanzen".

## Was am Pruefstand fehlt

`harness/room_by_room.py` vergleicht ein Bildpaar je Raum. Damit sind Flimmern und
mitwandernde Ebenen grundsaetzlich unsichtbar. Noetig:

- Bildfolge je Raum (mindestens 30 Bilder) statt eines Bildes
- Flimmer-Mass: Pixel, die zwischen aufeinanderfolgenden Bildern wechseln, waehrend das
  8-Bit-Bild dort unveraendert ist
- Ebenen-Vergleich: fuer jeden Streifen den besten Versatz suchen (`harness/shift_probe.py`
  kann das je Bild) und melden, wenn HD und 8-Bit verschiedene Versaetze haben
