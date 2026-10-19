"""Aufnahmelauf mit Spielstand: je Raum gleicher Frame, 8-Bit gegen HD-Komposition.

Der Raum wird ueber einen geladenen Spielstand und startScene angesprungen, also auf dem Weg
des Spiels. Damit laufen Raumskript, Oberflaechensperre (SO_USERPUT_OFF) und die
Akteurssichtbarkeit so, wie das Spiel sie setzt. Der Startparameter --boot-param springt
dagegen mitten in den Raum, ohne dass das Raumskript je laeuft.

Voraussetzung: ein Spielstand in `saves/comi.s01` (anlegen mit harness/make_save.sh).
"""
import csv
import os
import subprocess
import sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(REPO, "release/linux")
OUT = os.environ.get("HD_SWEEP_OUT", "/opt/data/projects/comi-hd/reports/final")
os.makedirs(OUT, exist_ok=True)
SECONDS = int(os.environ.get("HD_SWEEP_SECONDS", "30"))


def dump(room, laufzeit=SECONDS):
    for f in ("/tmp/hd_ref.ppm", "/tmp/hd_step_4_kostueme.ppm"):
        try:
            os.unlink(f)
        except OSError:
            pass
    env = dict(os.environ, HD_DUMP_STEPS="1", HD_DUMP_REF="1", HD_LOAD_SLOT="1", HD_JUMP_ROOM=room)
    try:
        subprocess.run([os.path.join(REPO, "scummvm/fork/scummvm"), "--config=scummvm_video.ini",
                        "--path=game", "comi"], cwd=GAME, env=env, timeout=laufzeit,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass
    return os.path.exists("/tmp/hd_ref.ppm"), os.path.exists("/tmp/hd_step_4_kostueme.ppm")


def compare(ref_path, hd_path):
    ref = Image.open(ref_path).convert("RGB")
    hd = Image.open(hd_path).convert("RGB")
    w, h = ref.size
    scale = hd.width // w if w and hd.width % w == 0 else 2
    crop = hd.crop((0, 0, min(hd.width, w * scale), min(hd.height, h * scale)))
    crop = crop.resize((w, h), Image.LANCZOS)
    a = np.asarray(ref, dtype=np.int16)
    b = np.asarray(crop, dtype=np.int16)
    d = np.abs(a - b).max(axis=2)
    return float(d.mean()), float((d > 40).mean() * 100)


def main():
    rooms = sys.argv[1:]
    rows = []
    for room in rooms:
        mittel = ueber = None
        for versuch in (0, 1, 2):
            # Der Aufnahmelauf wird per timeout beendet und kann die Bilddatei mitten im
            # Schreiben abschneiden. Dann mit laengerer Laufzeit noch einmal.
            ok_ref, ok_hd = dump(room, SECONDS + versuch * 5)
            if not (ok_ref and ok_hd):
                continue
            try:
                mittel, ueber = compare("/tmp/hd_ref.ppm", "/tmp/hd_step_4_kostueme.ppm")
                break
            except OSError:
                mittel = ueber = None
        if mittel is None:
            print("Raum %s: keine verwertbaren Bilder" % room, flush=True)
            continue
        rows.append((room, round(mittel, 1), round(ueber, 1)))
        print("Raum %-4s Abweichung %5.1f  ueber 40: %4.1f%%" % (room, mittel, ueber), flush=True)

    path = os.path.join(OUT, "gleicher_frame.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["raum", "abweichung", "ueber40_prozent"])
        w.writerows(rows)

    if rows:
        stark = [r[2] for r in rows]
        print("\nRaeume: %d, ueber 40 im Mittel %.1f%%, schlechtester %.1f%%, ueber 10: %d" %
              (len(rows), sum(stark) / len(stark), max(stark), sum(1 for v in stark if v > 10)))


if __name__ == "__main__":
    main()
