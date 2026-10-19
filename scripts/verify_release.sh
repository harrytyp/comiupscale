#!/usr/bin/env bash
# Pruef-Tor fuer einen Release-Stand. Ein Aufruf, klare Rueckmeldung, Rueckgabewert 0 nur
# wenn alles stimmt.
#
#   bash scripts/verify_release.sh
#
# Geprueft wird:
#   1. Engine-Binary vorhanden und startfaehig
#   2. HD-Assets gegen die Pruefsummenliste (docs/asset-manifest.txt)
#   3. Texture-Packs enthalten jede Asset-Datei genau einmal
#   4. Raumvergleich: kein Raum ueber 10 Prozent starker Abweichung, Mittel unter 1 Prozent
#      (Grundlage: harness/final_sweep.py, Ergebnis in reports/final_save/gleicher_frame.csv)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/venv/bin/python3"
[ -x "$PY" ] || PY=python3
FEHLER=0

sag() { printf '%-46s %s\n' "$1" "$2"; }
ok()  { sag "$1" "ok"; }
bad() { sag "$1" "FEHLER"; FEHLER=$((FEHLER + 1)); }

echo "== 1. Engine"
BIN="$ROOT/release/linux/scummvm"
if [ -x "$BIN" ]; then
    VERSION="$("$BIN" --version 2>/dev/null | head -1)"
    ok "release/linux/scummvm (${VERSION:-Version unbekannt})"
else
    bad "release/linux/scummvm fehlt"
fi

echo "== 2. HD-Assets"
if "$PY" scripts/asset_manifest.py --check > /tmp/hd_manifest_check.log 2>&1; then
    ok "Pruefsummen ($(grep -c . docs/asset-manifest.txt) Zeilen)"
else
    bad "Pruefsummen weichen ab (siehe /tmp/hd_manifest_check.log)"
    tail -5 /tmp/hd_manifest_check.log
fi

echo "== 3. Texture-Packs"
if "$PY" scripts/check_texture_packs.py > /tmp/hd_pack_check.log 2>&1; then
    ok "$(head -2 /tmp/hd_pack_check.log | tail -1)"
else
    bad "Packs unvollstaendig oder doppelt (siehe /tmp/hd_pack_check.log)"
    tail -5 /tmp/hd_pack_check.log
fi

echo "== 4. Raumvergleich"
CSV="/opt/data/projects/comi-hd/reports/final_save/gleicher_frame.csv"
if [ -s "$CSV" ]; then
    "$PY" - "$CSV" <<'PY'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1]), delimiter=";"))
werte = [float(r["ueber40_prozent"]) for r in rows if r.get("ueber40_prozent")]
if not werte:
    print("keine Werte"); sys.exit(2)
schlecht = [r["raum"] for r in rows if float(r["ueber40_prozent"]) > 10]
mittel = sum(werte) / len(werte)
print("Raeume %d, Mittel %.2f%%, ueber 10%%: %d %s" % (len(werte), mittel, len(schlecht), schlecht[:8]))
sys.exit(0 if (not schlecht and mittel < 1.0) else 1)
PY
    if [ $? -eq 0 ]; then ok "Raumvergleich innerhalb der Schwellen"; else bad "Raumvergleich ueber Schwelle"; fi
else
    bad "kein Messergebnis ($CSV fehlt)"
fi

echo
if [ "$FEHLER" -eq 0 ]; then
    echo "GESAMT: bestanden"
    exit 0
fi
echo "GESAMT: $FEHLER Punkt(e) offen"
exit 1
