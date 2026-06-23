#!/usr/bin/env python3
"""
HD Rendering Diagnostics for COMI Upscaled.

Reads debug dump raw files written by the ScummVM fork and reports
on HD rendering health. Run after the game writes dumps (triggered
by hd_dump_frame=N in [comi] config).

Usage:
    python scripts/check_hd_dumps.py <dir-with-dumps>
    python scripts/check_hd_dumps.py .                     # current dir
"""

import os
import sys
import struct


def analyze_dump(path, label, expected_w, expected_h, bpp):
    """Check a raw dump file for basic sanity."""
    if not os.path.exists(path):
        return f"  MISS {label}: NOT FOUND at {path}"

    size = os.path.getsize(path)
    expected_size = expected_w * expected_h * bpp

    if size == 0:
        return f"  MISS {label}: EMPTY file"

    issues = []
    if size != expected_size:
        issues.append(f"wrong size: {size} (expected {expected_size})")
    
    # Read first and last few pixels
    with open(path, 'rb') as f:
        data = f.read()

    # Check if all pixels are identical (solid color = no data)
    sample = data[:min(256, len(data))]
    unique = len(set(sample))
    if unique <= 2:
        issues.append(f"all pixels same value ({unique} unique bytes in sample)")

    # Check for zero-only data
    non_zero = sum(1 for b in data[:10000] if b != 0)
    if non_zero == 0:
        issues.append("all zeros (no content)")

    status = "OK" if not issues else "WARN"
    details = ", ".join(issues) if issues else f"{expected_w}x{expected_h} {size} bytes OK"
    return f"  {status} {label}: {details}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_hd_dumps.py <dump-dir>")
        print("       python check_hd_dumps.py /z/Projekte/COMI-Upscaled")
        sys.exit(1)

    dump_dir = sys.argv[1]
    if not os.path.isdir(dump_dir):
        print(f"ERROR: directory not found: {dump_dir}")
        sys.exit(2)

    print(f"=== HD Dump Analysis: {dump_dir} ===\n")

    # Game resolution constants
    SD_W, SD_H = 640, 480
    HD_W, HD_H = 2560, 1920

    # Check which dump files exist
    dumps = {}
    for f in os.listdir(dump_dir):
        if f.startswith("hd_dump_") and f.endswith(".raw"):
            parts = f.replace("hd_dump_", "").replace(".raw", "").split("_", 1)
            if len(parts) == 2:
                room, kind = parts[0], parts[1]
                dumps[f"{room}_{kind}"] = os.path.join(dump_dir, f)

    if not dumps:
        print("  No hd_dump_*.raw files found.")
        print("  Enable hd_dump_frame=N in [comi] config to generate them.")
        sys.exit(0)

    # Group by room number
    rooms = {}
    for key, path in dumps.items():
        room = key.split("_")[0]
        if room not in rooms:
            rooms[room] = {}
        kind = key.split("_", 1)[1]
        rooms[room][kind] = path

    for room in sorted(rooms.keys()):
        print(f"--- Room {room} ---")
        kinds = rooms[room]
        
        if "composite" in kinds:
            print(analyze_dump(kinds["composite"], f"composite", HD_W, HD_H, 4))
        if "hdcomposite" in kinds:
            print(analyze_dump(kinds["hdcomposite"], f"hdcomposite", HD_W, HD_H, 4))
        if "clean" in kinds:
            print(analyze_dump(kinds["clean"], f"clean bg", SD_W, SD_H, 1))
        if "virtscr" in kinds:
            print(analyze_dump(kinds["virtscr"], f"virtscr", SD_W, SD_H, 1))
        if "valid" in kinds:
            print(analyze_dump(kinds["valid"], f"valid mask", SD_W, SD_H, 1))

        # Check state file
        state_path = os.path.join(dump_dir, f"hd_dump_{room}_state.txt")
        if os.path.exists(state_path):
            with open(state_path) as f:
                content = f.read()
            hd_line = [l for l in content.split("\n") if "hdScale" in l or "HD" in l]
            if hd_line:
                print(f"  state: {hd_line[0].strip()}")

        print()

    # Summary
    print("--- Summary ---")
    issues = []
    for room in sorted(rooms.keys()):
        kinds = rooms[room]
        for kind, path in kinds.items():
            if kind == "composite":
                size = os.path.getsize(path)
                if size < HD_W * HD_H * 4:
                    issues.append(f"Room {room}: composite too small ({size})")
                # Check if composite has content
                with open(path, 'rb') as f:
                    data = f.read(1024)  # first KB
                if all(b == 0 for b in data):
                    issues.append(f"Room {room}: composite is all zeros")

    if issues:
        print("WARN  Issues found:")
        for i in issues:
            print(f"    {i}")
    else:
        print("OK  All dumps look healthy")


if __name__ == "__main__":
    main()
