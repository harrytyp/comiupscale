#!/usr/bin/env python3
"""Zeigt den Aufbau der OBIM-Elemente eines Raums: welche Kind-Tags kommen vor?

Damit laesst sich sagen, in welcher Form die Objektbilder dort gespeichert sind —
die Grundlage fuer den Reader.
"""
import collections
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
            obims = list(sputm.findall('OBIM', room_el))
            print('Raum %d: %d OBIM' % (raum, len(obims)))
            for i, obim in enumerate(obims[:5]):
                tags = collections.Counter(ch.tag for ch in obim.children())
                print('  OBIM %d: %s' % (i, dict(tags)))
            return 0
    print('Raum nicht gefunden')
    return 1


if __name__ == '__main__':
    sys.exit(main())
