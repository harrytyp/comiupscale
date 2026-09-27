#!/usr/bin/env bash
# Zeitschiene des Inventarzustands in einem Schiffskampfraum.
# Zeigt, ab welchem Bild das Inventar offen ist und ob es wieder zugeht.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/release/linux" || exit 1

for R in 40 25; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 20 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "===== Raum $R: rc=$? ====="
	echo "  Verlauf invActive (nur Wechsel):"
	grep -oE "invActive=[0-9]" hd_state.log 2>/dev/null | uniq -c | head -8
	echo "  Erste und letzte Meldung zum Inventarobjekt:"
	grep -oE "(CULL|RENDER) obj=114[^\"]*" hd_state.log 2>/dev/null | head -2
	grep -oE "(CULL|RENDER) obj=114[^\"]*" hd_state.log 2>/dev/null | tail -2
	echo "  Anzahl Bilder: $(ls -1 /tmp/hd_scan/*.ppm 2>/dev/null | wc -l)"
done
echo "ZEITSCHIENE_DURCH"
