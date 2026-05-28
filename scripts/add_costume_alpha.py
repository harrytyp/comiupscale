#!/usr/bin/env python3
"""
Alpha generator v4 — GPU-batched alpha mask compositing.

Three-phase approach:
  1. Scan originals → compute binary masks at original resolution (CPU)
  2. Batch-resize ALL masks as a single PyTorch tensor (GPU if available)
  3. Composite each HD image with its pre-resized mask (CPU I/O)

Phase 2 is the money shot: one torch.nn.functional.interpolate call
instead of 25K separate PIL resizes.

Usage:
    python scripts/add_costume_alpha.py [--workers 4] [--no-gpu]
"""

import os
import sys
import argparse
import tempfile
import pickle
from functools import partial
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from PIL import Image
import numpy as np
from tqdm import tqdm

SRC = 'Z:/Projekte/COMI-Upscaled/CMI UPSCALED/extracted/COMI/costumes'
HD = 'Z:/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/costumes'


# ── Phase 1: Scan originals → binary masks ──────────

def scan_mask(fname, src_dir):
    """Read original PNG, compute binary mask + original size.
    Returns (fname, mask_bytes, orig_size, bg_idx) or None if skipped."""
    src_path = os.path.join(src_dir, fname)
    try:
        orig = Image.open(src_path)
        if orig.mode != 'P':
            return None
        orig_arr = np.array(orig)
        border = np.concatenate([orig_arr[0, :], orig_arr[-1, :],
                                 orig_arr[:, 0], orig_arr[:, -1]])
        unique, counts = np.unique(border, return_counts=True)
        bg_idx = int(unique[np.argmax(counts)])
        mask = (orig_arr != bg_idx).astype(np.uint8)
        return (fname, mask.tobytes(), orig.size, bg_idx)
    except Exception as e:
        return None


# ── Phase 2: GPU-batched mask resize ────────────────

def batch_resize_masks(mask_records, device='cpu'):
    """Resize all masks 4x in one batched GPU operation.

    mask_records: list of (fname, mask_bytes, orig_size, bg_idx)
    Returns: dict of {fname: resized_mask_array}
    """
    import torch
    import torch.nn.functional as F

    # Build batched tensor
    batch_tensors = []
    fnames = []
    orig_sizes = {}

    for fname, mask_bytes, orig_size, bg_idx in mask_records:
        w, h = orig_size
        mask = np.frombuffer(mask_bytes, dtype=np.uint8).reshape(h, w)
        # Normalize to float [0, 1] for interpolate
        mask_t = torch.from_numpy(mask.astype(np.float32)).unsqueeze(0).unsqueeze(0)
        batch_tensors.append(mask_t)
        fnames.append(fname)
        orig_sizes[fname] = (w, h, bg_idx)

    if not batch_tensors:
        return {}, {}

    # Stack: (N, 1, H, W) — note: different H,W per image!
    # F.interpolate requires same H,W, so we pad to max dimensions or
    # process in size groups. Simpler: pad all to max W x max H.
    max_w = max(s[0] for s in orig_sizes.values())
    max_h = max(s[1] for s in orig_sizes.values())

    print(f'  Batched tensor: {len(batch_tensors)} masks, max size {max_w}x{max_h}')

    padded = []
    for t in batch_tensors:
        _, _, h, w = t.shape
        pad_h = max_h - h
        pad_w = max_w - w
        # Pad (left, right, top, bottom) — note zero padding = transparent
        padded.append(F.pad(t, (0, pad_w, 0, pad_h), mode='constant', value=0))

    big_tensor = torch.cat(padded, dim=0)  # (N, 1, max_h, max_w)
    big_tensor = big_tensor.to(device)

    # Single batched resize
    big_resized = F.interpolate(
        big_tensor, size=(max_h * 4, max_w * 4),
        mode='bilinear', align_corners=False,
    )  # (N, 1, max_h*4, max_w*4)

    # Un-pad and convert back
    results = {}
    hd_sizes = {}
    for i, fname in enumerate(fnames):
        w, h, bg_idx = orig_sizes[fname]
        mask_slice = big_resized[i, 0, :h * 4, :w * 4]
        # Threshold back to uint8 0-255
        mask_np = (mask_slice.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        results[fname] = mask_np
        hd_sizes[fname] = (w * 4, h * 4)

    return results, hd_sizes


# ── Phase 3: Composite HD images (parallel I/O) ─────

def composite_single(args):
    """Read HD file, apply pre-computed mask, save. Returns bool."""
    fname, mask_arr, hd_dir = args
    hd_path = os.path.join(hd_dir, fname)
    if not os.path.exists(hd_path):
        return False
    try:
        hd = Image.open(hd_path)
        hd_rgb = np.array(hd.convert('RGB'))
        # Ensure mask matches HD dimensions (may be slightly off due to rounding)
        mh, mw = mask_arr.shape
        if (mw, mh) != hd.size:
            # Resize mask to match
            from PIL import Image as _PIL
            mask_img = _PIL.fromarray(mask_arr, mode='L')
            mask_arr = np.array(mask_img.resize(hd.size, _PIL.BILINEAR))

        hd_out = np.zeros((hd.size[1], hd.size[0], 4), dtype=np.uint8)
        hd_out[:, :, :3] = hd_rgb
        hd_out[:, :, 3] = mask_arr
        Image.fromarray(hd_out, 'RGBA').save(hd_path)
        return True
    except Exception as e:
        return False


# ── Main ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='GPU-batched alpha fixup')
    parser.add_argument('--workers', type=int, default=4,
                        help='Workers for Phase 1+3 (default: 4)')
    parser.add_argument('--no-gpu', action='store_true',
                        help='Force CPU for Phase 2')
    parser.add_argument('--device', default='auto',
                        help='Torch device (auto/cpu/cuda/dml)')
    args = parser.parse_args()

    if not os.path.exists(SRC):
        print(f"Source not found: {SRC}")
        return
    os.makedirs(HD, exist_ok=True)

    # Resolve device
    device = 'cpu'
    if args.device == 'auto':
        try:
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
            # Try DirectML for AMD
            if device == 'cpu':
                try:
                    import torch_directml
                    device = torch_directml.device()
                    print(f'  Using DirectML: {device}')
                except ImportError:
                    pass
        except ImportError:
            pass
    else:
        device = args.device
    if args.no_gpu:
        device = 'cpu'

    print(f'Device: {device}')
    print()

    # ── Gather files (fast scandir) ──
    fnames = []
    with os.scandir(SRC) as it:
        for e in it:
            if e.name.endswith('.png') and e.is_file():
                fnames.append(e.name)

    total = len(fnames)
    print(f'Costume PNGs: {total}')

    # ── Phase 1: Scan original masks (parallel CPU) ──
    print('Phase 1: Scanning originals...')
    mask_records = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(scan_mask, f, SRC): f for f in fnames}
        with tqdm(total=total, unit='img', desc='  Scanning',
                  ncols=80) as pbar:
            for f in as_completed(futures):
                result = f.result()
                if result:
                    mask_records.append(result)
                pbar.update(1)

    print(f'  Masks computed: {len(mask_records)}')
    print()

    # ── Phase 2: GPU-batched resize ──
    print('Phase 2: Batch resizing masks...')
    resized_masks, hd_sizes = batch_resize_masks(mask_records, device=device)
    print(f'  Masks resized: {len(resized_masks)}')
    print()

    # ── Phase 3: Composite (parallel I/O) ──
    print('Phase 3: Compositing HD images...')
    applied = 0
    composite_args = [(f, resized_masks[f], HD) for f in fnames if f in resized_masks]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(composite_single, a) for a in composite_args]
        with tqdm(total=len(composite_args), unit='img', desc='  Compositing',
                  ncols=80) as pbar:
            for f in as_completed(futures):
                if f.result():
                    applied += 1
                pbar.update(1)

    print()
    print(f'Costumes: {applied}/{total} alpha masks applied')
    print('Done')


if __name__ == '__main__':
    main()
