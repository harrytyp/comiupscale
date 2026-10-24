#!/usr/bin/env python3
"""Zeigt, welche Bildebenen ein Raum hat: RMIM (Hintergrund), SMAP (Vordergrund), OBIM.

SMAP ist die Vordergrund-Ebene eines COMI-Raums: Pixel, die UEBER den Figuren liegen
(Stuhllehne, Theke, Pflanze im Vordergrund). Sie wird getrennt vom Hintergrund gezeichnet.

Aufruf: python3 scripts/raum_ebenen.py 86
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
    raum = int(sys.argv[1])
    game = open_game_resource(os.path.join(paths.GAME_DIR, 'COMI.LA0'))
    for t in game.read_resources():
        for lflf in get_rooms(t.children()):
            if (lflf.attribs.get('gid', 0) or 0) != raum:
                continue
            room_el = sputm.find('ROOM', lflf) or sputm.find('RMDA', lflf)
            for tag in ('RMIM', 'SMAP', 'OBIM'):
                treffer = list(sputm.findall(tag, room_el))
                print('%-5s %2d' % (tag, len(treffer)))
                for el in treffer[:3]:
                    groesse = el.attribs.get('size')
                    print('      size=%s  tags=%s' % (groesse, sorted({c.tag for c in el.children()})))
            return 0
    print('Raum nicht gefunden')
    return 1


if __name__ == '__main__':
    sys.exit(main())
