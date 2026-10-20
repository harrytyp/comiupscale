# Pruefung vor jeder Auslieferung

Ein Aufruf, vier Punkte, Rueckgabewert 0 nur wenn alles stimmt:

    bash scripts/verify_release.sh

| Punkt | Was geprueft wird | Schwelle |
|-------|-------------------|----------|
| 1 | Linux-Engine vorhanden und startfaehig | muss starten |
| 1b | Windows-Binary juenger als die Engine-Quellen | Datum |
| 2 | HD-Assets gegen `docs/asset-manifest.txt` | 26662 Dateien, keine Abweichung |
| 3 | Texture-Packs enthalten jede Datei genau einmal | fehlt 0, doppelt 0, fremd 0 |
| 4 | Raumvergleich, neuestes Ergebnis in `reports/final_save*/` | kein Raum ueber 10 Prozent, Mittel unter 1 Prozent |

## Raumvergleich selbst messen

    bash harness/make_save.sh                      # Spielstand anlegen, einmalig
    ./venv/bin/python3 harness/final_sweep.py $(ls -d reports/sd/*/ | xargs -n1 basename)

Ergebnis: `gleicher_frame.csv` mit `abweichung` und `ueber40_prozent` je Raum. Gemessen wird
das 8-Bit-Bild gegen die HD-Komposition **desselben Frames**, der Raum wird ueber den
Spielstand und `startScene` angesprungen.

Einzelnen Raum untersuchen:

    ./venv/bin/python3 harness/steps_room.py 25        # Abweichung je Aufbaustufe
    ./venv/bin/python3 harness/steps_diff.py 25        # was eine Stufe aendert

## Was gemessen wird und was nicht

Gemessen wird, ob die HD-Ebene zeigt, was die Engine im 8-Bit-Bild zeigt. Nicht gemessen wird,
ob die HD-Kunst selbst gut aussieht; das ist eine andere Frage und braucht Augen.

## Aufnahmen

`projects/comi-hd/work/dumps/` (nicht /tmp, das kann jederzeit verloren gehen). Der
Aufnahmelauf beendet sich selbst ueber `HD_EXIT_AFTER`, damit keine halben Dateien entstehen.
`harness/dumps.py` prueft jede Datei gegen ihre Kopfzeile, bevor verglichen wird.
