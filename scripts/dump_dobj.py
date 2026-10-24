#!/usr/bin/env python3
"""Gibt das Objektverzeichnis (DOBJ) aus: Nummer, Name, Raum, Zustand.

Damit laesst sich beantworten, ob ein Objekt, das im Spiel gezeichnet wird, ueberhaupt
ein Bild in den Spieldaten hat — die Frage, die ueber "fehlendes Asset" oder
"zur Laufzeit zusammengesetzt" entscheidet.

Aufruf:
  python3 scripts/dump_dobj.py            # alles
  python3 scripts/dump_dobj.py 15         # nur Raum 15
  python3 scripts/dump_dobj.py --obj 398  # ein Objekt
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import paths

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))

from nutcracker.sputm.resource import load_resource
from nutcracker.sputm.index import read_dobj_v8
# Dieselbe Suche wie im Tabellenbauer — die Struktur dort ist erprobt.
from build_object_map import find_dobj_in_elements


def find_dobj(elements):
    for el in elements:
        try:
            name = el.tag if isinstance(el.tag, str) else el.attribs.get('name', '')
        except AttributeError:
            name = ''
        if str(name).upper().endswith('DOBJ'):
            data = el.data() if callable(getattr(el, 'data', None)) else None
            if data:
                return data
        kids = list(el.children()) if hasattr(el, 'children') else []
        if kids:
            found = find_dobj(kids)
            if found:
                return found
    return None


def main():
    arg_room = None
    arg_obj = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '--obj':
            arg_obj = int(sys.argv[2])
        else:
            arg_room = int(sys.argv[1])

    game_file = os.path.join(paths.GAME_DIR, 'COMI.LA0')
    game = load_resource(game_file)
    data = find_dobj_in_elements(game.index)
    if data is None:
        print('DOBJ nicht gefunden')
        return 1
    eintraege = list(read_dobj_v8(data))
    print('# DOBJ-Eintraege gesamt: %d' % len(eintraege))
    for name, (obj_id, state, room, obj_class) in eintraege:
        if arg_obj is not None and obj_id != arg_obj:
            continue
        if arg_room is not None and room != arg_room:
            continue
        print('%5d  %-40s room=%-4d state=%-3d class=%d' % (obj_id, name, room, state, obj_class))
    return 0


if __name__ == '__main__':
    sys.exit(main())
