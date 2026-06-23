#!/usr/bin/env python3
"""
Bulk upscale costume PNGs using RealESRGAN with a tqdm progress bar.

Iterates over extracted costume PNGs, upscales any that haven't been
upscaled yet (checks output dir), and shows ETA as it goes.

Usage:
    python scripts/upscale_costumes.py [--gpu auto] [--src DIR] [--dst DIR]

Requires: Pillow, numpy, tqdm
"""

import os
import subprocess
import sys
import time
import argparse
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description='Bulk upscale COMI costumes')
    parser.add_argument('--gpu', default='auto', help='GPU device ID for RealESRGAN')
    parser.add_argument('--src', default='assets/extracted/COMI/costumes')
    parser.add_argument('--dst', default='assets/upscaled/costumes')
    parser.add_argument('--esrgan', default='tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe')
    parser.add_argument('--models', default='tools/realesrgan-ncnn-vulkan-v0.2.0-windows/models')
    parser.add_argument('--model-name', default='realesrgan-x4plus-anime')
    parser.add_argument('--limit', type=int, default=0, help='Max files to upscale (0 = all)')
    parser.add_argument('--skip-existing', action='store_true', default=True)
    parser.add_argument('--no-progress', action='store_true', help='Disable tqdm bar (plain output)')
    args = parser.parse_args()

    src_dir = args.src
    dst_dir = args.dst
    os.makedirs(dst_dir, exist_ok=True)

    # --- Scan files ---
    tqdm.write('Scanning source directory...')
    t0 = time.time()
    entries = []
    with os.scandir(src_dir) as it:
        for entry in it:
            if entry.name.endswith('.png') and entry.is_file():
                entries.append(entry.name)
    entries.sort()
    total = len(entries)
    tqdm.write(f'Found {total} costume PNGs ({time.time()-t0:.1f}s)')

    if total == 0:
        tqdm.write('Nothing to do.')
        return

    # --- Run the gauntlet ---
    upscaled = 0
    skipped = 0
    errors = 0
    process_start = time.time()

    pbar = tqdm(
        total=total,
        unit='img',
        unit_scale=True,
        desc='Upscaling costumes',
        ncols=80,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
        disable=args.no_progress,
    )

    for fname in entries:
        src = os.path.join(src_dir, fname)
        dst = os.path.join(dst_dir, fname)

        if args.skip_existing and os.path.exists(dst):
            skipped += 1
            pbar.update(1)
            pbar.set_postfix_str(f'skip {skipped} err {errors}', refresh=False)
            continue

        if upscaled >= args.limit and args.limit > 0:
            # Skip remaining in pbar
            remaining = len(entries) - (upscaled + skipped)
            pbar.update(remaining)
            break

        upscaled += 1
        tqdm.write(f'  → {fname}', file=sys.stderr) if upscaled <= 3 or upscaled % 500 == 0 else None

        result = subprocess.run(
            [args.esrgan, '-i', src, '-o', dst,
             '-m', args.models, '-n', args.model_name, '-g', args.gpu],
            capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            errors += 1
            if errors <= 10:
                tqdm.write(f'  ⚠ ERROR on {fname}: {result.stderr.strip()[:200]}')

        pbar.update(1)
        if upscaled % 100 == 0:
            pbar.set_postfix_str(f'upscaled={upscaled} skip={skipped} err={errors}', refresh=True)

    pbar.close()

    elapsed = time.time() - process_start
    print()
    print('═' * 50)
    print(f'  Done!  {upscaled} upscaled  |  {skipped} skipped  |  {errors} errors')
    print(f'  Time:  {elapsed:.0f}s ({elapsed/60:.1f}min)')
    print('═' * 50)


if __name__ == '__main__':
    main()
