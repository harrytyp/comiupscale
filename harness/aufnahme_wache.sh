#!/usr/bin/env bash
# Gesundheitscheck fuer Messlaeufe: hat der Lauf wirklich HD-Bilder geschrieben?
#
# Aufruf: aufnahme_wache.sh <aufnahmeordner> [mindestzahl]
#
# Zaehlt brauchbare PPM-Aufnahmen: Datei vorhanden, Kopfzeile vollstaendig, Breite und
# Hoehe groesser 0, Bilddaten nicht abgeschnitten. Eine 0 hohe Kompositflaeche schreibt
# nur "P6\n1280 0\n255\n" — solche Dateien zaehlen hier NICHT als Bild. Genau dieser
# Fall hat am 25.10. wie eine vorhandene Aufnahme ausgesehen, waehrend die Messung
# in Wahrheit nichts gemessen hat.
#
# Rueckgabe: 0 = mindestens <mindestzahl> brauchbare Bilder vorhanden
#            2 = zu wenige oder keine, Meldung auf stderr (Messung abbrechen!)
set -uo pipefail

ORDNER=${1:?Aufnahmeordner fehlt}
MIN=${2:-1}
# Nur die HD-Bilder zaehlen, nicht die 8-Bit-Referenzen daneben (h00012.ppm / r00012.ppm).
# Mit Umleitung (LD_PRELOAD-Shim) heissen sie z1_*.ppm, deshalb ist das Muster einstellbar.
MUSTER=${3:-}
if [ -z "$MUSTER" ]; then
	if /usr/bin/ls "$ORDNER"/h*.ppm > /dev/null 2>&1; then
		MUSTER='h*.ppm'
	else
		MUSTER='*.ppm'
	fi
fi

if [ ! -d "$ORDNER" ]; then
	echo "ABBRUCH: Aufnahmeordner fehlt: $ORDNER — die Messung hat nichts aufgenommen." >&2
	exit 2
fi

anzahl=0
leer=0
kaputt=0
for datei in "$ORDNER"/$MUSTER; do
	[ -e "$datei" ] || continue
	{ read -r magic; read -r dims; } < "$datei" 2>/dev/null || { kaputt=$((kaputt + 1)); continue; }
	[ "$magic" = "P6" ] || { kaputt=$((kaputt + 1)); continue; }
	w=${dims%% *}
	h=${dims##* }
	case "$w$h" in *[!0-9]*|'') kaputt=$((kaputt + 1)); continue ;; esac
	if [ "$w" -le 0 ] || [ "$h" -le 0 ]; then
		leer=$((leer + 1))
		continue
	fi
	bytes=$(/usr/bin/stat -c %s "$datei" 2>/dev/null || echo 0)
	# Kopf "P6\n<w> <h>\n255\n" ist mindestens 15 Byte lang, danach 3 Byte je Punkt.
	if [ "$bytes" -lt $((15 + w * h * 3)) ]; then
		kaputt=$((kaputt + 1))
		continue
	fi
	anzahl=$((anzahl + 1))
done

if [ "$anzahl" -lt "$MIN" ]; then
	echo "ABBRUCH: nur $anzahl brauchbare Aufnahmen in $ORDNER (verlangt: $MIN)." >&2
	echo "         leere Flaechen (Hoehe 0): $leer, unvollstaendig/kein PPM: $kaputt" >&2
	echo "         Das ist eine Leermessung, kein Messergebnis. Lauf wiederholen." >&2
	exit 2
fi

echo "Aufnahme-Wache: $anzahl brauchbare Aufnahmen in $ORDNER (verlangt: $MIN)."
[ "$leer" -gt 0 ] && echo "Aufnahme-Wache: $leer leere Flaechen (Hoehe 0) uebersprungen."
[ "$kaputt" -gt 0 ] && echo "Aufnahme-Wache: $kaputt unbrauchbare Dateien uebersprungen."
exit 0
