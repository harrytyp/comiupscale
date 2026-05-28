#!/usr/bin/env python3
"""
Alpha generator v5: pixel-precise transparency mask from original 8-bit object.
Optimized version: NEAREST mask resize (binary data, no quality loss),
os.scandir for NAS speed, tqdm progress bar, removed pointless float32 dance.

Usage:
    python scripts/add_object_alpha_v5.py
"""

import os
from PIL import Image
import numpy as np
from tqdm import tqdm

SRC = 'Z:/Projekte/COMI-Upscaled/CMI UPSCALED/extracted/COMI/IMAGES/objects'
HD = 'Z:/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/objects'
SRC_L = 'Z:/Projekte/COMI-Upscaled/CMI UPSCALED/extracted/COMI/IMAGES/objects_layers'
HD_L = 'Z:/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/objects_layers'


def process(src_path, hd_path):
    if not os.path.exists(hd_path):
        return False
    orig = Image.open(src_path)
    hd = Image.open(hd_path)

    if orig.mode != 'P':
        return False

    orig_arr = np.array(orig)
    border = np.concatenate([orig_arr[0, :], orig_arr[-1, :],
                             orig_arr[:, 0], orig_arr[:, -1]])
    unique, counts = np.unique(border, return_counts=True)
    bg_idx = int(unique[np.argmax(counts)])

    # Binary mask → BILINEAR 4x scale (anti-aliases edges; NEAREST creates stair-steps)
    mask_orig = (orig_arr != bg_idx).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask_orig, mode='L')
    mask_hd = mask_img.resize(hd.size, Image.BILINEAR)
    mask_arr = np.array(mask_hd, dtype=np.uint8)

    # RGBA composite
    hd_rgb = np.array(hd.convert('RGB'))
    hd_out = np.zeros((hd.size[1], hd.size[0], 4), dtype=np.uint8)
    hd_out[:, :, :3] = hd_rgb
    hd_out[:, :, 3] = mask_arr

    out_img = Image.fromarray(hd_out, 'RGBA')
    out_img.save(hd_path)
    return True


def process_dir(src_dir, hd_dir, label):
    count = 0
    if not os.path.exists(src_dir):
        return 0
    os.makedirs(hd_dir, exist_ok=True)

    total = 0
    with os.scandir(src_dir) as it:
        for e in it:
            if e.name.endswith('.png') and e.is_file():
                total += 1

    pbar = tqdm(total=total, unit='img', desc=f'Alpha fixup ({label})',
                ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

    with os.scandir(src_dir) as it:
        for e in it:
            if not e.name.endswith('.png') or not e.is_file():
                continue
            if process(e.path, os.path.join(hd_dir, e.name)):
                count += 1
            pbar.update(1)

    pbar.close()
    return count


print(f'Objects: {process_dir(SRC, HD, "objects")} converted')
print(f'Layers: {process_dir(SRC_L, HD_L, "layers")} converted')
print('Done')
