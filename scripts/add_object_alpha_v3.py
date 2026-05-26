#!/usr/bin/env python3
"""
Alpha generator v3: distance-based chroma-key with anti-aliased edges.
Detects the background color from the original 8-bit border, then uses
a color-distance threshold to set alpha on HD version, with smooth
edge falloff for anti-aliased pixels.
"""

import os
from PIL import Image
import numpy as np

SRC = 'Z:/Projekte/COMI-Upscaled/CMI UPSCALED/extracted/COMI/IMAGES/objects'
HD = 'Z:/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/objects'

# Also process layers
SRC_L = 'Z:/Projekte/COMI-Upscaled/CMI UPSCALED/extracted/COMI/IMAGES/objects_layers'
HD_L = 'Z:/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/objects_layers'

THRESHOLD = 40  # color distance threshold for full transparency
SOFTEN = 20     # additional distance range for alpha fade

def process(src_path, hd_path):
    if not os.path.exists(hd_path):
        return False
    orig = Image.open(src_path)
    hd = Image.open(hd_path)
    
    if orig.mode != 'P':
        return False
    
    # Detect background color from original's most common border pixel
    orig_arr = np.array(orig)
    h_border = np.concatenate([orig_arr[0,:], orig_arr[-1,:], orig_arr[:,0], orig_arr[:,-1]])
    unique, counts = np.unique(h_border, return_counts=True)
    bg_idx = int(unique[np.argmax(counts)])
    
    # Get the actual RGB of the background color from the palette
    palette = orig.getpalette()
    bg_r, bg_g, bg_b = palette[bg_idx*3], palette[bg_idx*3+1], palette[bg_idx*3+2]
    
    # Scale to HD size
    hd_rgb = np.array(hd.convert('RGB'))
    hd_h, hd_w, _ = hd_rgb.shape
    
    # Compute color distance from background for each HD pixel
    dr = hd_rgb[:,:,0].astype(int) - bg_r
    dg = hd_rgb[:,:,1].astype(int) - bg_g
    db = hd_rgb[:,:,2].astype(int) - bg_b
    dist = np.sqrt(dr*dr + dg*dg + db*db)
    
    # Alpha: 0 for pixels close to bg color, 255 for far pixels, smooth fade in between
    alpha = np.clip((dist - THRESHOLD) / SOFTEN * 255, 0, 255).astype(np.uint8)
    
    # Create output RGBA
    hd_out = np.zeros((hd_h, hd_w, 4), dtype=np.uint8)
    hd_out[:,:,:3] = hd_rgb
    hd_out[:,:,3] = alpha
    
    out_img = Image.fromarray(hd_out, 'RGBA')
    out_img.save(hd_path)
    return True

def process_dir(src_dir, hd_dir, label):
    count = 0
    if not os.path.exists(src_dir):
        return 0
    os.makedirs(hd_dir, exist_ok=True)
    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith('.png'): continue
        src = os.path.join(src_dir, fname)
        hd = os.path.join(hd_dir, fname)
        if process(src, hd):
            count += 1
    return count

print(f'Objects: {process_dir(SRC, HD, "obj")} converted')
print(f'Layers: {process_dir(SRC_L, HD_L, "lay")} converted')
print('Done')
