#!/usr/bin/env python3
"""Listet die obersten Ressourcen-Tags der Spieldatei (z. B. LECF, FLOB, ...).

Damit ist belegbar, ob es eigene Objektressourcen gibt, die die Extraktion nicht liest.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import paths

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.preset import sputm


def main():
    game = open_game_resource(os.path.join(paths.GAME_DIR, 'COMI.LA0'))
    zaehler = collections.Counter()
    for t in game.read_resources():
        for el in t.children():
            zaehler[el.tag] += 1
    for tag, n in zaehler.most_common(12):
        print('%-6s %5d' % (tag, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
