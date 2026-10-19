#!/usr/bin/env python3
"""Prueft einen eigenen HD-Ordner (eigene Upscales) auf Namen, Format und Vollstaendigkeit.

Damit laesst sich ein Mod vor dem Start pruefen, statt Fehler erst im Spiel zu sehen.

    python3 scripts/validate_hd_mod.py --dir /pfad/zu/meinem/hd
    python3 scripts/validate_hd_mod.py --dir ... --referenz release/linux/hd

Geprueft wird:

- erlaubte Ordner: backgrounds, costumes, objects, objects_layers, fonts
- Hintergruende: `backgrounds/NNNN_name.png`
- Kostueme: `costumes/LFLF_NNNN_AKOS_NNNN_aframe_N.png`
- Objekte: `objects/NNNN_name_NNNN.png`
- alle Bilder PNG und lesbar
- mit --referenz: welche Dateien dort fehlen (unvollstaendiger Mod)
"""
import argparse
import os
import re
import sys

from PIL import Image

ORDNER = {"backgrounds", "costumes", "objects", "objects_layers", "fonts"}
MUSTER = {
    "backgrounds": re.compile(r"^\d{4}_[a-z0-9_.-]+\.png$", re.I),
    "costumes": re.compile(r"^LFLF_\d{4}_AKOS_\d{4}_aframe_\d+\.png$", re.I),
    "objects": re.compile(r"^\d{4}_[a-z0-9_.-]+_\d{4}\.png$", re.I),
    "objects_layers": re.compile(r"^\d{4}_[a-z0-9_.-]+_\d{4}\.png$", re.I),
    "fonts": re.compile(r".+", re.I),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="HD-Ordner des Mods")
    ap.add_argument("--referenz", help="vollstaendiger HD-Ordner zum Vergleichen")
    ap.add_argument("--max-meldungen", type=int, default=20)
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print("Ordner fehlt: %s" % args.dir)
        return 2

    fehler = []
    warnungen = []
    gefunden = set()
    anzahl = {}

    for base, dirs, files in os.walk(args.dir):
        rel_dir = os.path.relpath(base, args.dir).replace(os.sep, "/")
        if rel_dir == ".":
            rel_dir = ""
        if rel_dir:
            top = rel_dir.split("/")[0]
            if top not in ORDNER:
                warnungen.append("unbekannter Ordner: %s" % rel_dir)
                continue

        for name in files:
            rel = (rel_dir + "/" + name) if rel_dir else name
            gefunden.add(rel.replace(os.sep, "/"))
            top = rel_dir.split("/")[0] if rel_dir else ""
            anzahl[top] = anzahl.get(top, 0) + 1

            muster = MUSTER.get(top)
            if muster and not muster.match(name):
                fehler.append("Name passt nicht: %s" % rel)
                continue
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
                if not name.lower().endswith(".png"):
                    fehler.append("kein PNG: %s" % rel)
                    continue
                try:
                    with Image.open(os.path.join(base, name)) as im:
                        im.verify()
                except Exception as exc:  # noqa: BLE001
                    fehler.append("Bild nicht lesbar: %s (%s)" % (rel, exc))
            elif top in MUSTER:
                fehler.append("keine Bilddatei: %s" % rel)

    print("Dateien: %d" % len(gefunden))
    for top in sorted(anzahl):
        print("  %-16s %d" % (top or "(Wurzel)", anzahl[top]))

    if args.referenz:
        referenz = set()
        for base, _dirs, files in os.walk(args.referenz):
            for name in files:
                referenz.add(os.path.relpath(os.path.join(base, name), args.referenz).replace(os.sep, "/"))
        fehlend = sorted(referenz - gefunden)
        print("gegen Referenz: %d fehlen, %d zusaetzlich" % (len(fehlend), len(gefunden - referenz)))
        for rel in fehlend[:args.max_meldungen]:
            print("  fehlt: %s" % rel)

    for text in warnungen[:args.max_meldungen]:
        print("  Hinweis: %s" % text)
    for text in fehler[:args.max_meldungen]:
        print("  Fehler: %s" % text)
    print("Ergebnis: %d Fehler, %d Hinweise" % (len(fehler), len(warnungen)))
    return 0 if not fehler else 1


if __name__ == "__main__":
    sys.exit(main())
