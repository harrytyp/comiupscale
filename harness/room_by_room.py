#!/usr/bin/env python3
"""Geht Raum fuer Raum durch und schreibt nach jedem Raum sofort in die Ergebnisdatei.

Kein Sammellauf: jeder Raum wird einzeln gestartet, gemessen und protokolliert. Bricht der
Lauf ab, steht alles bis zum letzten Raum bereits in der Datei.

Aufruf: python3 harness/room_by_room.py [raum ...]
Ohne Raeume: alle Raeume aus reports/sd.
"""
import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dumps import DumpError, compare, load_ppm, scale_to  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(REPO, "release/linux")
DUMPS = os.environ.get("HD_DUMP_DIR", "/opt/data/projects/comi-hd/work/dumps")
OUT = os.environ.get("HD_SWEEP_OUT", "/opt/data/projects/comi-hd/reports/raumweise")
CSV = os.path.join(OUT, "gleicher_frame.csv")
TIMEOUT = int(os.environ.get("HD_SWEEP_TIMEOUT", "25"))


def messe(raum):
    for name in ("hd_ref.ppm", "hd_step_4_kostueme.ppm"):
        pfad = os.path.join(DUMPS, name)
        if os.path.exists(pfad):
            os.replace(pfad, pfad + ".alt")
    env = dict(os.environ, HD_DUMP_STEPS="1", HD_DUMP_REF="1", HD_LOAD_SLOT="1",
               HD_JUMP_ROOM=raum, HD_DUMP_DIR=DUMPS, HD_EXIT_AFTER="70", HD_DUMP_AT="60",
               HD_FIXED_DELTA=os.environ.get("HD_FIXED_DELTA", "20"))
    try:
        subprocess.run([os.path.join(REPO, "scummvm/fork/scummvm"),
                        "--config=scummvm_video.ini", "--path=game", "comi"],
                       cwd=GAME, env=env, timeout=TIMEOUT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass
    ref_p = os.path.join(DUMPS, "hd_ref.ppm")
    hd_p = os.path.join(DUMPS, "hd_step_4_kostueme.ppm")
    if not (os.path.exists(ref_p) and os.path.exists(hd_p)):
        return None
    ref = load_ppm(ref_p)
    # Pflichtpruefung: das Intro zeigt eine Nahaufnahme des Schilds am Scumm Bar. Ist das
    # Bild damit identisch, wurde kein Raum aufgenommen, sondern der Intro-Ausschnitt.
    # Ohne diese Pruefung besteht jede Schwelle, weil zwei gleiche Bilder verglichen werden.
    intro_p = os.path.join(DUMPS, "intro_ref.ppm")
    if os.path.exists(intro_p):
        intro = load_ppm(intro_p)
        if intro.shape == ref.shape and float(abs(int(ref.astype("int16").mean()) - int(intro.astype("int16").mean()))) < 1:
            d = (ref.astype("int16") - intro.astype("int16"))
            if float((d * d).mean()) ** 0.5 < 4.0:
                print("Raum %s: Intro statt Raum (Bild identisch mit dem Anfang) — ungueltig" % raum, flush=True)
                return None
    hd = scale_to(load_ppm(hd_p), ref.shape[1], ref.shape[0])
    return compare(ref, hd)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DUMPS, exist_ok=True)
    raeume = sys.argv[1:]
    if not raeume:
        basis = "/opt/data/projects/comi-hd/reports/sd"
        raeume = sorted((d for d in os.listdir(basis) if d.isdigit()), key=int)

    fertig = set()
    if os.path.exists(CSV):
        with open(CSV, newline="") as f:
            # Raeume ohne Aufnahme gelten nicht als erledigt und werden erneut versucht.
            fertig = {r["raum"] for r in csv.DictReader(f, delimiter=";")
                      if (r.get("ueber40_prozent") or "").strip()}
        print("bereits gemessen: %d" % len(fertig), flush=True)
    else:
        with open(CSV, "w", newline="") as f:
            csv.writer(f, delimiter=";").writerow(["raum", "abweichung", "ueber40_prozent"])

    for raum in raeume:
        if raum in fertig:
            continue
        ergebnis = messe(raum)
        if ergebnis is None:
            print("Raum %-4s keine Aufnahme" % raum, flush=True)
            with open(CSV, "a", newline="") as f:
                csv.writer(f, delimiter=";").writerow([raum, "", ""])
            continue
        mittel, ueber = ergebnis
        with open(CSV, "a", newline="") as f:
            csv.writer(f, delimiter=";").writerow([raum, round(mittel, 1), round(ueber, 1)])
        print("Raum %-4s %5.1f  ueber 40: %4.1f%%" % (raum, mittel, ueber), flush=True)


if __name__ == "__main__":
    main()
