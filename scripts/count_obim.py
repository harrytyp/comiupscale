#!/usr/bin/env python3
"""Zaehlt je Raum die OBIM-Elemente (Objektbilder) in den Spieldaten.

Beantwortet die Frage, warum die Extraktion fuer manche Raeume keine Objekte liefert:
gibt es dort ueberhaupt OBIM-Elemente?

Aufruf: python3 scripts/count_obim.py [raum ...]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import paths

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.room.pproom import get_rooms
from nutcracker.sputm.preset import sputm


def main():
    wollen = {int(x) for x in sys.argv[1:]} if len(sys.argv) > 1 else None
    game_file = os.path.join(paths.GAME_DIR, 'COMI.LA0')
    gameres = open_game_resource(game_file)
    root = gameres.read_resources()
    gesamt = 0
    for t in root:
        for lflf in get_rooms(t.children()):
            room_id = lflf.attribs.get('gid', 0) or 0
            # OBIM haengen im ROOM-Element, nicht direkt im LFLF.
            room_el = sputm.find('ROOM', lflf) or sputm.find('RMDA', lflf)
            obim = list(sputm.findall('OBIM', room_el)) if room_el else []
            rmim = list(sputm.findall('RMIM', room_el)) if room_el else []
            gesamt += len(obim)
            if wollen is None or room_id in wollen:
                print("Raum %-4d OBIM=%3d  RMIM=%3d" % (room_id, len(obim), len(rmim)))
    if wollen is None:
        print("OBIM gesamt: %d" % gesamt)


if __name__ == '__main__':
    sys.exit(main())
