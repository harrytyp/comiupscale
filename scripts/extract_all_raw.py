#!/usr/bin/env python3
"""
Extract ALL raw assets from COMI game files for GPU upscale workspace.

Extracts: backgrounds, objects, object_layers, fonts, costumes
All saved as raw 8-bit palette PNGs (not upscaled).

Usage:
  python extract_all_raw.py /path/to/COMI/ [--outdir ./raw_extracted]
"""

import sys, os, glob
from pathlib import Path

# NUTcracker path
NUT_SRC = Path(__file__).resolve().parent.parent.parent / 'nutcracker_src'
sys.path.insert(0, str(NUT_SRC))

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.room.pproom import get_rooms, read_room_settings, read_room, read_objects
from nutcracker.sputm import preset
from nutcracker.smush import anim
from nutcracker.smush.decode import decode_nut
from nutcracker.graphics.frame import resize_pil_image
from nutcracker.graphics.image import ImagePosition
import numpy as np

sputm = preset.sputm


def extract_all(game_path, outdir):
    game_path = Path(game_path)
    outdir = Path(outdir)
    game_file = game_path / 'COMI.LA0'
    resource_dir = game_path / 'RESOURCE'

    if not game_file.exists():
        print(f"ERROR: {game_file} not found")
        sys.exit(1)

    # Room name mapping (from RESOURCE/ROOMNAM.TXT or similar)
    # NUTcracker has a built-in mapping for V8 games
    from nutcracker.sputm import preset
    rnam = {}

    gameres = open_game_resource(str(game_file))
    root = gameres.read_resources()
    root_list = list(root)

    # --- Step 1: Backgrounds, Objects, Layers ---
    print("=== Backgrounds, Objects, Object Layers ===")
    bg_dir = outdir / 'backgrounds'
    bg_dir.mkdir(parents=True, exist_ok=True)
    obj_dir = outdir / 'objects'
    obj_dir.mkdir(parents=True, exist_ok=True)
    lay_dir = outdir / 'objects_layers'
    lay_dir.mkdir(parents=True, exist_ok=True)

    from nutcracker.graphics.frame import resize_pil_image
    from nutcracker.graphics.image import ImagePosition

    for t in root_list:
        for lflf in get_rooms(t.children()):
            header, palette, room, rmim = read_room_settings(lflf)
            room_id = lflf.attribs.get('gid', 0)
            room_bg_image = None

            # Backgrounds
            for bg_path, room_bg_img, _ in read_room(header, rmim):
                bg_fn = f'{room_id:04d}_bg.png'
                room_bg_img.putpalette(palette)
                room_bg_img.save(str(bg_dir / bg_fn))
                room_bg_image = room_bg_img

            # Objects + Layers
            for obj_path, name, im, obj_x, obj_y in read_objects(header, room, 8):
                fn = f'{room_id:04d}_{name}.png'
                im.putpalette(palette)
                im.save(str(obj_dir / fn))

                if room_bg_image:
                    try:
                        layer = resize_pil_image(
                            *room_bg_image.size, 39, im,
                            ImagePosition(x1=obj_x, y1=obj_y),
                        )
                        layer.putpalette(palette)
                        layer.save(str(lay_dir / fn))
                    except:
                        pass

            print(f"  Room {room_id}: bg + objects saved")

    bg_count = len(list(bg_dir.glob('*.png')))
    obj_count = len(list(obj_dir.glob('*.png')))
    lay_count = len(list(lay_dir.glob('*.png')))
    print(f"  Backgrounds: {bg_count} | Objects: {obj_count} | Layers: {lay_count}")

    # --- Step 2: Fonts ---
    print("\n=== Fonts ===")
    font_dir = outdir / 'fonts'
    font_dir.mkdir(parents=True, exist_ok=True)

    for nut_path in sorted(resource_dir.glob('FONT*.NUT')):
        name = nut_path.stem
        print(f"  Decoding {nut_path.name} ...", end=' ', flush=True)
        try:
            root_smush = anim.from_path(str(nut_path))
            decode_nut(root_smush, str(font_dir / name))
            print("chars.png" if (font_dir / name / 'chars.png').exists() else "done")
        except Exception as e:
            print(f"error: {e}")

    font_count = len(list(font_dir.rglob('*.png')))
    print(f"  Font PNGs: {font_count}")

    # --- Step 3: Costumes ---
    print("\n=== Costumes ===")
    cost_dir = outdir / 'costumes'
    cost_dir.mkdir(parents=True, exist_ok=True)

    from nutcracker.sputm.costume.akos import (
        akos_header_from_bytes, akof_from_bytes,
        read_akos_resource,
    )

    for t in root_list:
        for lflf in get_rooms(t.children()):
            _, palette, _, _ = read_room_settings(lflf)
            for akos in sputm.findall('AKOS', lflf):
                try:
                    for idx, ((xoff, yoff), im) in enumerate(
                        read_akos_resource(akos, palette)
                    ):
                        lflf_name = os.path.basename(lflf.attribs['path'])
                        akos_name = os.path.basename(akos.attribs['path'])
                        imname = f'{lflf_name}_{akos_name}_aframe_{idx}.png'
                        im.save(str(cost_dir / imname))
                except Exception as e:
                    print(f"  Error: {e}")

    cost_count = len(list(cost_dir.glob('*.png')))
    print(f"  Costume frames: {cost_count}")

    # --- Summary ---
    print("\n=== Summary ===")
    total = 0
    for subdir in ['backgrounds', 'objects', 'objects_layers', 'fonts', 'costumes']:
        d = outdir / subdir
        if d.exists():
            count = len(list(d.rglob('*.png')))
            size = sum(f.stat().st_size for f in d.rglob('*.png')) / 1024 / 1024
            total += count
            print(f"  {subdir}: {count} files, {size:.1f} MB")
    print(f"  TOTAL: {total} files")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract all raw COMI assets')
    parser.add_argument('game_path', help='Path to COMI game directory')
    parser.add_argument('-o', '--outdir', default='./raw_extracted',
                        help='Output directory')
    args = parser.parse_args()
    extract_all(args.game_path, args.outdir)


if __name__ == '__main__':
    main()
