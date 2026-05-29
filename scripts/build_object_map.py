#!/usr/bin/env python3
"""
Build a JSON mapping from obj_nr to extracted object PNG filenames.

The NUTcracker extracts objects as: {room}_{name}_{state}.png
The ScummVM engine uses obj_nr (numeric ID).
The DOBJ resource in COMI.LA0 maps obj_name ↔ obj_nr.

This script reads DOBJ via NUTcracker, walks extracted PNGs, and outputs:
  config/object_map.json  — mapping for runtime engine use

Usage:
  cd <project-root>
  python scripts/build_object_map.py
"""

import json
import os
import sys

# Use paths.py for all directory references
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import paths

from nutcracker.sputm.resource import load_resource
from nutcracker.sputm.index import read_dobj_v8
from nutcracker.kernel2.element import Element


def find_dobj_in_elements(elements):
    """Recursively search Element tree for DOBJ."""
    if isinstance(elements, (list, tuple)):
        for elem in elements:
            result = find_dobj_in_elements(elem)
            if result is not None:
                return result
        return None
    if isinstance(elements, Element):
        if elements.tag == 'DOBJ':
            return elements.data
        for child in elements.children():
            result = find_dobj_in_elements(child)
            if result is not None:
                return result
    return None


def build_maps():
    sys.path.insert(0, paths.NUTCRACKER_SRC)
    game_file = os.path.join(paths.GAME_DIR, 'COMI.LA0')
    extracted_base = os.path.join(paths.ASSETS_EXTRACTED, 'IMAGES')
    hd_dir = paths.CONFIG_DIR

    if not os.path.exists(game_file):
        print(f"ERROR: Game file not found: {game_file}")
        sys.exit(1)

    # Load game resource (parses the index into elements)
    print(f"Loading game: {game_file}")
    game = load_resource(game_file)
    print(f"Game: version={game.version}")

    # Find DOBJ element in the index tree
    print("Searching for DOBJ in index...")
    dobj_data = find_dobj_in_elements(game.index)
    if dobj_data is None:
        print("ERROR: DOBJ not found in game index")
        sys.exit(1)
    print(f"DOBJ found: {len(dobj_data)} bytes")

    # Parse DOBJ entries via NUTcracker's reader
    dobj_entries = list(read_dobj_v8(dobj_data))
    print(f"DOBJ entries: {len(dobj_entries)}")

    # Build lookup: name → (obj_id, state, room, class)
    name_to_id = {}
    id_to_name = {}
    for name, (obj_id, state, room, obj_class) in dobj_entries:
        name_to_id[name] = obj_id
        id_to_name[obj_id] = name

    # Walk extracted PNGs and index them
    objects_dir = os.path.join(extracted_base, 'objects')
    layers_dir = os.path.join(extracted_base, 'objects_layers')

    extracted = {}  # (room, name) → {states, state_files, layer_files}
    missed_names = set()

    for base_dir, is_layer in [(objects_dir, False), (layers_dir, True)]:
        if not os.path.isdir(base_dir):
            print(f"  WARNING: {base_dir} not found")
            continue
        for fname in sorted(os.listdir(base_dir)):
            if not fname.endswith('.png'):
                continue
            base = fname[:-4]
            # Pattern: {room}_{name}_{state}.png
            # Split on LAST underscore for state
            parts = base.rsplit('_', 1)
            if len(parts) != 2:
                continue
            name_part, state_str = parts
            try:
                state = int(state_str)
            except ValueError:
                continue
            # Split on FIRST underscore for room
            us = name_part.find('_')
            if us < 0:
                continue
            room_str = name_part[:us]
            name = name_part[us + 1:]
            try:
                room_id = int(room_str)
            except ValueError:
                continue

            key = (room_id, name)
            if key not in extracted:
                extracted[key] = {
                    'room': room_id,
                    'name': name,
                    'states': set(),
                    'state_files': {},
                    'layer_files': {},
                }
            extracted[key]['states'].add(state)
            files_dict = 'layer_files' if is_layer else 'state_files'
            extracted[key][files_dict].setdefault(state, []).append(fname)

    print(f"Extracted objects: {len(extracted)} (room, name) pairs")

    # Match extracted names to DOBJ, build obj_nr → files mapping
    obj_map = {}  # obj_nr → {name, rooms}
    missed_in_dobj = 0

    for (room_id, name), info in extracted.items():
        obj_id = name_to_id.get(name)
        if obj_id is None:
            missed_in_dobj += 1
            missed_names.add(name)
            continue

        if obj_id not in obj_map:
            obj_map[obj_id] = {
                'name': name,
                'rooms': {},
            }
        room_key = str(room_id)
        obj_map[obj_id]['rooms'][room_key] = {
            'states': sorted(info['states']),
            'state_files': {str(s): v for s, v in info['state_files'].items()},
            'layer_files': {str(s): v for s, v in info['layer_files'].items()},
        }

    if missed_in_dobj:
        print(f"  Skipped {missed_in_dobj} entries not in DOBJ ({(len(missed_names))} unique names)")

    # Write JSON mapping for engine
    os.makedirs(hd_dir, exist_ok=True)
    map_path = os.path.join(hd_dir, 'object_map.json')
    # Serialize obj_id as string key (JSON requires string keys)
    serializable = {str(k): v for k, v in obj_map.items()}
    with open(map_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\n✓ Engine mapping: {map_path} ({os.path.getsize(map_path)} bytes)")
    print(f"  {len(obj_map)} objects mapped ({len(dobj_entries)} in DOBJ)")

    # Print examples
    samples = sorted(obj_map.keys())[:8]
    print("\n  Examples:")
    for obj_id in samples:
        info = obj_map[obj_id]
        example_room = next(iter(info['rooms']), '?')
        room_info = info['rooms'].get(example_room, {})
        states = room_info.get('states', [])[:3]
        layers = bool(room_info.get('layer_files'))
        print(f"    obj={obj_id:4d}  name={info['name']:35s}  room={example_room:>3s}  "
              f"states={states}  layers={'Y' if layers else 'n'}")

    print("\nDone!")


if __name__ == '__main__':
    build_maps()
