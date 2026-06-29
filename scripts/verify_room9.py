#!/usr/bin/env python3
"""Render a visual proof: overlay HD Guybrush on HD cannon background."""
import sys, os, numpy as np
from PIL import Image

BG_PATH = '/opt/data/local/comi-hd-final/hd/backgrounds/bg_0009.png'
COSTUME_DIR = '/opt/data/local/comi-hd-final/hd/costumes'

# Load HD background
bg = Image.open(BG_PATH).convert('RGBA')
print(f'Background: {bg.size}')

# Load a Guybrush frame (HD)
guybrush = Image.open(os.path.join(COSTUME_DIR, 'LFLF_0009_AKOS_0025_aframe_100.png')).convert('RGBA')
print(f'Guybrush: {guybrush.size}')

# Check for white pixels in transparent areas
gb_arr = np.array(guybrush)
alpha = gb_arr[:,:,3]
trans = alpha == 0
white_trans = np.all(gb_arr[trans] >= [250,250,250,0], axis=1) if trans.any() else np.array([])

print(f'Alpha stats: {np.sum(trans)} trans ({100*np.sum(trans)/alpha.size:.1f}%), {np.sum(alpha==255)} opaque')
if len(white_trans):
    print(f'  White RGB in transparent area: {np.sum(white_trans)} ({100*np.sum(white_trans)/np.sum(trans):.1f}%)')
    
# Check that NO opaque pixels are white (that would be the white streak bug)
opaque = alpha > 128
if opaque.any():
    white_opaque = np.all(gb_arr[opaque, :3] >= [250,250,250], axis=1)
    print(f'  White in OPAQUE area: {np.sum(white_opaque)} — this would be visible!')

print()
print('=== HD Costume Alpha Verification ===')
# Verify: Chaikin preserved original SD fill-pixel transparency
# By checking that the alpha mask has HOLES (transparent areas inside the contour)
# The white fill pixels should be transparent, not filled by fillPoly
# Sample the center of the costume - if there's a hole, our fix worked
h, w = gb_arr.shape[:2]
print(f'Alpha at center ({w//2},{h//2}): alpha={gb_arr[h//2,w//2,3]}')
# Check a few lines for alpha holes
mid_row = alpha[h//2, :]
hole_pixels = np.sum(mid_row == 0)
total_row = len(mid_row)
print(f'Center row alpha holes: {hole_pixels}/{total_row} transparent ({100*hole_pixels/total_row:.1f}%)')

# Composite: Guybrush at position on cannon bg
# For a visual test, paste him at roughly his in-game position
canvas = bg.copy()
# Guybrush is usually positioned center-bottom
px = (bg.width - guybrush.width) // 2
py = bg.height - guybrush.height - 50
canvas.paste(guybrush, (px, py), guybrush)

out_path = '/opt/data/local/comi-hd-final/hd/room9_proof.png'
canvas.save(out_path)
print(f'\nProof image saved: {out_path} (MEDIA:{out_path})')
