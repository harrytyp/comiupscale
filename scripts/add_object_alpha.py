#!/usr/bin/env python3
"""
Generate RGBA HD object PNGs with proper alpha transparency.

COMI objects use palette index 0 as transparent. The original extraction
saves them as paletted PNGs with NO transparency metadata. When upscaled
by RealESRGAN, the transparent background gets filled with arbitrary colors.

This script:
1. Loads original 8-bit object PNG
2. Uses palette index 0 as transparency mask
3. Loads upscaled HD version
4. Sets alpha=0 where original was transparent (with 4x scaling)
5. Saves as RGBA PNG

Run:
  cd /z/Projekte/COMI-Upscaled
  python scripts/add_object_alpha.py
"""

import os
import sys
from PIL import Image
import numpy as np

SRC_DIR = 'assets/extracted/COMI/IMAGES/objects'
SRC_LAYERS_DIR = 'assets/extracted/COMI/IMAGES/objects_layers'
HD_DIR = 'game/hd/objects'
HD_LAYERS_DIR = 'game/hd/objects_layers'


def process_object(src_path, hd_path):
    """Process a single object: add alpha to HD version from original mask."""
    if not os.path.exists(hd_path):
        return False

    orig = Image.open(src_path)
    hd = Image.open(hd_path)

    if hd.mode == 'RGBA':
        # Already has alpha - check if it's meaningful
        hd_arr = np.array(hd)
        if hd_arr[:, :, 3].min() < 255:
            return False  # Already has valid alpha
    elif hd.mode != 'RGB':
        return False  # Unexpected mode

    # Convert original to palette
    if orig.mode != 'P':
        orig = orig.convert('P')

    orig_arr = np.array(orig)

    # In COMI objects, palette index 0 is transparent
    trans_mask = (orig_arr == 0)

    if not trans_mask.any():
        return False  # No transparent pixels

    # Scale mask to HD size (4x)
    # For each HD pixel, if the corresponding original pixel was transparent, set alpha=0
    hd_w, hd_h = hd.size
    orig_w, orig_h = orig.size
    scale_x = hd_w / orig_w
    scale_y = hd_h / orig_h

    # Create HD-sized alpha mask from original transparency
    hd_alpha = np.ones((hd_h, hd_w), dtype=np.uint8) * 255

    for y in range(hd_h):
        orig_y = min(int(y / scale_y), orig_h - 1)
        for x in range(hd_w):
            orig_x = min(int(x / scale_x), orig_w - 1)
            if trans_mask[orig_y, orig_x]:
                hd_alpha[y, x] = 0

    # Create RGBA output
    if hd.mode == 'RGBA':
        hd_out = np.array(hd)
        hd_out[:, :, 3] = hd_alpha
    else:
        hd_rgb = np.array(hd)
        hd_out = np.zeros((hd_h, hd_w, 4), dtype=np.uint8)
        hd_out[:, :, :3] = hd_rgb
        hd_out[:, :, 3] = hd_alpha

    # Save as RGBA PNG
    out_img = Image.fromarray(hd_out, 'RGBA')
    out_img.save(hd_path)
    return True


def main():
    count = 0
    errors = 0

    # Create directories if needed
    for d in [HD_DIR, HD_LAYERS_DIR]:
        os.makedirs(d, exist_ok=True)

    # Process objects
    if os.path.exists(SRC_DIR):
        for fname in sorted(os.listdir(SRC_DIR)):
            if not fname.endswith('.png'):
                continue
            src = os.path.join(SRC_DIR, fname)
            hd = os.path.join(HD_DIR, fname)
            try:
                if process_object(src, hd):
                    count += 1
                    if count % 50 == 0:
                        print(f'  {count} objects processed...')
            except Exception as e:
                print(f'  ERROR: {fname}: {e}')
                errors += 1

    print(f'Objects: {count} converted, {errors} errors')

    # Process layers
    lay_count = 0
    if os.path.exists(SRC_LAYERS_DIR):
        for fname in sorted(os.listdir(SRC_LAYERS_DIR)):
            if not fname.endswith('.png'):
                continue
            src = os.path.join(SRC_LAYERS_DIR, fname)
            hd = os.path.join(HD_LAYERS_DIR, fname)
            try:
                if process_object(src, hd):
                    lay_count += 1
            except Exception as e:
                print(f'  ERROR: {fname}: {e}')
                errors += 1

    print(f'Layers: {lay_count} converted, {errors} total errors')
    print('Done!')


if __name__ == '__main__':
    main()
