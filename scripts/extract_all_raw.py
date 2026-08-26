#!/usr/bin/env python3
"""
Extract ALL raw assets from COMI game files for GPU upscale workspace.

Extracts: backgrounds, objects, object_layers, fonts, costumes
All saved as raw 8-bit palette PNGs (not upscaled).

Usage:
  python extract_all_raw.py /path/to/COMI/ [--outdir ./raw_extracted]
"""

import sys, os, glob, logging
from pathlib import Path

# Suppress NUTcracker debug noise
logging.disable(logging.CRITICAL)

# NUTcracker path — use repo's tools/nutcracker/
NUT_SRC = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(NUT_SRC))

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.room.pproom import get_rooms, read_room_settings, read_room, read_objects
from nutcracker.sputm import preset
from nutcracker.smush import anim
from nutcracker.smush.decode import decode_nut
from nutcracker.graphics.frame import resize_pil_image
from nutcracker.graphics.image import ImagePosition
import numpy as np
from PIL import Image

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
            if room_id is None:
                room_id = 0
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

    # Extract font glyphs directly from the NUT FRME/FOBJ frames into a
    # clean RGBA sheet (glyph on transparent background, 16x16 grid).
    # NOTE: decode_nut's create_char_grid is BROKEN for FONT0 (glyphs
    # become black placeholder boxes). This direct extraction reads the
    # actual glyph bitmaps from the frames, so all fonts (0-4) get their
    # real glyphs.
    from nutcracker.smush.decode import generate_frames, DECODE_FRAME_IMAGE
    from nutcracker.graphics import image as nut_image
    import numpy as np

    GRID = 16
    CELL_W = 56   # base px, matches the waifu/HD convention (56x56 base)
    CELL_H = 56

    for nut_path in sorted(resource_dir.glob('FONT*.NUT')):
        name = nut_path.stem
        print(f"  Decoding {nut_path.name} ...", end=' ', flush=True)
        try:
            root_smush = anim.from_path(str(nut_path))
            header, frames = anim.parse(root_smush)
            chars = [ctx.screen for ctx in generate_frames(header, frames, DECODE_FRAME_IMAGE)]
            sheet = Image.new('RGBA', (GRID * CELL_W, GRID * CELL_H), (0, 0, 0, 0))
            for idx, (loc, im) in enumerate(chars):
                if idx >= GRID * GRID:
                    continue
                img = nut_image.convert_to_pil_image(im)
                # NUT glyphs are palette images: Index 0 = OUTLINE (black
                # contour), Index 1 = FILL (replaced with text color by the
                # 8-bit renderer), Index 39 = transparent. Encode this so
                # the renderer can tint the fill and keep the outline:
                #   outline -> black, fill -> WHITE (tint target), rest -> transparent.
                if img.mode == 'P':
                    pa = np.array(img)
                    rgba = img.convert('RGBA')
                    r_arr, g_arr, b_arr, a_arr = [np.array(c) for c in rgba.split()]
                    # Build mask: outline = index 0, fill = index 1
                    is_outline = (pa == 0)
                    is_fill = (pa == 1)
                    # Fill pixels -> white, outline pixels -> black
                    r_out = np.where(is_fill, 255, np.where(is_outline, 0, r_arr))
                    g_out = np.where(is_fill, 255, np.where(is_outline, 0, g_arr))
                    b_out = np.where(is_fill, 255, np.where(is_outline, 0, b_arr))
                    a_out = np.where(pa == 39, 0, 255).astype(np.uint8)
                    img = Image.merge('RGBA', (
                        Image.fromarray(r_out.astype(np.uint8), 'L'),
                        Image.fromarray(g_out.astype(np.uint8), 'L'),
                        Image.fromarray(b_out.astype(np.uint8), 'L'),
                        Image.fromarray(a_out.astype(np.uint8), 'L'),
                    ))
                else:
                    img = img.convert('RGBA')
                # Keep the FULL frame size (loc.x2-loc.x1, loc.y2-loc.y1)
                # — do NOT crop the transparent top padding away. The
                # 8-bit renderer draws the glyph at the frame's top edge
                # (y) and the internal transparent rows above the ink
                # position it on the text baseline. If we crop the bbox,
                # the glyph loses that padding and gets top-aligned.
                # Paste the frame at the cell origin (no padding) so the
                # renderer can draw cell-top -> ink-bottom with no offset.
                fw = max(1, loc.x2 - loc.x1)
                fh = max(1, loc.y2 - loc.y1)
                if img.size != (fw, fh):
                    # The decoded image may be smaller than the frame;
                    # paste it at the frame's offset (xoff/yoff).
                    pad = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
                    pad.paste(img, (loc.x1, loc.y1), img)
                    img = pad
                # Paste at cell origin (no padding) — the frame's own top
                # padding (transparent rows above the ink) is preserved.
                row = idx // GRID
                col = idx % GRID
                cell_x = col * CELL_W
                cell_y = row * CELL_H
                sheet.paste(img, (cell_x, cell_y), img)
            out_sub = font_dir / name
            out_sub.mkdir(parents=True, exist_ok=True)
            sheet.save(str(out_sub / 'chars.png'))
            print("chars.png")
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
