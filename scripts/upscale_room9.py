#!/usr/bin/env python3
"""Upscale only Room 9 costumes using RealESRGAN + Chaikin alpha."""
import sys, os, glob, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upscale_esrgan import upscale_image

SRC = '/opt/data/local/comi-hd-final/hd/costumes'  # already HD, no upscale needed
DST = '/opt/data/local/comi-hd-final/hd/costumes'

os.makedirs(DST, exist_ok=True)

# Room 9 = LFLF_0009, AKOS_0025 (Guybrush), AKOS_0026 (Larry), AKOS_0028 (pirates)
room9 = sorted(glob.glob(os.path.join(SRC, 'LFLF_0009_AKOS_0025_aframe_*.png')) +
               glob.glob(os.path.join(SRC, 'LFLF_0009_AKOS_0026_aframe_*.png')) +
               glob.glob(os.path.join(SRC, 'LFLF_0009_AKOS_0028_aframe_*.png')))

print(f'Room 9 frames to process: {len(room9)}')

start = time.time()
for i, src_path in enumerate(room9):
    fname = os.path.basename(src_path)
    dst_path = os.path.join(DST, fname)
    try:
        upscale_image(src_path, dst_path)
    except Exception as e:
        print(f'  ERROR {fname}: {e}')
    if (i + 1) % 20 == 0:
        elapsed = time.time() - start
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remain = len(room9) - i - 1
        print(f'  [{i+1}/{len(room9)}] {rate:.1f} fps, ETA: {remain/rate/60:.1f}min' if rate > 0 else f'  [{i+1}/{len(room9)}]')

total = time.time() - start
print(f'\nDone in {total/60:.1f} min')
