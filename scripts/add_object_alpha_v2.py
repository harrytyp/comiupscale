#!/usr/bin/env python3
"""
Improved alpha generator: detects transparent color from original 8-bit object
by analyzing the border/most-common-pixel pattern, not just palette index 0.
"""

import os, sys
from PIL import Image
import numpy as np

SRC_DIR = 'assets/extracted/COMI/IMAGES/objects'
HD_DIR = 'game/hd/objects'

def process_object(src_path, hd_path):
    if not os.path.exists(hd_path):
        return False, 'no_hd_file'
    
    orig = Image.open(src_path)
    hd = Image.open(hd_path)
    
    if hd.mode == 'RGBA':
        hd_arr = np.array(hd)
        if hd_arr[:,:,3].min() < 255:
            return False, 'already_alpha'
    
    if orig.mode != 'P':
        return False, 'not_palette'
    
    orig_arr = np.array(orig)
    h_orig, w_orig = orig_arr.shape
    
    # Strategy: find the transparent pixel value by looking at
    # the MOST common pixel value along all 4 borders of the original image.
    # In COMI objects, the transparent background surrounds the object,
    # so border pixels should be the transparent color.
    border_pixels = np.concatenate([
        orig_arr[0, :],          # top row
        orig_arr[-1, :],         # bottom row
        orig_arr[:, 0],          # left col
        orig_arr[:, -1],         # right col
    ])
    
    unique, counts = np.unique(border_pixels, return_counts=True)
    # The most common border pixel is likely the transparent color
    trans_idx = unique[np.argmax(counts)]
    
    # Check: does this index appear mostly on borders and rarely inside?
    total = orig_arr.size
    count = (orig_arr == trans_idx).sum()
    
    # If the most common index covers >30% of the image, it's likely background
    if count < total * 0.10:
        return False, 'no_clear_bg'
    
    # Create transparency mask at original resolution
    trans_mask = (orig_arr == trans_idx)
    
    # Scale to HD size
    hd_w, hd_h = hd.size
    scale_x = hd_w / w_orig
    scale_y = hd_h / h_orig
    
    hd_alpha = np.ones((hd_h, hd_w), dtype=np.uint8) * 255
    for y in range(hd_h):
        orig_y = min(int(y / scale_y), h_orig - 1)
        row_hd = int(orig_y * hd_w / w_orig)  # not needed, use original mapping
        for x in range(hd_w):
            orig_x = min(int(x / scale_x), w_orig - 1)
            if trans_mask[orig_y, orig_x]:
                hd_alpha[y, x] = 0
    
    # Create RGBA
    if hd.mode == 'RGBA':
        hd_out = np.array(hd)
        hd_out[:,:,3] = hd_alpha
    else:
        hd_rgb = np.array(hd)
        hd_out = np.zeros((hd_h, hd_w, 4), dtype=np.uint8)
        hd_out[:,:,:3] = hd_rgb
        hd_out[:,:,3] = hd_alpha
    
    out_img = Image.fromarray(hd_out, 'RGBA')
    out_img.save(hd_path)
    return True, f'converted (idx={trans_idx})'


def main():
    count = 0
    for fname in sorted(os.listdir(SRC_DIR)):
        if not fname.endswith('.png'):
            continue
        src = os.path.join(SRC_DIR, fname)
        hd = os.path.join(HD_DIR, fname)
        ok, msg = process_object(src, hd)
        if ok:
            count += 1
        elif msg not in ('already_alpha', 'no_clear_bg', 'not_palette', 'no_hd_file'):
            print(f'  {fname}: {msg}')
        if count % 100 == 0 and count > 0:
            print(f'  {count} converted...')
    print(f'Total converted: {count}')


if __name__ == '__main__':
    main()
