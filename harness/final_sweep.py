#!/usr/bin/env python3
"""Aufnahmelauf mit Spielstand: je Raum gleicher Frame, 8-Bit gegen HD-Komposition.

Der Raum wird ueber einen geladenen Spielstand und startScene angesprungen, also auf dem Weg
des Spiels. Damit laufen Raumskript, Oberflaechensperre (SO_USERPUT_OFF) und die
Akteurssichtbarkeit so, wie das Spiel sie setzt.

Der Lauf beendet sich selbst (HD_EXIT_AFTER), damit keine halb geschriebenen Aufnahmen
entstehen. Jede Aufnahme wird vor dem Vergleich gegen ihre Kopfzeile geprueft.

Aufruf: python3 harness/final_sweep.py <raum> [<raum> ...]
Umgebung: HD_SWEEP_OUT (Ergebnisordner), HD_SWEEP_FRAMES (Bilder je Raum, Vorgabe 90)
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
OUT = os.environ.get("HD_SWEEP_OUT", "/opt/data/projects/comi-hd/reports/final")
FRAMES = os.environ.get("HD_SWEEP_FRAMES", "90")


def dump(room, versuch=0):
    env = dict(os.environ, HD_DUMP_STEPS="1", HD_DUMP_REF="1", HD_LOAD_SLOT="1",
               HD_JUMP_ROOM=room, HD_DUMP_DIR=DUMPS, HD_EXIT_AFTER=FRAMES)
    try:
        subprocess.run([os.path.join(REPO, "scummvm/fork/scummvm"),
                        "--config=scummvm_video.ini", "--path=game", "comi"],
                       cwd=GAME, env=env, timeout=120 + versuch * 30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass
    return (os.path.exists(os.path.join(DUMPS, "hd_ref.ppm")),
            os.path.exists(os.path.join(DUMPS, "hd_step_4_kostueme.ppm")))


def main():
    rooms = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DUMPS, exist_ok=True)
    rows = []
    for room in rooms:
        ergebnis = None
        for versuch in (0, 1):
            ok_ref, ok_hd = dump(room, versuch)
            if not (ok_ref and ok_hd):
                continue
            try:
                ref = load_ppm(os.path.join(DUMPS, "hd_ref.ppm"))
                hd = scale_to(load_ppm(os.path.join(DUMPS, "hd_step_4_kostueme.ppm")),
                              ref.shape[1], ref.shape[0])
                ergebnis = compare(ref, hd)
                break
            except DumpError as exc:
                print("Raum %s: Aufnahme unbrauchbar (%s), neuer Versuch" % (room, exc), flush=True)
        if ergebnis is None:
            print("Raum %s: keine verwertbaren Bilder" % room, flush=True)
            continue
        mittel, ueber = ergebnis
        rows.append((room, round(mittel, 1), round(ueber, 1)))
        print("Raum %-4s Abweichung %5.1f  ueber 40: %4.1f%%" % (room, mittel, ueber), flush=True)

    path = os.path.join(OUT, "gleicher_frame.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["raum", "abweichung", "ueber40_prozent"])
        w.writerows(rows)

    if rows:
        stark = [r[2] for r in rows]
        print("\nRaeume: %d, ueber 40 im Mittel %.2f%%, schlechtester %.1f%%, ueber 10: %d" %
              (len(rows), sum(stark) / len(stark), max(stark), sum(1 for v in stark if v > 10)))


if __name__ == "__main__":
    main()
