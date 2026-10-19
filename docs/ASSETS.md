# HD-Assets: wie sie entstehen und wie Aenderungen reproduzierbar bleiben

Die HD-Assets liegen nicht in git (Groesse). Verbindlich ist der Stand in `release/linux/hd/`.
Reproduzierbar ist er ueber die Skripte in `scripts/`, die alle versioniert sind.

## Reihenfolge

1. `scripts/full_pipeline.sh` — Extraktion mit nutcracker, Hochskalierung (RealESRGAN,
   `models/`, `.venv-upscale`), Texturepack bauen.
2. Nacharbeiten, die der Pipeline-Lauf nicht leistet. Jedes Skript schreibt direkt in die
   Release-Ordner und legt `.prev`-Sicherungen an:
   - `scripts/fix_missing_backgrounds.sh` — Hintergruende, die die Extraktion nicht liefert
   - `scripts/fix_room25_background.sh` — Raum 25 aus dem Roharchiv hochskaliert
   - `scripts/fix_scroll_backgrounds.sh` — scrollende Raeume, Randraender
   - `scripts/fix_shipcom_width.py` — Breite der Schiffskarten-Hintergruende
   - `scripts/add_object_alpha_v7.py`, `scripts/fix_mask_alpha.py`, `scripts/fix_magenta_mask.py`
     — Alphakanaele der Objekte und Kostueme

## Pruefen

`harness/final_sweep.py` faehrt jeden Raum headless, laedt ihn ueber einen Spielstand
(`harness/make_save.sh`) und vergleicht 8-Bit-Bild und HD-Komposition **desselben Frames**.
Ergebnis: `abweichung` je Pixel und `ueber40_prozent` (Anteil starker Abweichungen).

Stand vom 19.10.2026: 91 Raeume, keine ueber 10 Prozent, Mittel 0,6 Prozent.

## Vorlage fuer einen fehlenden Inhalt

Fehlt in einem Raum Inhalt, den das Original zeigt, ist die Reihenfolge:

1. Pruefen, ob der Inhalt im HD-Hintergrund steckt (`hd/backgrounds/<raum>_<name>.png`).
2. Pruefen, ob er in der Extraktion steckt (`nutcracker sputm room decode`).
3. Steckt er in keinem von beiden, ist er kein Asset, sondern wird zur Laufzeit gezeichnet.
   Dann ist die Engine dran, nicht die Texture (Raum 89: Figur unter dem Hand-Kostuem,
   Raum 25: Inventarobjekt ueber der Grossaufnahme).
