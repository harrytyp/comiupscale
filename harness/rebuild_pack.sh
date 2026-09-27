#!/usr/bin/env bash
# Baut das Assetpaket neu und laedt es hoch, danach die Linux-Binary in den Release-Ordner.
set -u
REPO=/opt/data/local/comi-hd-repo
PY=/opt/hermes/.venv/bin/python
cd "$REPO" || exit 1

echo "=== Linux-Binary uebernehmen ==="
cp -f "$REPO/scummvm/fork/scummvm" "$REPO/release/linux/scummvm"
ls -la "$REPO/release/linux/scummvm" | awk '{print $5, $9}'

echo "=== Paket bauen ==="
"$PY" scripts/build_texture_pack.py --dir release/linux/hd \
  --out /opt/data/dist/hd_assets_part1.zip \
  --folders backgrounds objects objects_layers fonts 2>&1 | tail -8

echo "=== Groesse und Pruefsumme ==="
stat -c '%s %n' /opt/data/dist/hd_assets_part1.zip
sha256sum /opt/data/dist/hd_assets_part1.zip

echo "=== Inhalt pruefen: sind die vier Karten 4992 breit? ==="
"$PY" - <<'PYEOF'
import zipfile
from PIL import Image
import io
z = zipfile.ZipFile("/opt/data/dist/hd_assets_part1.zip")
for name in z.namelist():
    base = name.rsplit("/", 1)[-1]
    if base.startswith(("0040_", "0041_", "0042_", "0043_")) and base.endswith(".png"):
        im = Image.open(io.BytesIO(z.read(name)))
        print("  %-40s %dx%d" % (base, *im.size))
PYEOF
echo "PAKET_FERTIG"
