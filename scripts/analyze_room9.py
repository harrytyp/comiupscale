#!/usr/bin/env python3
"""Analyze Room 9 objects and their extraction status."""
import sys
from pathlib import Path
# Add tools/nutcracker to path (custom fork with AKOS decoder)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from nutcracker.sputm.tree import open_game_resource
import logging
logging.disable(logging.CRITICAL)  # suppress spam

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.preset import sputm
from nutcracker.sputm.index import read_dobj_v8
from nutcracker.kernel2.element import Element

gameres = open_game_resource('/opt/data/local/comi-hd-final/COMI.LA0')
root = gameres.read_resources()

# Find DOBJ
def find_dobj(elements):
    if isinstance(elements, (list, tuple)):
        for e in elements:
            r = find_dobj(e)
            if r: return r
        return None
    if isinstance(elements, Element):
        if elements.tag == 'DOBJ':
            return elements.data
        for c in elements.children():
            r = find_dobj(c)
            if r: return r
    return None

for t in root:
    dobj_data = find_dobj(t)
    break

if dobj_data:
    entries = list(read_dobj_v8(dobj_data))
    print('=== DOBJ: Room 9 objects ===')
    for name, (obj_id, state, room, obj_class) in entries:
        if room == 9:
            print(f'  obj_nr={obj_id:4d}  state={state}  class={obj_class}  name={name}')
    
    print()
    print('=== DOBJ: objects named cannon/larry ===')
    for name, (obj_id, state, room, obj_class) in entries:
        nl = name.lower()
        if 'cannon' in nl or 'larry' in nl:
            print(f'  obj_nr={obj_id:4d}  room={room}  state={state}  class={obj_class}  name={name}')

print()
print('=== Room 9 OBIM details ===')
for t in root:
    for lflf in t.children():
        if lflf.tag != 'LFLF':
            continue
        if lflf.attribs.get('gid', -1) != 9:
            continue
        
        room = sputm.find('ROOM', lflf)
        obims = list(sputm.findall('OBIM', room))
        print(f'Room 9: {len(obims)} OBIMs')
        
        for obim in obims:
            imhd_data = sputm.find('IMHD', obim).data
            data = bytes(imhd_data)
            name = data[:40].split(b'\0')[0].decode().strip()
            version = int.from_bytes(data[40:44], 'little')
            image_count = int.from_bytes(data[44:48], 'little')
            obj_x = int.from_bytes(data[48:52], 'little')
            obj_y = int.from_bytes(data[52:56], 'little')
            obj_w = int.from_bytes(data[56:60], 'little')
            obj_h = int.from_bytes(data[60:64], 'little')
            actor_dir = int.from_bytes(data[64:68], 'little')
            flags = int.from_bytes(data[68:72], 'little')
            
            imag_count = len(list(sputm.findall('IMAG', obim)))
            gid = obim.attribs.get('gid', '-')
            
            print(f'  gid={str(gid):>5s}  img_count={image_count}  IMAGs={imag_count}  '
                  f'name={name:35s}  pos=({obj_x:4d},{obj_y:4d})  size=({obj_w}x{obj_h})  '
                  f'flags={flags:#010x}')
