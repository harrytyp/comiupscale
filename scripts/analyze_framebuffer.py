#!/usr/bin/env python3
"""Analyze the framebuffer dump to find actual dimensions and compare with original."""

import struct
from PIL import Image

DUMP = r"C:\Users\go75bel\scummvm-fork\hd_fb_dump.raw"
PNG = r"Z:\Projekte\COMI-Upscaled\ScummVM\monkey3\hd\bg_0087.png"

with open(DUMP, "rb") as f:
    raw = f.read()

n = len(raw)
print(f"Total bytes: {n}")
print(f"Bytes per pixel: 4 (RGBA)")
pixels_4bpp = n // 4
print(f"Pixel count (4bpp): {pixels_4bpp}")
print(f"Bytes per pixel: 3 (RGB)")
pixels_3bpp = n // 3
print(f"Pixel count (3bpp): {pixels_3bpp}")
print()

# Try 4 bytes per pixel (RGBA)
print("=== 4 BPP candidates ===")
for w in range(1, 5000):
    if n % (w * 4) == 0:
        h = n // (w * 4)
        ratio = w / h if h > 0 else 0
        if 200 <= h <= 4000 and 0.5 <= ratio <= 3.0:
            print(f"  {w} x {h} = {w*h} px (ratio {ratio:.3f})")

# Try reading the dump with the most likely size
# Let me find the size that gives the most coherent image
# by checking if pixels at the left edge match expected values
print("\n=== Pixel analysis ===")

# For room 87, the left edge should have colored pixels (not black)
# Try to find correct dimensions by checking horizontal coherence
best_dim = None
best_score = 0
for w in range(400, 2000):
    if n % (w * 4) == 0:
        h = n // (w * 4)
        if h < 200 or h > 2000:
            continue
        # Check pixel coherence: adjacent pixels should be similar
        # (real images have spatial coherence)
        score = 0
        try:
            for y in range(0, min(h, 100), 5):
                for x in range(0, min(w-5, 100), 5):
                    off1 = (y * w + x) * 4
                    off2 = (y * w + x + 1) * 4
                    if off2 + 3 < len(raw):
                        # Check if adjacent pixels have similar values
                        diff = sum(abs(raw[off1+i] - raw[off2+i]) for i in range(3))
                        score += max(0, 100 - diff)  # Higher score = more similar
        except:
            pass
        if score > best_score:
            best_score = score
            best_dim = (w, h)

if best_dim:
    w, h = best_dim
    print(f"\nBest guess: {w} x {h} (coherence score {best_score})")
    
    # Read with this size
    img = Image.frombytes("RGBA", (w, h), raw, "raw", ("RGBA", 0, 1))
    img_rgb = img.convert("RGB")
    
    print(f"Pixel (0,0): {img_rgb.getpixel((0,0))}")
    print(f"Pixel (100,100): {img_rgb.getpixel((100,100))}")
    print(f"Pixel (w//2,h//2): {img_rgb.getpixel((w//2,h//2))}")
    
    # Save as PNG for visual inspection
    img.save("hd_fb_dump_parsed.png")
    print(f"\nSaved to hd_fb_dump_parsed.png")
    
    # Compare with original if sizes match
    orig = Image.open(PNG).convert("RGB")
    ow, oh = orig.size
    print(f"\nOriginal: {ow} x {oh}")
    if w == ow and h == oh:
        diff = 0
        total = 0
        for y in range(0, h, 10):
            for x in range(0, w, 10):
                total += 1
                if img_rgb.getpixel((x,y)) != orig.getpixel((x,y)):
                    diff += 1
        print(f"Pixel diff: {diff}/{total} ({(1-diff/total)*100:.1f}% match)")
    else:
        # Scale original to match dump size for comparison
        orig_resized = orig.resize((w, h), Image.NEAREST)
        diff = 0
        total = 0
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                total += 1
                if img_rgb.getpixel((x,y)) != orig_resized.getpixel((x,y)):
                    diff += 1
        print(f"Pixel diff vs nearest-neighbor scaled original: {diff}/{total}")
        if diff == 0:
            print("100% MATCH with nearest-neighbor downscale!")
