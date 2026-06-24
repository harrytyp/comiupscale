#!/usr/bin/env python3
"""
SD vs HD Diff Analyzer — reads raw composite files and produces a visual diff report.

Reads:
  hd_dump_NN_sdcomposite.raw  (SD-only, palette-mapped 8-bit scaled up)
  hd_dump_NN_diff.raw         (red = changed pixels, gray = unchanged)

Produces:
  - Per-region diff analysis (background vs foreground)
  - Connected component analysis (which areas changed)
  - PNG visualization (if Pillow available)
"""

import struct
import sys
import os
import math


def load_raw_rgba(path, width, height):
    """Load a raw RGBA file (4 bytes per pixel, row by row)."""
    with open(path, 'rb') as f:
        data = f.read()
    expected = width * height * 4
    if len(data) < expected:
        print(f"  WARNING: {path} too small ({len(data)} < {expected})")
        return None
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            offset = (y * width + x) * 4
            r, g, b, a = data[offset], data[offset+1], data[offset+2], data[offset+3]
            row.append((r, g, b, a))
        pixels.append(row)
    return pixels


def analyze_diff(diff_path, sd_path, width, height):
    """Analyze the diff between SD and HD composites."""
    diff = load_raw_rgba(diff_path, width, height)
    sd = load_raw_rgba(sd_path, width, height)
    
    if diff is None or sd is None:
        return None
    
    # Count red pixels (changed) vs gray pixels (unchanged)
    red_count = 0
    gray_count = 0
    total = width * height
    
    # Region analysis (split into 4x4 grid)
    grid_w, grid_h = 4, 4
    cell_w = width // grid_w
    cell_h = height // grid_h
    grid_diff = [[0] * grid_w for _ in range(grid_h)]
    grid_total = [[0] * grid_w for _ in range(grid_h)]
    
    # Bounding box of all changed pixels
    min_x, min_y = width, height
    max_x, max_y = 0, 0
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = diff[y][x]
            gx, gy = min(x // cell_w, grid_w-1), min(y // cell_h, grid_h-1)
            grid_total[gy][gx] += 1
            if r > 200 and g < 50 and b < 50:  # red = changed
                red_count += 1
                grid_diff[gy][gx] += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
            else:
                gray_count += 1
    
    return {
        'total': total,
        'changed': red_count,
        'unchanged': gray_count,
        'pct': red_count * 100.0 / total,
        'bbox': (min_x, min_y, max_x, max_y) if red_count > 0 else None,
        'grid': grid_diff,
        'grid_total': grid_total,
    }


def print_report(frame_num, result, width, height):
    """Print a human-readable diff report."""
    if result is None:
        print(f"  Frame {frame_num}: KEINE DATEN")
        return
    
    print(f"\n{'='*60}")
    print(f"  SD vs HD DIFF: Frame {frame_num} ({width}x{height})")
    print(f"{'='*60}")
    print(f"\n  Geänderte Pixel: {result['changed']:,}/{result['total']:,} ({result['pct']:.1f}%)")
    
    if result['bbox']:
        bx0, by0, bx1, by1 = result['bbox']
        print(f"  Bounding Box:    ({bx0},{by0}) → ({bx1},{by1}) [{bx1-bx0}x{by1-by0}]")
    
    # Grid analysis
    print(f"\n  ┌─────────────────────────────────────────────┐")
    print(f"  │ Diff-Verteilung (4×4 Grid)                  │")
    print(f"  │ Rot = geändert, Grau = unverändert           │")
    print(f"  ├─────────────────────────────────────────────┤")
    for gy in range(4):
        row = "  │ "
        for gx in range(4):
            diff_count = result['grid'][gy][gx]
            total = result['grid_total'][gy][gx]
            pct = diff_count * 100.0 / total if total > 0 else 0
            if pct > 50:
                row += "███ "
            elif pct > 20:
                row += "▓▓▓ "
            elif pct > 5:
                row += "░░░ "
            else:
                row += "··· "
        row += "│"
        print(row)
    print(f"  └─────────────────────────────────────────────┘")
    print(f"  ███ >50%  ▓▓▓ >20%  ░░░ >5%  ··· <5%")
    
    # Interpretation
    print(f"\n  ── Interpretation ──")
    top_pct = sum(result['grid'][0][gx] for gx in range(4)) / max(1, sum(result['grid_total'][0][gx] for gx in range(4))) * 100
    mid_pct = sum(result['grid'][1][gx] + result['grid'][2][gx] for gx in range(4)) / max(1, sum(result['grid_total'][1][gx] + result['grid_total'][2][gx] for gx in range(4))) * 100
    bot_pct = sum(result['grid'][3][gx] for gx in range(4)) / max(1, sum(result['grid_total'][3][gx] for gx in range(4))) * 100
    
    if top_pct > 5:
        print(f"  • Oben ({top_pct:.1f}%): HD-Hintergrund aktiv (Top 25%)")
    if mid_pct > 5:
        print(f"  • Mitte ({mid_pct:.1f}%): HD-Objekte/Costumes aktiv (Mitte 50%)")
    if bot_pct > 5:
        print(f"  • Unten ({bot_pct:.1f}%): HD-UI/Text aktiv (Untere 25%)")
    
    if result['pct'] < 1:
        print(f"  ⚠️  SEHR WENIGE Änderungen — HD-Pipeline bringt kaum Unterschied!")
    elif result['pct'] > 80:
        print(f"  ✅ Starke HD-Wirkung — fast alles geändert")
    else:
        print(f"  📊 Moderate HD-Wirkung — {result['pct']:.1f}% der Pixel geändert")


def save_png(pixels, path, width, height):
    """Save as PNG using Pillow if available."""
    try:
        from PIL import Image
        img = Image.new('RGBA', (width, height))
        for y in range(height):
            for x in range(width):
                img.putpixel((x, y), pixels[y][x])
        img.save(path)
        print(f"  PNG gespeichert: {path}")
        return True
    except ImportError:
        print(f"  (Pillow nicht verfügbar — PNG-Speicherung übersprungen)")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sd_vs_hd_diff.py <frame_number> [width] [height]")
        print("       python3 sd_vs_hd_diff.py 30")
        print("       python3 sd_vs_hd_diff.py all")
        sys.exit(1)
    
    logdir = "logs"
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 2560
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 1920
    
    if sys.argv[1] == "all":
        # Find all diff files
        frames = []
        for f in os.listdir(logdir):
            if f.endswith("_diff.raw"):
                m = f.replace("hd_dump_", "").replace("_diff.raw", "")
                try:
                    frames.append(int(m))
                except ValueError:
                    pass
        frames.sort()
    else:
        frames = [int(sys.argv[1])]
    
    for frame_num in frames:
        diff_path = os.path.join(logdir, f"hd_dump_{frame_num}_diff.raw")
        sd_path = os.path.join(logdir, f"hd_dump_{frame_num}_sdcomposite.raw")
        
        if not os.path.exists(diff_path):
            print(f"Frame {frame_num}: {diff_path} nicht gefunden")
            continue
        
        result = analyze_diff(diff_path, sd_path, width, height)
        print_report(frame_num, result, width, height)
        
        # Save PNG visualization
        if result:
            diff = load_raw_rgba(diff_path, width, height)
            if diff:
                save_png(diff, os.path.join(logdir, f"hd_dump_{frame_num}_diff.png"), width, height)
