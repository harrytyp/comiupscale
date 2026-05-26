#!/usr/bin/env python3
"""
Alpha generator v4: pixel-precise transparency mask from original 8-bit object.
Uses the original's pixel indices to create a hard transparency mask,
then applies gaussian blur to anti-alias edges.
"""

import os
from PIL import Image, ImageFilter
import numpy as np

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
    border = np.concatenate([orig_arr[0,:], orig_arr[-1,:], orig_arr[:,0], orig_arr[:,-1]])
    unique, counts = np.unique(border, return_counts=True)
    bg_idx = int(unique[np.argmax(counts)])

    # Build binary transparency mask at original resolution
    mask_orig = (orig_arr != bg_idx).astype(np.uint8) * 255  # 255 = opaque, 0 = transparent

    # Scale up to HD size using PIL (handles anti-aliasing)
    mask_img = Image.fromarray(mask_orig, mode='L')
    mask_hd = mask_img.resize(hd.size, Image.LANCZOS)

    # Convert to numpy array and apply soft threshold
    mask_arr = np.array(mask_hd, dtype=np.float32)
    
    # Soften: clip to [0,255] and convert to uint8
    mask_arr = np.clip(mask_arr, 0, 255).astype(np.uint8)

    # Create RGBA output
    hd_rgb = np.array(hd.convert('RGB'))
    hd_out = np.zeros((hd.size[1], hd.size[0], 4), dtype=np.uint8)
    hd_out[:,:,:3] = hd_rgb
    hd_out[:,:,3] = mask_arr

    out_img = Image.fromarray(hd_out, 'RGBA')
    out_img.save(hd_path)
    return True


def process_dir(src_dir, hd_dir):
    count = 0
    if not os.path.exists(src_dir):
        return 0
    os.makedirs(hd_dir, exist_ok=True)
    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith('.png'):
            continue
        if process(os.path.join(src_dir, fname), os.path.join(hd_dir, fname)):
            count += 1
    return count


print(f'Objects: {process_dir(SRC, HD)} converted')
print(f'Layers: {process_dir(SRC_L, HD_L)} converted')
print('Done')
