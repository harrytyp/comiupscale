#!/usr/bin/env python3
"""
Apply Chaikin vector-contour alpha smoothing to upscaled HD assets.

Reads the original SD image (any mode with alpha/mask) to compute a binary
alpha mask, applies Chaikin corner-cutting to smooth the contour, scales 4x,
and composites the smooth alpha onto the already-upscaled HD RGB image.

Usage:
    python3 apply_chaikin_alpha.py --single <sd_source.png> <hd_upscaled.png> [--output o.png]
    python3 apply_chaikin_alpha.py --batch <sd_dir> <hd_dir> [--output-dir <out_dir>] [--pattern '*']
"""

import os, sys, argparse
import cv2
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm


# ═══════════════════════════════════════════════════════════════════
# Chaikin corner-cutting
# ═══════════════════════════════════════════════════════════════════

def chaikin_smooth(pts, iterations=3):
    """Chaikin corner cutting: each iteration doubles points and smooths corners."""
    pts = pts.astype(np.float64)
    for _ in range(iterations):
        n = len(pts)
        new_pts = []
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            new_pts.append(0.25 * p1 + 0.75 * p2)
            new_pts.append(0.75 * p1 + 0.25 * p2)
        pts = np.array(new_pts)
    return pts


# ═══════════════════════════════════════════════════════════════════
# Alpha mask extraction (handles all image modes)
# ═══════════════════════════════════════════════════════════════════

def extract_mask(img):
    """Extract binary alpha mask (0/255) from any PIL image mode."""
    arr = np.array(img)

    if img.mode == 'RGBA':
        return (arr[:, :, 3] > 127).astype(np.uint8) * 255
    elif img.mode in ('P', 'PA'):
        # Palette index 0 = transparent (AKOS convention)
        return (arr > 0).astype(np.uint8) * 255
    elif img.mode == 'LA':
        return (arr[:, :, 0] > 127).astype(np.uint8) * 255
    elif img.mode == 'L':
        return (arr > 127).astype(np.uint8) * 255
    elif img.mode == 'RGB':
        # Border detection: most common border pixel = background
        border = np.concatenate([
            arr[0, :, :], arr[-1, :, :],
            arr[:, 0, :], arr[:, -1, :],
        ])
        flat = border[:, 0].astype(int) * 65536 + border[:, 1].astype(int) * 256 + border[:, 2].astype(int)
        vals, cnts = np.unique(flat, return_counts=True)
        if len(vals) <= 1:
            return np.full((arr.shape[0], arr.shape[1]), 255, dtype=np.uint8)
        bg_val = vals[np.argmax(cnts)]
        bg = np.array([(bg_val >> 16) & 0xFF, (bg_val >> 8) & 0xFF, bg_val & 0xFF])
        diff = np.max(np.abs(arr.astype(int) - bg.astype(int)), axis=2)
        return (diff > 30).astype(np.uint8) * 255
    # Fallback: fully opaque
    return np.full((arr.shape[0], arr.shape[1]), 255, dtype=np.uint8)


# ═══════════════════════════════════════════════════════════════════
# Core function: apply Chaikin-smoothed alpha to one HD image
# ═══════════════════════════════════════════════════════════════════

def apply_chaikin_alpha(sd_path, hd_path, output_path=None):
    """Apply Chaikin-smoothed alpha from SD source to HD upscaled image.

    If sd_path doesn't exist, falls back to extracting the alpha mask
    from the HD image itself (at 1/4 resolution for contour computation).
    """
    if not os.path.exists(hd_path):
        return False, f"HD not found: {hd_path}"

    try:
        # Determine source for mask computation
        if os.path.exists(sd_path):
            src_img = Image.open(sd_path)
            src_from_hd = False
        else:
            # Fallback: use HD image's own alpha at reduced resolution
            hd_img_tmp = Image.open(hd_path)
            if hd_img_tmp.mode != 'RGBA':
                return True, "No alpha channel, skipping"
            src_img = hd_img_tmp
            src_from_hd = True

        mask = extract_mask(src_img)

        # If mask from SD is fully opaque, try extracting from HD alpha
        if np.all(mask > 127) and src_from_hd:
            return True, "Fully opaque, no transparency to smooth"

        if np.all(mask > 127) and not src_from_hd:
            # SD is fully opaque — no transparency, skip
            return True, "SD is fully opaque, skipping"

        # Original dimensions for contour finding
        src_h, src_w = mask.shape

        # If source is HD (4x), downsample mask for contour finding
        if src_from_hd:
            src_w //= 4
            src_h //= 4
            mask = cv2.resize(mask, (src_w, src_h), interpolation=cv2.INTER_NEAREST)

        # Find contours: CHAIN_APPROX_NONE preserves all edge pixels for Chaikin
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

        if hierarchy is None or len(contours) == 0:
            # No contours — fully opaque or transparent
            hd_img = Image.open(hd_path)
            if hd_img.mode == 'RGBA':
                arr = np.array(hd_img)
                arr[:, :, 3] = 255 if np.mean(mask) > 127 else 0
                (Image.fromarray(arr, 'RGBA').save(output_path or hd_path))
            return True, f"Fully {'opaque' if np.mean(mask) > 127 else 'transparent'}"

        # Build 4x alpha buffer from smoothed contours
        hierarchy = hierarchy[0]
        alpha_4x = np.zeros((src_h * 4, src_w * 4), dtype=np.uint8)

        outer_list, hole_list = [], []
        for i, cnt in enumerate(contours):
            if len(cnt) < 4:
                continue
            pts = cnt.reshape(-1, 2).astype(np.float64)
            # Chaikin smoothing (3 iterations, same as upscale_esrgan.py)
            pts = chaikin_smooth(pts, iterations=3)
            # Scale 4x
            pts_4x = (pts * 4).astype(np.int32)
            np.clip(pts_4x[:, 0], 0, src_w * 4 - 1, out=pts_4x[:, 0])
            np.clip(pts_4x[:, 1], 0, src_h * 4 - 1, out=pts_4x[:, 1])
            if hierarchy[i][3] == -1:
                outer_list.append(pts_4x)
            else:
                hole_list.append(pts_4x)

        if outer_list:
            cv2.fillPoly(alpha_4x, outer_list, 255)
        if hole_list:
            cv2.fillPoly(alpha_4x, hole_list, 0)

        # Preserve original SD transparency (fill pixels index 255, transparent BG)
        # Chaikin fillPoly fills everything inside outer contours as opaque,
        # which overwrites fill pixels that should stay transparent.
        if not src_from_hd:
            orig_up = cv2.resize(mask, (alpha_4x.shape[1], alpha_4x.shape[0]),
                                 interpolation=cv2.INTER_NEAREST)
            alpha_4x[orig_up == 0] = 0

        # Composite onto HD image
        hd_img = Image.open(hd_path)
        hd_arr = np.array(hd_img)
        if hd_arr.shape[2] == 4:
            hd_arr[:, :, 3] = alpha_4x
        else:
            hd_arr = np.dstack([hd_arr, alpha_4x])

        # Clean RGB in fully transparent areas:
        # RealESRGAN upscales fill pixels (palette index 255 = white) to white RGB,
        # but they should be invisible where alpha=0. Chaikin smoothing makes alpha
        # boundaries tighter, potentially exposing white halos. Set RGB=0 where alpha=0
        # to prevent white bleed-through at transparent edges.
        transparent = (hd_arr[:, :, 3] == 0)
        hd_arr[transparent, 0:3] = 0

        Image.fromarray(hd_arr, 'RGBA').save(output_path or hd_path)

        return True, f"OK ({len(outer_list)} outer, {len(hole_list)} holes)"

    except Exception as e:
        return False, f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════
# Batch processing
# ═══════════════════════════════════════════════════════════════════

def batch_process(sd_dir, hd_dir, output_dir=None, pattern=None, max_workers=4):
    """Batch process all SD→HD pairs in directories."""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    all_files = sorted([f for f in os.listdir(sd_dir) if f.endswith('.png')])
    if pattern:
        import fnmatch
        all_files = [f for f in all_files if fnmatch.fnmatch(f, pattern)]

    if not all_files:
        # No SD files found — try using HD files directly with fallback
        all_files = sorted([f for f in os.listdir(hd_dir) if f.endswith('.png')])
        if pattern:
            all_files = [f for f in all_files if fnmatch.fnmatch(f, pattern)]
        if not all_files:
            print(f"No PNG files found")
            return
        todo = all_files
        use_hd_fallback = True
        print(f"No SD sources — using HD alpha fallback for {len(todo)} images")
    else:
        # Filter to files that have HD counterparts
        todo = [f for f in all_files if os.path.exists(os.path.join(hd_dir, f))]
        use_hd_fallback = False

    print(f"Processing {len(todo)} images ({len(todo)}/{len(all_files)} matched)")
    print(f"  SD: {sd_dir}")
    print(f"  HD: {hd_dir}")

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for fname in todo:
            sd_path = os.path.join(sd_dir, fname)
            hd_path = os.path.join(hd_dir, fname)
            out_path = os.path.join(output_dir, fname) if output_dir else None
            futures[pool.submit(apply_chaikin_alpha, sd_path, hd_path, out_path)] = fname

        with tqdm(total=len(todo), unit='img', desc='Chaikin', ncols=80) as pbar:
            for f in as_completed(futures):
                fname = futures[f]
                ok, msg = f.result()
                results.append((fname, ok, msg))
                pbar.update(1)

    ok = sum(1 for _, o, _ in results if o)
    fail = sum(1 for _, o, _ in results if not o)
    print(f"\nDone: {ok} OK, {fail} failed / {len(todo)}")
    if fail:
        for fname, _, msg in results:
            if not msg.startswith("OK"):
                print(f"  {fname}: {msg}")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description='Chaikin alpha smoothing for HD assets')
    p.add_argument('mode', choices=['single', 'batch'])
    p.add_argument('sd_source', help='SD source path or directory')
    p.add_argument('hd_target', help='HD target path or directory')
    p.add_argument('--output', '-o', help='Output path (single) or directory (batch)')
    p.add_argument('--pattern', default=None, help='Filename pattern (batch)')
    p.add_argument('--workers', type=int, default=4, help='Parallel workers (batch)')
    args = p.parse_args()

    if args.mode == 'single':
        ok, msg = apply_chaikin_alpha(args.sd_source, args.hd_target, args.output)
        print(f"{'✓' if ok else '✗'} {os.path.basename(args.sd_source)}: {msg}")
    else:
        batch_process(args.sd_source, args.hd_target, args.output,
                      pattern=args.pattern, max_workers=args.workers)


if __name__ == '__main__':
    main()
