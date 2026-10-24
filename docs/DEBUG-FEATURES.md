# Debug-Features der HD-Engine

Alle Schalter werden über Umgebungsvariablen gesetzt. Sie ändern nur das Verhalten für
Aufnahmen und Diagnose, nie das Spiel selbst. Jeder Schalter ist hier dokumentiert, damit
eine Messung von aussen reproduzierbar ist.

## Aufnahme und Reproduzierbarkeit

| Variable | Wirkung |
|---|---|
| `HD_FIXED_DELTA=<ms>` | Fester Zeitschritt pro Bild. Ohne ihn hängt der Spielzustand an der Rechenlast, und zwei Läufe zeigen unterschiedliche Bilder. Mit `20` liefern zwei verschiedene Engine-Builds dasselbe Bild. |
| `HD_JUMP_ROOM=<raum>` | Wechselt über `startScene` in den Raum, wie es das Spiel tut. |
| `HD_SAVE_SLOT` / `HD_LOAD_SLOT` | Spielstand schreiben / laden. |
| `HD_EXIT_AFTER=<bilder>` | Beendet den Lauf nach n Bildern. |
| `HD_DUMP_AT=<bilder>` | Einzelaufnahme nach n Bildern. |
| `HD_DUMP_SEQ` | Bildfolge, erst ab dem Raumsprung (`_hdCaptureArmed`). |
| `HD_DUMP_DIR` | Zielordner für Aufnahmen. |

## Diagnose

| Variable | Wirkung |
|---|---|
| `HD_TINT_8BIT=1` | Färbt jedes Pixel, das aus der 8-Bit-Ebene gezeichnet wird, magenta. Damit ist sichtbar und zählbar, wo noch 8-Bit-Grafik steht — ohne Schätzung. |
| `HD_SPY=1` | Schreibt jede gezeichnete 8-Bit-Textur mit auf: Objekt (Nummer, Zustand, Lage, Größe) und Kostüm (AKOS, Bild). Ausserdem fehlende HD-Texuren mit Pfad. |
| `HD_LEGACY_CAMX=1` | Schaltet auf die alte Rechnung des Fensteranfangs zurück (`vs->xstart` statt Kamera). Nur zum Vergleich. |
| `HD_SKIP_SMUSH=1` | Überspringt Zwischensequenzen, damit ein Aufnahmelauf direkt zum Spielverlauf kommt. |
| `HD_TRACE_DRAW=1` | Zeichnet Kostüm-Zugriffe mit. |

## Protokolldateien

| Datei | Inhalt |
|---|---|
| `work/dumps/hd_room.txt` | Tatsächlich geladener Raum. Wird vor jedem Lauf gelöscht, sonst meldet sie einen alten Wert. |
| `work/dumps/hd_fg.log` | Je 30 Bilder: Raum, HD-Raum, Vordergrundanteil (8-Bit-Pixel / 8-Bit-Pixel). |
| `work/dumps/hd_spy.log` | Jede gezeichnete 8-Bit-Textur: `OBJ` bzw. `AKOS`. |
| `work/dumps/hd_missing.log` | Fehlende HD-Texturen: `NOMAP` (nicht im Verzeichnis) oder `MISSING` (Verzeichnis ja, Datei nein). |
| `work/dumps/hd_skip.log` | Grund, warum eine Komposition ausfiel (`smush`, `hd_off_until`). |

## Prüfwerkzeuge

| Werkzeug | Zweck |
|---|---|
| `harness/room_by_room.py` | Raum für Raum messen, Ergebnis sofort in eine CSV. |
| `harness/hd_anteil.py` | Anteil des Bildes, der aus dem HD-Hintergrund stammt (Geometrie aus dem Protokoll). |
| `harness/achtbit_check.py` | Anteil der Kanten auf dem 8-Bit-Raster (Hinweis, kein Beweis — HD-Kanten liegen auch mal auf dem Raster). |
| `harness/hd_check.py` | Korrelation gegen Asset und Hochskalierung. |
| `harness/shift_probe.py` | Bester Versatz zwischen HD und 8-Bit. |
| `harness/ausschnitt.sh`, `einzel.sh` | Ausschnitte in Originalauflösung für die Sichtprüfung. |

## Merksätze aus den Messungen

- **Raumspur vor jedem Lauf löschen.** Sonst meldet sie einen Raum, der nie geladen wurde.
- **Nenner prüfen.** Ein Vordergrundanteil von „6 Prozent" war falsch, weil 8-Bit-Pixel durch
  HD-Pixel geteilt wurden. Richtig: 302080 / 307200 = 98,3 Prozent.
- **Ein Bild ist keine Messung.** Flimmern und Scrollfehler brauchen Bildfolgen.
- **Signalfarbe schlägt Statistik.** `HD_TINT_8BIT` sagt exakt, wo 8-Bit steht; jede
  Korrelation hat in dieser Arbeit Fehlalarme geliefert.
