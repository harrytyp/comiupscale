#!/usr/bin/env python3
"""Misst fuer einen Raum jede Aufbaustufe gegen das 8-Bit-Bild desselben Frames.

Aufruf: python3 harness/steps_room.py 25 [sekunden]

Der Raum wird ueber den Spielstand und startScene angesprungen (wie im Spiel). Ausgegeben
wird je Stufe die mittlere Abweichung und der Anteil starker Abweichungen. Damit ist
sichtbar, welche Stufe den Unterschied macht: Hintergrund, Vordergrund, Objekte, Kostueme.
"""
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dumps import DumpError, compare, load_ppm, scale_to  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(REPO, "release/linux")
DUMPS = os.environ.get("HD_DUMP_DIR", "/opt/data/projects/comi-hd/work/dumps")


def run(room, sekunden):
    env = dict(os.environ, HD_DUMP_STEPS="1", HD_DUMP_REF="1",
               HD_LOAD_SLOT="1", HD_JUMP_ROOM=room, HD_DUMP_DIR=DUMPS,
               HD_EXIT_AFTER=str(os.environ.get("HD_EXIT_AFTER", "90")))
    try:
        subprocess.run([os.path.join(REPO, "scummvm/fork/scummvm"),
                        "--config=scummvm_video.ini", "--path=game", "comi"],
                       cwd=GAME, env=env, timeout=sekunden,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass


def main():
    room = sys.argv[1]
    sekunden = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    os.makedirs(DUMPS, exist_ok=True)
    run(room, sekunden)

    ref_path = os.path.join(DUMPS, "hd_ref.ppm")
    if not os.path.exists(ref_path):
        print("keine Aufnahme fuer Raum %s" % room)
        return 2
    try:
        ref = load_ppm(ref_path)
    except DumpError as exc:
        print("8-Bit-Aufnahme unbrauchbar: %s" % exc)
        return 2

    print("Raum %s, 8-Bit %dx%d" % (room, ref.shape[1], ref.shape[0]))
    for path in sorted(glob.glob(os.path.join(DUMPS, "hd_step_*.ppm"))):
        try:
            img = scale_to(load_ppm(path), ref.shape[1], ref.shape[0])
            mittel, ueber = compare(ref, img)
        except DumpError as exc:
            print("  %-26s unbrauchbar: %s" % (os.path.basename(path)[8:-4], exc))
            continue
        print("  %-26s Abweichung %6.1f  ueber 40 %5.1f%%" %
              (os.path.basename(path)[8:-4], mittel, ueber))
    return 0


if __name__ == "__main__":
    sys.exit(main())
