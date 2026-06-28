#!/usr/bin/env python3
"""
COMI HD Costume Extractor — Fixed Alpha Version

Extracts all AKOS costume frames from COMI with correct transparency
AND correct palette mapping.

FIXES APPLIED (2026-06-28):
1. build_palette(codec) — For codec 5 (BOMP) / 16 (SMAP), pixel indices
   are direct indices into the 256-color room palette (APAL). The function
   now returns raw room_palette[:768] instead of construct_palette(akpl, rgbs).
2. decode_frame() — Removed order='F' from np.reshape(). The BOMP/SMAP/RLE
   decoders return pixel data in row-major (not column-major) order, matching
   NUTcracker's own convert_to_pil_image() implementation.

Alpha handling: fill pixels (palette index 255) are set to alpha=0.

Usage:
    python extract_costumes_fixed.py /path/to/COMI.LA0 [output_dir]
"""

import sys
import os
import io
from pathlib import Path

import numpy as np
from PIL import Image

# Add nutcracker to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'nutcracker_src'))

from nutcracker.sputm.tree import open_game_resource
from nutcracker.sputm.costume.akos import (
    akos_header_from_bytes, akof_from_bytes, construct_palette
)
from nutcracker.sputm.room.pproom import get_rooms, read_room_settings
from nutcracker.sputm import preset
from nutcracker.codex import bpp_cost

sputm = preset.sputm


def get_room_palette(lflf_node):
    """Extract the 256-color room palette from ROOM/PALS/WRAP/APAL."""
    room = sputm.find('ROOM', lflf_node)
    if not room:
        return None
    pals = sputm.find('PALS', room)
    if not pals:
        return None
    wrap = sputm.find('WRAP', pals)
    if not wrap:
        return None
    apals = list(sputm.findall('APAL', wrap))
    if not apals:
        return None
    return list(apals[0].data)  # 768 bytes = 256 RGB colors


def build_palette(akpl_data, rgbs_data, room_palette, codec=5):
    """
    Build the correct 256-color palette for a costume.

    Per NUTcracker's read_akos_resource():
    - codec 5 (BOMP) / codec 16 (SMAP): pixel indices are DIRECT room palette indices
    - codec 1 (RLE) with RGBS: AKPL maps into RGBS via construct_palette()
    - codec 1 without RGBS but max_akpl > 15: AKPL maps into room palette
    """
    max_akpl = max(akpl_data) if akpl_data else 0

    if codec in (5, 16):
        # BOMP/SMAP: pixel values are direct indices into 256-color room palette
        if room_palette:
            return bytearray(room_palette[:768]), 'room_palette_raw'
        return bytearray(768), 'empty'
    elif codec == 1 and rgbs_data is not None and max_akpl <= 15:
        # Sparse AKPL: indices are into RGBS color table
        return construct_palette(akpl_data, rgbs_data), 'rgbs'
    elif max_akpl > 15 and room_palette is not None:
        # Dense AKPL (codec 1): indices are room palette indices
        palette = bytearray(768)
        for i, idx in enumerate(akpl_data):
            palette[i*3] = room_palette[idx*3]
            palette[i*3+1] = room_palette[idx*3+1]
            palette[i*3+2] = room_palette[idx*3+2]
        return palette, 'room'
    elif rgbs_data is not None:
        return construct_palette(akpl_data, rgbs_data), 'rgbs'
    else:
        if room_palette:
            return bytearray(room_palette[:768]), 'room_direct'
        return bytearray(768), 'empty'


def decode_frame(akhd, ci_data, cd_data, palette, num_colors):
    """Decode a single costume frame and return (PIL Image, raw_index_array)."""
    width = int.from_bytes(ci_data[0:2], signed=False, byteorder='little')
    height = int.from_bytes(ci_data[2:4], signed=False, byteorder='little')

    stream = io.BytesIO(cd_data)

    if akhd.codec == 1:
        arr = bpp_cost.decode1(width, height, num_colors, stream, strict=False)
    elif akhd.codec == 5:
        from nutcracker.codex import bomp
        out = bomp.decode_image(cd_data, width, height, fill_value=b'\xff')
        arr = np.frombuffer(out, dtype=np.uint8).reshape((height, width))
    elif akhd.codec == 32:
        from nutcracker.codex import rle
        out = rle.decode_lined_rle(cd_data, width, height, verify=False)
        arr = np.frombuffer(out, dtype=np.uint8).reshape((height, width))
    elif akhd.codec == 16:
        from nutcracker.codex import smap
        bpp = stream.read(1)[0]
        out = smap.decode_run_majmin(stream, width * height, bpp)
        arr = np.frombuffer(out, dtype=np.uint8).reshape((height, width))
    else:
        return None, 0, 0, None

    im = Image.fromarray(arr, mode='P')
    im.putpalette(list(palette))
    return im, width, height, arr  # arr = raw palette indices


def extract_all_costumes(game_path, output_dir):
    """Extract all costume frames from the game with correct alpha."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gameres = open_game_resource(game_path)
    root = gameres.read_resources()

    stats = {
        'rooms': 0,
        'costumes': 0,
        'frames': 0,
        'fill_fixed': 0,
        'palette_modes': {'room': 0, 'rgbs': 0, 'room_direct': 0, 'empty': 0, 'room_palette_raw': 0}
    }

    for t in root:
        for lflf in get_rooms(t.children()):
            room_id = lflf.attribs.get('path', 'unknown')
            room_palette = get_room_palette(lflf)

            if room_palette:
                stats['rooms'] += 1

            # Find all AKOS costumes in this room
            for akos in sputm.findall('AKOS', lflf):
                akos_path = akos.attribs.get('path', 'unknown')
                akos_name = os.path.basename(akos_path)

                akhd = akos_header_from_bytes(sputm.find('AKHD', akos).data)
                akpl = sputm.find('AKPL', akos)
                rgbs = sputm.find('RGBS', akos)

                if not akpl:
                    continue

                # Build palette (pass codec for correct handling)
                palette, mode = build_palette(
                    akpl.data,
                    rgbs.data if rgbs else None,
                    room_palette,
                    akhd.codec
                )
                stats['palette_modes'][mode] += 1

                # Get frame offsets
                akof_data = sputm.find('AKOF', akos)
                if not akof_data:
                    continue
                akof_list = list(akof_from_bytes(akof_data.data))
                akci = sputm.find('AKCI', akos)
                akcd = sputm.find('AKCD', akos)

                if not akci or not akcd:
                    continue

                stats['costumes'] += 1

                # Parse LFLF and AKOS IDs for HD naming convention
                parts = room_id.split('/')
                lflf_owner = int(parts[-1].split('_')[-1]) if len(parts) > 1 else 0
                akos_id = int(akos_name.split('_')[-1]) if '_' in akos_name else 0

                # Decode all frames
                for frame_idx in range(len(akof_list)):
                    cd_start, ci_start = akof_list[frame_idx]
                    cd_end = akof_list[frame_idx + 1][0] if frame_idx + 1 < len(akof_list) else len(akcd.data)

                    ci = akci.data[ci_start:ci_start + 8]
                    cd = akcd.data[cd_start:cd_end]

                    im, w, h, raw_indices = decode_frame(akhd, ci, cd, palette, len(akpl.data))

                    if im is None:
                        continue
                    # Check if frame has any non-fill content
                    if raw_indices is not None:
                        non_fill = np.sum(raw_indices != 255)
                    else:
                        arr_rgb = np.array(im.convert('RGB'))
                        non_fill = np.sum(np.any(arr_rgb > 10, axis=2))

                    if non_fill > 0:
                        # Save as PNG with alpha
                        # Strategy: combine explicit fill detection (raw_indices == 255
                        # for BOMP codec) with dominant-index heuristic for other codecs.
                        # Also mark palette index 0 transparent (ScummVM convention).
                        rgba = im.convert('RGBA')
                        arr_rgba = np.array(rgba)

                        # Method 1: Explicit BOMP fill value (index 255)
                        if raw_indices is not None:
                            fill_mask = (raw_indices == 255)
                            arr_rgba[fill_mask, 3] = 0
                            stats['fill_fixed'] += int(np.sum(fill_mask))

                        # Method 2: Dominant-index heuristic for other codecs
                        arr_p = np.array(im)
                        unique, counts = np.unique(arr_p, return_counts=True)
                        total_px = arr_p.size
                        for idx_val, cnt in zip(unique, counts):
                            if cnt / total_px > 0.4:
                                arr_rgba[arr_p == idx_val, 3] = 0

                        # Method 3: Palette index 0 = transparent (ScummVM convention)
                        arr_rgba[arr_p == 0, 3] = 0

                        # Save with HD naming convention
                        hd_frame_path = output_dir / f'LFLF_{lflf_owner:04d}_AKOS_{akos_id:04d}_aframe_{frame_idx}.png'
                        Image.fromarray(arr_rgba).save(hd_frame_path)

                        stats['frames'] += 1

                if stats['costumes'] % 50 == 0:
                    print(f'  Processed {stats["costumes"]} costumes, {stats["frames"]} frames...')

    print(f'\n=== Extraction Complete ===')
    print(f'Rooms: {stats["rooms"]}')
    print(f'Costumes: {stats["costumes"]}')
    print(f'Frames: {stats["frames"]}')
    print(f'Fill pixels fixed: {stats["fill_fixed"]}')
    print(f'Palette modes: {stats["palette_modes"]}')
    print(f'Output: {output_dir}')

    return stats


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <COMI.LA0> [output_dir]')
        sys.exit(1)

    game_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'hd_costumes_fixed'

    extract_all_costumes(game_path, output_dir)
