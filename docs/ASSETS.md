# HD-Assets: wie sie entstehen und wie Aenderungen reproduzierbar bleiben

Die HD-Assets liegen nicht in git (Groesse). Verbindlich ist der Stand in `release/linux/hd/`.
Reproduzierbar ist er ueber die Skripte in `scripts/`, die alle versioniert sind.

## Ein Aufruf

    bash scripts/build_release_assets.sh          # Pipeline und Nacharbeiten
    bash scripts/build_release_assets.sh --check  # Pruefsummen gegen den Release-Stand

Das Skript ruft die Schritte unten in fester Reihenfolge auf. Es bricht bei jedem Fehler ab
(`set -e`), damit kein halber Stand als fertig gilt.

## Modelle (nicht in git, Groesse)

    models/RealESRGAN_x4plus.pth          63,9 MB  sha256 4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1
    models/RealESRGAN_x4plus_anime_6B.pth 17,1 MB  sha256 f872d837d3c90ed2e05227bed711af5671a6fd1c9f7d7e91c911a61f155e99da

Beide Dateien vor einem Lauf gegen diese Summen pruefen. Ohne die richtige Gewichtsdatei
entsteht ein anderer Stand, ohne dass es auffaellt.

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

## Packs

Die drei Texture-Packs `release/hd_assets_part1..3.zip` werden aus `release/linux/hd/`
gebaut, deterministisch nach Dateiname:

    python3 scripts/rebuild_texture_packs.py

Zuordnung: `backgrounds/` und `audio/` nach part1, `objects/`, `objects_layers/`, `fonts/`
und `object_map.json` nach part3, Kostueme reihum nach SHA-1 des Dateinamens modulo 3 auf
alle drei Packs. Am Ende prueft das Skript, dass jede Datei genau einmal enthalten ist.

Stand 19.10.2026: die Packs vom 18.07.2026 enthielten 436 Dateien nicht, die im HD-Ordner
lagen (Hintergruende 0039 bis 0094, Audio). Sie werden deshalb neu gebaut; der vorherige Stand
wandert beim Neubau nach `.prev`.

## Pruefen

`scripts/asset_manifest.py` schreibt Pfad, Groesse und SHA-256 jeder Datei unter
`release/linux/hd/` nach `docs/asset-manifest.txt` (26662 Dateien, 5,3 GB). `--check` meldet
fehlende, neue und abweichende Dateien. Damit ist der ausgelieferte Texturestand nachweisbar,
auch ohne die Assets in git.

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
