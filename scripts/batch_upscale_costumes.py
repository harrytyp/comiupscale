#!/usr/bin/env python3
"""
Batch upscale all extracted costume frames using RealESRGAN.
Reads from hd/costumes/, writes to hd/costumes_ai/.
Use --force to regenerate all frames (overwrites existing).
"""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))

from upscale_esrgan import upscale_image

SRC_DIR = '/opt/data/local/scummvm-build/hd/costumes'
DST_DIR = '/opt/data/local/scummvm-build/hd/costumes_ai'

os.makedirs(DST_DIR, exist_ok=True)

# --force flag: regenerate all
force = '--force' in sys.argv

all_files = sorted([f for f in os.listdir(SRC_DIR) if f.endswith('.png')])
print(f'Total frames: {len(all_files)}')

if force:
    print('Force mode: regenerating ALL frames')
    todo = all_files
else:
    already_done = set(os.listdir(DST_DIR))
    todo = [f for f in all_files if f not in already_done]
    print(f'Already done: {len(all_files) - len(todo)}')
    print(f'Remaining: {len(todo)}')

if not todo:
    print('Nothing to do!')
    sys.exit(0)

start = time.time()
processed = 0
errors = 0

for i, fname in enumerate(todo):
    src = os.path.join(SRC_DIR, fname)
    dst = os.path.join(DST_DIR, fname)
    
    try:
        upscale_image(src, dst)
        processed += 1
    except Exception as e:
        print(f'  ERROR {fname}: {e}')
        errors += 1
    
    # Progress every 100 frames
    if (i + 1) % 100 == 0:
        elapsed = time.time() - start
        rate = (i + 1) / elapsed
        eta = (len(todo) - i - 1) / rate / 3600
        print(f'Progress: {i+1}/{len(todo)} ({processed} ok, {errors} err) - {rate:.1f} frames/s - ETA: {eta:.1f}h')

elapsed = time.time() - start
print(f'\nDone! Processed {processed} frames in {elapsed/3600:.1f}h ({errors} errors)')
print(f'Output: {DST_DIR}')
