# Übergabe: Doppel-Asset-Bug (Comi HD)

Stand nach der Sitzung vom 24.10.2026. Ziel: ein Akteur wird doppelt gezeichnet — einmal in
8 Bit, einmal in HD, um 3 bis 8 Pixel versetzt.

## Fertig und geprüft

Schatten-Bug (Preview, nur Guybrush): 686 Frames geprüft, **0** Reste. 343 Frames aus der
Alpha-Maske bereinigt, Originale in `hd/costumes_backup/`.
Skript: `harness/guybrush_braunsaum_entfernen.py`
Regel: breite, flache braune Fläche unten (Breite > 55 % des Bildes, Höhe < 25 %) wird auf
Alpha 0 gesetzt — Stiefel und Kleidung bleiben, weil sie schmal und hoch sind.

## Offen: Doppel-Asset

Betroffen: Raum 44, Akteure `akos=2` (Spielfigur) und `akos=251`.

Messwerte:
- Versatz 3 bis 8 Pixel (Spitzenprofile der Stufenbilder: 172 gegen 180, 299 gegen 302).
- Kamera-Fenster ist es nicht: `xstart=46`, `camLinks=46`, deckungsgleich.
- Beide Akteure haben HD-Einträge (`hd_cost_bounds.log`), es fehlt also nichts.
- Restmessung Raum 44: 3,87 % magenta, ohne Figuren 0,13 %.

Ausgeschlossen (jeweils gemessen):
- `drawX` doppelt gerechnet → 4,30 % (schlechter), verworfen.
- `_hdRelX`/`_hdRelY` veraltet → 3,87 % unverändert, verworfen.
- Objekte in der Fehlt-Maske ohne Bild → eigener Fix, brachte 86 von 1,31 auf 0,02 %.
- Schattenakteure ausgelassen → eigener Fix, brachte 86 von 8,65 auf 1,31 %.

Verdächtige Stelle: `gfx.cpp:2920`
```cpp
int64 hdCX = (int64)(drawX + limbDrawX * sclX / 255) * hdW / MAX(1, visW);
```
`limbDrawX` stammt aus `_hdLimbDrawX[]`, gesetzt in `akos.cpp:393` (`xMoveCur`).

## Nächster Schritt (ohne Build)

1. **Frame-Nummerierung prüfen** — die Annahme `h00040.ppm` war falsch, deshalb lief der
   letzte Vergleich ins Leere. Erst `ls hd_seq/` ansehen.
2. Zwei Läufe in Raum 44: einmal normal, einmal `HD_NO_ACTORS=1`, je mit `HD_DUMP_SEQ=1`.
3. Differenz der beiden Bilder = Fläche der 8-Bit-Figur.
4. HD-Fläche aus `hd_step_4_kostueme.ppm` minus `hd_step_1_hintergrund.ppm`.
5. Beide Flächen ins gleiche Koordinatensystem (Faktor 4) bringen, Abstand und Richtung
   messen. Das ist der Versatz — und die Richtung sagt, welche der beiden Zeichnungen falsch
   liegt.

## Werkzeuge

`harness/magenta_check.py` (Anteil 8 Bit je Raum), `magenta_orte.py` (Ort im Bild),
`HD_NO_ACTORS` / `HD_NO_OBJECTS` (Zeichenweg abschalten), `HD_SPY=1` (Protokolle:
`hd_cost_bounds.log`, `hd_actor_probe.log`, `hd_place.log`, `hd_maskobj.log`, `hd_fg.log`),
`scripts/count_obim.py`, `obim_liste.py`, `dump_dobj.py`.

Build: `bash /opt/data/tmp/build_fork_seq.sh`, danach `bash scripts/install_build.sh`.
