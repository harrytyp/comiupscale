#!/usr/bin/env python3
"""
Alpha generator v6: pixel-precise transparency mask from original 8-bit object.
Multiprocess version — processes objects and layers in parallel workers.

v6.1: Added post-processing step to remove residual background-colored pixels
      that survive the BILINEAR mask resize (e.g. green grass background at
      RGB ~(110,199,24) appearing as semi-opaque edges after upscaling).

Pipeline position: Run AFTER upscale_esrgan.py / batch_upscale_costumes.py.
Reads original 8-bit palette PNGs to build a per-pixel mask, resizes to HD,
then applies a second pass to catch remaining background-colored pixels in
the HD output.

Usage:
    python scripts/add_object_alpha_v6.py [--workers 4] [--bg-tolerance 50]
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


def detect_bg_color_from_hd(hd_arr):
    """Detect dominant background color from border pixels of an RGBA HD image.

    Samples all 4 edges. The most common opaque border color is assumed to be
    the background (e.g. green grass RGB~(110,199,24) from the original game
    room background that was baked into the extracted object).
    """
    h, w = hd_arr.shape[:2]
    border = []
    for x in range(w):
        border.append(hd_arr[0, x, :3].tobytes())
        border.append(hd_arr[h-1, x, :3].tobytes())
    for y in range(h):
        border.append(hd_arr[y, 0, :3].tobytes())
        border.append(hd_arr[y, w-1, :3].tobytes())

    from collections import Counter
    counts = Counter(border)
    if not counts:
        return None
    most_common = counts.most_common(1)[0]
    bg_bytes = most_common[0]
    bg_rgb = np.frombuffer(bg_bytes, dtype=np.uint8)
    return bg_rgb


def is_greenish(color_rgb):
    """Check if a color is greenish (typical COMI grass/vegetation background).

    Thresholds: G > 130, G > R*1.3, B < 80 — matches RGB(110,199,24) and
    similar variants that appear across many COMI outdoor object extractions.
    """
    r, g, b = int(color_rgb[0]), int(color_rgb[1]), int(color_rgb[2])
    return g > 130 and g > r * 1.3 and b < 80


def postprocess_green_bg(hd_arr, bg_tolerance):
    """Remove residual green background pixels after mask-based alpha.

    Many COMI objects were extracted with a green grass background
    (RGB~110,199,24) baked in. The BILINEAR mask resize from v6 leaves
    semi-transparent edges where green leaks through. This step detects the
    dominant green background from border pixels and makes matching pixels
    transparent, regardless of their current alpha value.

    Returns the fixed array and (pixels_fixed, total, bg_color) tuple.
    """
    h, w = hd_arr.shape[:2]
    total = h * w

    bg_color = detect_bg_color_from_hd(hd_arr)
    if bg_color is None:
        return hd_arr, (0, total, None)

    if not is_greenish(bg_color):
        return hd_arr, (0, total, tuple(bg_color))

    # Find all pixels within tolerance of the green background color
    rgb = hd_arr[:, :, :3].astype(np.int16)
    diff = np.abs(rgb - bg_color.astype(np.int16)).sum(axis=2)
    mask = diff < bg_tolerance

    pixels_fixed = int(mask.sum())
    if pixels_fixed > 0:
        hd_arr[:, :, 3] = np.where(mask, 0, hd_arr[:, :, 3])

    return hd_arr, (pixels_fixed, total, tuple(bg_color))


def process_file(fname, src_dir, hd_dir, bg_tolerance):
    """Process a single file. Returns (filename, success, stats)."""
    hd_path = os.path.join(hd_dir, fname)
    if not os.path.exists(hd_path):
        return (fname, False, None)

    src_path = os.path.join(src_dir, fname)
    try:
        hd = Image.open(hd_path)

        # Step 1: Build mask from original 8-bit palette PNG
        mask_fixed = 0
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
                # Original is not palette-indexed — convert existing to RGBA
                hd_out = np.array(hd.convert('RGBA'))
        else:
            # No original available — convert existing to RGBA
            hd_out = np.array(hd.convert('RGBA'))

        # Step 2: Post-process to remove residual green background pixels
        hd_out, (green_fixed, total, bg_color) = postprocess_green_bg(
            hd_out, bg_tolerance)

        Image.fromarray(hd_out, 'RGBA').save(hd_path)

        stats = {
            'mask_fixed': mask_fixed,
            'green_fixed': green_fixed,
            'total': total,
            'bg_color': bg_color,
        }
        return (fname, True, stats)
    except Exception as e:
        return (fname, False, None)


def process_dir_mp(src_dir, hd_dir, label, workers, bg_tolerance):
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
    process = partial(process_file, src_dir=src_dir, hd_dir=hd_dir,
                      bg_tolerance=bg_tolerance)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process, f): f for f in fnames}
        with tqdm(total=total, unit='img', desc=f'Alpha fixup ({label})',
                  ncols=90) as pbar:
            for future in as_completed(futures):
                _, ok, stats = future.result()
                if ok:
                    applied += 1
                    if stats and stats['green_fixed'] > 0:
                        green_total += stats['green_fixed']
                pbar.update(1)

    return applied, green_total


def main():
    parser = argparse.ArgumentParser(
        description='Alpha mask for objects/layers with green background cleanup')
    parser.add_argument('--workers', type=int, default=6,
                        help='Parallel workers (default: 6)')
    parser.add_argument('--bg-tolerance', type=int, default=50,
                        help='Color distance tolerance for background detection '
                             '(default: 50). Lower = stricter, higher = more '
                             'aggressive cleanup.')
    args = parser.parse_args()

    objs, green_objs = process_dir_mp(SRC, HD, "objects", args.workers,
                                       args.bg_tolerance)
    lyrs, green_lyrs = process_dir_mp(SRC_L, HD_L, "layers", args.workers,
                                       args.bg_tolerance)
    print(f'Objects: {objs} converted, {green_objs} green-bg pixels removed')
    print(f'Layers: {lyrs} converted, {green_lyrs} green-bg pixels removed')
    print('Done')


if __name__ == '__main__':
    main()
