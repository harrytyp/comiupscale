#!/usr/bin/env bash
# Fehlende Hintergruende fuer die nicht scrollbaren Raeume erzeugen.
#
# Befund 2026-09-26: Das HD-Paket hat 60 Raeume mit Hintergrund, die Extraktion aus den
# Spieldaten liefert 93. 34 Raeume laden deshalb die Ersatztextur, die als Platzhalter
# erscheint, wenn zur Raumnummer keine eigene Datei existiert (hd_asset_manager.cpp sucht ueber
# die fuehrende Zahl im Dateinamen). 58 sind inhaltlich in Ordnung.
#
# Quelle: die frische Extraktion (tools/nutcracker room decode), jeweils <raum>_<name>.png in
# 8-Bit-Raumgroesse. Aufruf: bash scripts/fix_missing_backgrounds.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv-upscale/bin/python"
EXTRACT="${EXTRACT:-/tmp/comi_extract/COMI/IMAGES/backgrounds}"
WORK="${WORK:-/tmp/missing_bg}"
ROOMS="${ROOMS:-7 8 39 52 54 56 57 58 59 62 63 64 65 66 67 68 69 71 73 74 76 77 78 79 80 81 82 83 84 85 88 92 93 94}"

mkdir -p "$WORK/in" "$WORK/out"
echo "=== Rohbilder einsammeln ==="
"$PY" - "$EXTRACT" "$WORK/in" "$ROOMS" <<'PYEOF'
import sys, os, glob, shutil
extract, out, rooms = sys.argv[1], sys.argv[2], sys.argv[3].split()
n = 0
for r in rooms:
    hits = sorted(glob.glob(os.path.join(extract, "%04d_*.png" % int(r))))
    if not hits:
        print("  Raum %s: kein Rohbild" % r); continue
    shutil.copyfile(hits[0], os.path.join(out, os.path.basename(hits[0])))
    n += 1
print("  %d Rohbilder" % n)
PYEOF

echo "=== Hochskalieren (4x, Modell RealESRGAN_x4plus_anime_6B) ==="
COMI_UPSCALE_MODEL=RealESRGAN_x4plus_anime_6B "$PY" "$ROOT/scripts/upscale_esrgan.py" \
  --input "$WORK/in" --output "$WORK/out" --pattern "*.png" 2>&1 | tail -3

echo "=== Einsetzen (alle vier Kopien, alte Fassung in den Backup-Ordner) ==="
"$PY" - "$WORK/out" "$ROOT" <<'PYEOF'
import sys, os, glob, shutil, time
src, root = sys.argv[1], sys.argv[2]
backup = "/opt/data/backups/comi-hd-bg-%s" % time.strftime("%Y%m%d-%H%M%S")
os.makedirs(backup, exist_ok=True)
files = sorted(glob.glob(src + "/*.png"))
for rel in ("release/linux/hd", "release/linux/game/hd", "release/windows/hd", "scummvm/fork/hd"):
    dst_dir = os.path.join(root, rel, "backgrounds")
    for p in files:
        base = os.path.basename(p)
        dst = os.path.join(dst_dir, base)
        if os.path.exists(dst):
            shutil.copyfile(dst, os.path.join(backup, base))
        shutil.copyfile(p, dst)
    print("  %-24s %d Dateien" % (rel, len(files)))
print("  alte Fassungen in %s" % backup)
PYEOF
echo fertig
