#!/usr/bin/env python3
"""
Alpha generator v6: pixel-precise transparency mask from original 8-bit object.
Multiprocess version — processes objects and layers in parallel workers.

v6.1: Added broad green-background cleanup as post-processing step.
      The original single-color tolerance (diff < 50) missed pixels where
      AI upscaling introduced color variation in the green grass background
      (RGB~110,199,24). The broad approach detects ALL greenish pixels using
      two heuristics:
        1. Greenish detection: G > 100, G > R*1.1, B < 120
        2. Near-background detection: |color - bg| < 80
      This catches all shades of green background without affecting actual
      object content (metal, wood, etc. are never greenish).

Pipeline position: Run AFTER upscale_esrgan.py / batch_upscale_costumes.py.
Reads original 8-bit palette PNGs to build a per-pixel mask, resizes to HD,
then applies broad green-background cleanup.

Usage:
    python scripts/add_object_alpha_v6.py [--workers 4]
"""

import os
import sys
import argparse
from functools import partial
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image
import numpy as np
from tqdm import tqdm

SRC = 'assets/extracted/COMI/IMAGES/objects'
HD = 'game/hd/objects'
SRC_L = 'assets/extracted/COMI/IMAGES/objects_layers'
HD_L = 'game/hd/objects_layers'


def has_green_border(arr, threshold=0.1):
    """Check if image has a green background based on border pixel analysis.

    Samples all 4 edges. If >threshold of border pixels are greenish
    (G > 100, G > R*1.2), the image has a green background.
    """
    h, w = arr.shape[:2]
    border_total = 0
    border_green = 0
    for x in range(w):
        for row in [0, h - 1]:
            r, g = int(arr[row, x, 0]), int(arr[row, x, 1])
            if g > 100 and g > r * 1.2:
                border_green += 1
            border_total += 1
    for y in range(h):
        for col in [0, w - 1]:
            r, g = int(arr[y, col, 0]), int(arr[y, col, 1])
            if g > 100 and g > r * 1.2:
                border_green += 1
            border_total += 1
    return border_green > border_total * threshold


def fix_green_background(arr, bg_tolerance=80):
    """Remove green background pixels using broad detection.

    Two-pronged approach:
    1. Greenish mask: any pixel where G > 100, G > R*1.1, B < 120
       (catches all green shades, not just one specific color)
    2. Near-background mask: any pixel within bg_tolerance of the dominant
       border color (catches color variations from AI upscaling)

    Returns (fixed_array, pixels_removed).
    """
    h, w = arr.shape[:2]

    # Heuristic 1: broad greenish detection
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    greenish = (g > 100) & (g > r * 1.1) & (b < 120)

    # Heuristic 2: near the dominant border color
    border = []
    for x in range(w):
        border.append(arr[0, x, :3].tobytes())
        border.append(arr[h - 1, x, :3].tobytes())
    for y in range(h):
        border.append(arr[y, 0, :3].tobytes())
        border.append(arr[y, w - 1, :3].tobytes())

    from collections import Counter
    counts = Counter(border)
    if counts:
        bg_bytes = counts.most_common(1)[0][0]
        bg_color = np.frombuffer(bg_bytes, dtype=np.uint8).astype(int)
        diff = np.abs(arr[:, :, :3].astype(int) - bg_color).sum(axis=2)
        near_bg = diff < bg_tolerance
    else:
        near_bg = np.zeros((h, w), dtype=bool)

    # Combine both heuristics
    to_fix = greenish | near_bg

    old_opaque = int((arr[:, :, 3] > 128).sum())
    arr[:, :, 3] = np.where(to_fix, 0, arr[:, :, 3])
    new_opaque = int((arr[:, :, 3] > 128).sum())

    return arr, old_opaque - new_opaque


def process_file(fname, src_dir, hd_dir):
    """Process a single file. Returns (filename, success, green_fixed)."""
    hd_path = os.path.join(hd_dir, fname)
    if not os.path.exists(hd_path):
        return (fname, False, 0)

    src_path = os.path.join(src_dir, fname)
    try:
        hd = Image.open(hd_path)

        # Step 1: Build mask from original 8-bit palette PNG
        if os.path.exists(src_path):
            orig = Image.open(src_path)
            if orig.mode == 'P':
                orig_arr = np.array(orig)
                border = np.concatenate([orig_arr[0, :], orig_arr[-1, :],
                                         orig_arr[:, 0], orig_arr[:, -1]])
                unique, counts = np.unique(border, return_counts=True)
                bg_idx = int(unique[np.argmax(counts)])

                mask_orig = (orig_arr != bg_idx).astype(np.uint8) * 255
                mask_img = Image.fromarray(mask_orig, mode='L')
                mask_hd = mask_img.resize(hd.size, Image.Resampling.BILINEAR)
                mask_arr = np.array(mask_hd, dtype=np.uint8)

                hd_rgb = np.array(hd.convert('RGB'))
                hd_out = np.zeros((hd.size[1], hd.size[0], 4), dtype=np.uint8)
                hd_out[:, :, :3] = hd_rgb
                hd_out[:, :, 3] = mask_arr
            else:
                hd_out = np.array(hd.convert('RGBA'))
        else:
            hd_out = np.array(hd.convert('RGBA'))

        # Step 2: Post-process green background if border is greenish
        green_fixed = 0
        if hd_out.shape[2] == 4 and has_green_border(hd_out):
            hd_out, green_fixed = fix_green_background(hd_out)

        Image.fromarray(hd_out, 'RGBA').save(hd_path)
        return (fname, True, green_fixed)
    except Exception as e:
        return (fname, False, 0)


def process_dir_mp(src_dir, hd_dir, label, workers):
    """Process all PNGs in a directory using multiprocessing."""
    if not os.path.exists(src_dir):
        print(f"  Source not found: {src_dir}")
        return 0, 0
    os.makedirs(hd_dir, exist_ok=True)

    fnames = []
    with os.scandir(hd_dir) as it:
        for e in it:
            if e.name.endswith('.png') and e.is_file():
                fnames.append(e.name)

    total = len(fnames)
    if total == 0:
        return 0, 0

    applied = 0
    green_total = 0
    process = partial(process_file, src_dir=src_dir, hd_dir=hd_dir)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process, f): f for f in fnames}
        with tqdm(total=total, unit='img', desc=f'Alpha fixup ({label})',
                  ncols=90) as pbar:
            for future in as_completed(futures):
                _, ok, gf = future.result()
                if ok:
                    applied += 1
                    green_total += gf
                pbar.update(1)

    return applied, green_total


def main():
    parser = argparse.ArgumentParser(
        description='Alpha mask for objects/layers with green background cleanup')
    parser.add_argument('--workers', type=int, default=6,
                        help='Parallel workers (default: 6)')
    args = parser.parse_args()

    objs, green_objs = process_dir_mp(SRC, HD, "objects", args.workers)
    lyrs, green_lyrs = process_dir_mp(SRC_L, HD_L, "layers", args.workers)
    print(f'Objects: {objs} converted, {green_objs} green-bg pixels removed')
    print(f'Layers: {lyrs} converted, {green_lyrs} green-bg pixels removed')
    print('Done')


if __name__ == '__main__':
    main()
