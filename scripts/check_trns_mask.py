#!/usr/bin/env python3
"""Belegprobe: Ist der TRNS-Index im Raumheader die Maske der Objektbilder?

Liest fuer ausgewaehlte Raeume den Transparency-Index aus dem Raumheader und
zeigt ihn zusammen mit der Palettenfarbe. Vergleicht ihn danach mit dem
Palettenindex, der in den extrahierten Quellbildern die Randflaeche stellt.

Aufruf:
    PYTHONPATH=tools python3 scripts/check_trns_mask.py <GAME_DIR> [room ...]
"""
import logging
import sys

import numpy as np
from PIL import Image

logging.disable(logging.CRITICAL)

sys.path.insert(0, "tools")

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.room.pproom import get_rooms, read_room_settings, read_objects
from nutcracker.sputm import preset  # noqa: F401

sputm = preset.sputm


def main():
    game_dir = sys.argv[1]
    wanted = [int(x) for x in sys.argv[2:]] or [1, 3, 22, 28]
    gameres = open_game_resource(game_dir + "/COMI.LA0")
    root_list = list(gameres.read_resources())
    found = []
    for t in root_list:
        for lflf in get_rooms(t.children()):
            room_id = lflf.attribs.get("gid", 0)
            if room_id not in wanted:
                continue
            header, palette, room, rmim = read_room_settings(lflf)
            trns = header.transparency
            col = "n/a"
            if trns is not None and palette:
                col = tuple(palette[trns * 3: trns * 3 + 3])
            objs = []
            for obj_path, name, im, ox, oy in read_objects(header, room, 8):
                arr = np.array(im)
                if trns is not None:
                    share = float((arr == trns).mean())
                else:
                    share = -1.0
                border = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
                u, c = np.unique(border, return_counts=True)
                objs.append((name, share, int(u[np.argmax(c)])))
                if len(objs) >= 4:
                    break
            found.append((room_id, trns, col, objs, palette))
            print("Raum %-3d TRNS=%-4s Farbe=%s" % (room_id, trns, col))
            for name, share, bidx in objs:
                print("    %-34s Anteil TRNS-Index: %5.1f%%   Randindex: %d" % (name, 100 * share, bidx))
    if not found:
        print("keine der Raeume gefunden:", wanted)


if __name__ == "__main__":
    main()
