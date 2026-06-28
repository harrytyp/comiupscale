#!/usr/bin/env python3
"""
Batch upscale all extracted costume frames using RealESRGAN + Chaikin alpha.
Reads from hd/costumes/, writes to hd/costumes_ai/.
Uses realesrgan-ncnn-vulkan (fast) for RGB upscale, then apply_chaikin_alpha
for smooth vector-contour alpha masks.
Use --force to regenerate all frames (overwrites existing).
Use --no-chaikin to skip alpha smoothing (nearest-neighbor alpha only).
"""
import sys, os, time, subprocess, glob

SRC_DIR = '/opt/data/local/scummvm-build/hd/costumes'
DST_DIR = '/opt/data/local/scummvm-build/hd/costumes_ai'
ESRGAN_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'realesrgan-ncnn-vulkan')

os.makedirs(DST_DIR, exist_ok=True)

force = '--force' in sys.argv
no_chaikin = '--no-chaikin' in sys.argv

all_files = sorted([f for f in os.listdir(SRC_DIR) if f.endswith('.png')])
print(f'Total frames: {len(all_files)}')

if force:
    todo = all_files
else:
    already_done = set(os.listdir(DST_DIR))
    todo = [f for f in all_files if f not in already_done]

print(f'To process: {len(todo)} frames')

if not todo:
    print('Nothing to do!')
    sys.exit(0)

# Step 1: RealESRGAN upscale
start = time.time()
print(f'\n=== Step 1: RealESRGAN upscale ({len(todo)} frames) ===')
processed = 0
errors = 0
for i, fname in enumerate(todo):
    src = os.path.join(SRC_DIR, fname)
    dst = os.path.join(DST_DIR, fname)
    try:
        subprocess.run([ESRGAN_BIN, '-i', src, '-o', dst, '-n', 'x4plus_anime_6B'],
                       capture_output=True, check=True, timeout=30)
        processed += 1
    except Exception as e:
        print(f'  ERROR {fname}: {e}')
        errors += 1
    if (i + 1) % 100 == 0:
        elapsed = time.time() - start
        rate = (i + 1) / elapsed
        remaining = len(todo) - i - 1
        print(f'  [{i+1}/{len(todo)}] {rate:.1f} fps, ETA: {remaining/rate/60:.1f}min')

elapsed1 = time.time() - start
print(f'Step 1 done: {processed} ok, {errors} err in {elapsed1/60:.1f}min')

if no_chaikin:
    print(f'Skipping Chaikin alpha smoothing')
    sys.exit(0)

# Step 2: Chaikin alpha post-processing
from apply_chaikin_alpha import batch_process
print(f'\n=== Step 2: Chaikin alpha smoothing ({processed} frames) ===')
start2 = time.time()
batch_process(SRC_DIR, DST_DIR, pattern=None, max_workers=4)
elapsed2 = time.time() - start2

total = time.time() - start
print(f'\n=== Done ===')
print(f'Step 1 (RealESRGAN): {elapsed1/60:.1f} min')
print(f'Step 2 (Chaikin):    {elapsed2/60:.1f} min')
print(f'Total:              {total/60:.1f} min')
print(f'Output: {DST_DIR}')
