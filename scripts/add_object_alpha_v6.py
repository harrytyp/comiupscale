#!/usr/bin/env python3
"""
Alpha generator v6: pixel-precise transparency mask from original 8-bit object.
Multiprocess version — processes objects and layers in parallel workers.

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


def process_file(fname, src_dir, hd_dir):
    """Process a single file. Returns (filename, True/False)."""
    hd_path = os.path.join(hd_dir, fname)
    if not os.path.exists(hd_path):
        return (fname, False)

    src_path = os.path.join(src_dir, fname)
    try:
        orig = Image.open(src_path)
        hd = Image.open(hd_path)

        if orig.mode != 'P':
            return (fname, False)

        orig_arr = np.array(orig)
        border = np.concatenate([orig_arr[0, :], orig_arr[-1, :],
                                 orig_arr[:, 0], orig_arr[:, -1]])
        unique, counts = np.unique(border, return_counts=True)
        bg_idx = int(unique[np.argmax(counts)])

        mask_orig = (orig_arr != bg_idx).astype(np.uint8) * 255
        mask_img = Image.fromarray(mask_orig, mode='L')
        mask_hd = mask_img.resize(hd.size, Image.BILINEAR)
        mask_arr = np.array(mask_hd, dtype=np.uint8)

        hd_rgb = np.array(hd.convert('RGB'))
        hd_out = np.zeros((hd.size[1], hd.size[0], 4), dtype=np.uint8)
        hd_out[:, :, :3] = hd_rgb
        hd_out[:, :, 3] = mask_arr

        Image.fromarray(hd_out, 'RGBA').save(hd_path)
        return (fname, True)
    except Exception as e:
        return (fname, False)


def process_dir_mp(src_dir, hd_dir, label, workers):
    """Process all PNGs in a directory using multiprocessing."""
    if not os.path.exists(src_dir):
        print(f"  Source not found: {src_dir}")
        return 0
    os.makedirs(hd_dir, exist_ok=True)

    fnames = []
    with os.scandir(src_dir) as it:
        for e in it:
            if e.name.endswith('.png') and e.is_file():
                fnames.append(e.name)

    total = len(fnames)
    if total == 0:
        return 0

    applied = 0
    process = partial(process_file, src_dir=src_dir, hd_dir=hd_dir)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process, f): f for f in fnames}
        with tqdm(total=total, unit='img', desc=f'Alpha fixup ({label})',
                  ncols=90) as pbar:
            for future in as_completed(futures):
                _, ok = future.result()
                if ok:
                    applied += 1
                pbar.update(1)

    return applied


def main():
    parser = argparse.ArgumentParser(description='Alpha mask for objects/layers')
    parser.add_argument('--workers', type=int, default=6,
                        help='Parallel workers (default: 6)')
    args = parser.parse_args()

    objs = process_dir_mp(SRC, HD, "objects", args.workers)
    lyrs = process_dir_mp(SRC_L, HD_L, "layers", args.workers)
    print(f'Objects: {objs} converted')
    print(f'Layers: {lyrs} converted')
    print('Done')


if __name__ == '__main__':
    main()
