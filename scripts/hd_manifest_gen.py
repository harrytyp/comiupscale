#!/usr/bin/env python3
"""Generate hd_manifest.json from extracted COMI backgrounds.

Scans the extracted backgrounds directory and produces a manifest
that maps room IDs to their HD (4x) dimensions.

Usage:
    python scripts/hd_manifest_gen.py [--bg-dir DIR] [--hd-dir DIR] [--output FILE]
"""

from PIL import Image
import argparse
import json
import os
import re

def extract_room_id(filename):
    """Extract room ID from filename like '0001_logo.png' → '0001'"""
    m = re.match(r'(\d+)_', filename)
    return m.group(1) if m else None

def main():
    parser = argparse.ArgumentParser(description='Generate HD manifest for COMI ScummVM fork')
    parser.add_argument('--bg-dir', default='CMI UPSCALED/extracted/COMI/IMAGES/backgrounds',
                        help='Source background directory (original PNGs)')
    parser.add_argument('--hd-dir', default='CMI UPSCALED/hd/backgrounds',
                        help='Target HD background directory (4x PNGs)')
    parser.add_argument('--output', default='hd_manifest.json',
                        help='Output manifest path')
    args = parser.parse_args()

    bg_dir = os.path.abspath(args.bg_dir)
    hd_dir = args.hd_dir.replace('\\', '/')
    
    if not os.path.isdir(bg_dir):
        print(f"Error: background directory not found: {bg_dir}")
        return 1

    backgrounds = {}
    for f in sorted(os.listdir(bg_dir)):
        if not f.lower().endswith('.png'):
            continue
        room_id = extract_room_id(f)
        if not room_id:
            continue
        im = Image.open(os.path.join(bg_dir, f))
        w, h = im.size
        backgrounds[room_id] = {
            "file": f"{hd_dir}/bg_{room_id}.png",
            "w": w * 4,
            "h": h * 4
        }

    manifest = {
        "version": 1,
        "engine": "scumm",
        "game": "monkey3",
        "scale": 4,
        "asset_dirs": {
            "backgrounds": hd_dir,
            "objects": "CMI UPSCALED/hd/objects",
            "costumes": "CMI UPSCALED/hd/costumes",
            "fonts": "CMI UPSCALED/hd/fonts",
            "cutscenes": "CMI UPSCALED/hd/cutscenes"
        },
        "backgrounds": backgrounds,
        "metadata": {
            "upscale_model": "realesrgan-x4plus-anime",
            "upscale_by": "RealESRGAN-NCNN-Vulkan v0.2.0",
            "created": "2026-05-23",
            "source_game": "Curse of Monkey Island (COMI.LA0/1/2)",
            "total_rooms": len(backgrounds)
        }
    }

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated manifest with {len(backgrounds)} rooms → {output_path}")
    print(f"HD backgrounds directory: {hd_dir}")
    return 0

if __name__ == '__main__':
    exit(main())
