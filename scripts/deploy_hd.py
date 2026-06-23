#!/usr/bin/env python3
"""
Deploy upscaled assets to ScummVM HD directory.

Copies any upscaled files not already in the HD directory.
Uses robocopy on Windows (much faster on NAS), shutil.copy2 elsewhere.

Usage:
    python scripts/deploy_hd.py [--src DIR] [--dst DIR]
"""

import os
import shutil
import subprocess
import sys
import argparse

# Use paths.py for default directories
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import paths


def _robocopy(src, dst, pattern="*.png"):
    """Use Windows robocopy — single process, multi-threaded I/O, NAS-friendly."""
    # robocopy flags:
    #   /xo  — exclude older (don't re-copy existing)
    #   /njh — no job header
    #   /njs — no job summary
    #   /ndl — no directory listing
    #   /nc  — no class
    #   /ns  — no size
    #   /np  — no progress (%)
    #   /mt:4 — multi-thread with 4 threads
    result = subprocess.run(
        ["robocopy", src, dst, pattern, "//xo", "//njh", "//njs", "//ndl", "//nc", "//ns", "//np", "//mt:4"],
        capture_output=True, text=True, timeout=600,
    )
    # robocopy exit codes: 0=nothing copied, 1=files copied, 2+=extra files or errors
    copied = 0
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            try:
                copied = int(parts[1])
            except ValueError:
                pass
    return copied


def _shutil_copy(src, dst):
    """Fallback for non-Windows: scan + copy per file."""
    total = 0
    copied = 0
    with os.scandir(src) as it:
        for entry in it:
            if not entry.name.endswith('.png') or not entry.is_file():
                continue
            total += 1
            dst_path = os.path.join(dst, entry.name)
            if not os.path.exists(dst_path):
                shutil.copy2(entry.path, dst_path)
                copied += 1
    return total, copied


def main():
    parser = argparse.ArgumentParser(description='Deploy HD assets')
    parser.add_argument('--src', default=paths.UPSCALED_COSTUMES)
    parser.add_argument('--dst', default=paths.HD_COSTUMES)
    args = parser.parse_args()

    if not os.path.isdir(args.src):
        print(f'Source not found: {args.src}')
        return

    os.makedirs(args.dst, exist_ok=True)

    # ── Windows → robocopy (multi-threaded, handles NAS well) ──
    if os.name == 'nt':
        # First try robocopy
        try:
            copied = _robocopy(args.src, args.dst)
            print(f'Deployed (robocopy): ~{copied} files → {args.dst}')
            return
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f'robocopy failed ({e}), falling back to shutil...')
            pass

    # ── Fallback: shutil.copy2 per file ──
    total, copied = _shutil_copy(args.src, args.dst)
    print(f'Deployed: {total} total, {copied} newly copied → {args.dst}')


if __name__ == '__main__':
    main()
