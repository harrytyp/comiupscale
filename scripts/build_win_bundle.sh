#!/usr/bin/env bash
# Baut das Windows-Bundle fuer das Release: Exe plus die Laufzeit-Dateien, die ein
# Windows-Rechner braucht. Aufruf: bash scripts/build_win_bundle.sh [ziel.zip]
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIN="$ROOT/release/windows"
OUT="${1:-/opt/data/dist/scummvm-win-bundle.zip}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for f in scummvm.exe SDL2.dll zlib1.dll scummvm.ini start_comi_hd.bat playback_comi_hd.bat INSTALL.txt; do
  [ -f "$WIN/$f" ] || { echo "FEHLT: $WIN/$f" >&2; exit 1; }
  cp "$WIN/$f" "$WORK/"
done

rm -f "$OUT"
# kein zip-Kommando auf diesem System, deshalb zipfile aus der Standardbibliothek
/opt/hermes/.venv/bin/python - "$WORK" "$OUT" <<'PY'
import sys, os, zipfile, hashlib
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in sorted(os.listdir(src)):
        z.write(os.path.join(src, name), name)
print("Bundle:", out)
print("Groesse:", os.path.getsize(out), "Byte")
with zipfile.ZipFile(out) as z:
    for i in z.infolist():
        print("  %-24s %10d Byte" % (i.filename, i.file_size))
print("SHA256:", hashlib.sha256(open(out, "rb").read()).hexdigest())
PY
