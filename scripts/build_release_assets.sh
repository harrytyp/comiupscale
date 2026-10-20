#!/usr/bin/env bash
# Baut die ausgelieferten HD-Assets von den Spieldaten bis zum Release-Stand.
#
# Ein Aufruf, feste Reihenfolge: Extraktion und Hochskalierung (full_pipeline.sh), dann die
# Nacharbeiten, die der Pipeline-Lauf nicht leistet. Jeder Schritt schreibt in die
# Release-Ordner und legt .prev-Sicherungen an.
#
#   bash scripts/build_release_assets.sh            # alles
#   bash scripts/build_release_assets.sh --check    # nur Pruefsummen vergleichen
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv-upscale/bin/python3"
[ -x "$PY" ] || PY=python3

if [ "${1:-}" = "--check" ]; then
    exec "$PY" scripts/asset_manifest.py --check
fi

echo "== 1/2 Pipeline: Extraktion und Hochskalierung =="
bash scripts/full_pipeline.sh

echo "== 2/2 Nacharbeiten =="
# Reihenfolge ist bindend: die Hintergruende zuerst, danach die Alphakanaele von Objekten
# und Kostuemen, weil die Alpha-Schritte auf den fertigen Bildern arbeiten.
bash  scripts/fix_missing_backgrounds.sh
bash  scripts/fix_room25_background.sh
bash  scripts/fix_scroll_backgrounds.sh
"$PY" scripts/fix_shipcom_width.py
"$PY" scripts/add_object_alpha_v7.py
"$PY" scripts/fix_mask_alpha.py
"$PY" scripts/fix_magenta_mask.py

echo "== 3/4 Texture-Packs =="
# Die Packs werden aus dem fertigen HD-Ordner gebaut, also nach allen Nacharbeiten.
"$PY" scripts/rebuild_texture_packs.py
"$PY" scripts/check_texture_packs.py

echo "== 4/4 Pruefsummen =="
"$PY" scripts/asset_manifest.py
echo "Fertig. Danach: bash scripts/verify_release.sh"
echo "Vergleich mit dem ausgelieferten Stand: bash scripts/build_release_assets.sh --check"
