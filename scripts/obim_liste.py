#!/usr/bin/env python3
"""Listet ALLE OBIM eines Raums mit Name und Kind-Tags (IMHD, IMAG, WRAP ...).

Damit laesst sich sehen, welche Objekte ein Bild haben und welche nur einen Kopf.

Aufruf: python3 scripts/obim_liste.py 86
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import paths

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.room.pproom import get_rooms, read_imhd_v8
from nutcracker.sputm.preset import sputm


def main():
    raum = int(sys.argv[1])
    game = open_game_resource(os.path.join(paths.GAME_DIR, 'COMI.LA0'))
    for t in game.read_resources():
        for lflf in get_rooms(t.children()):
            if (lflf.attribs.get('gid', 0) or 0) != raum:
                continue
            room_el = sputm.find('ROOM', lflf) or sputm.find('RMDA', lflf)
            for i, obim in enumerate(sputm.findall('OBIM', room_el)):
                imhd = sputm.find('IMHD', obim)
                name = '?'
                try:
                    name, h, w, x, y = read_imhd_v8(imhd.data)
                except Exception as e:
                    name = 'Fehler: %s' % e
                tags = sorted({c.tag for c in obim.children()})
                print('%2d  %-34s %-22s size=%s' % (i, name, ','.join(tags), obim.attribs.get('size')))
            return 0
    print('Raum nicht gefunden')
    return 1


if __name__ == '__main__':
    sys.exit(main())
