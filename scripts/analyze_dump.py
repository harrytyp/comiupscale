#!/usr/bin/env python3
"""Analyze the HD surface dump to determine rendering quality."""

import struct
import sys
from PIL import Image

DUMP = r"C:\Users\go75bel\scummvm-fork\hd_startup_dump.raw"
PNG = r"Z:\Projekte\COMI-Upscaled\test_pattern_2560x1920.png"

W, H = 2560, 1920

with open(DUMP, "rb") as f:
    raw = f.read()

expected_size = W * H * 4
print(f"Dump size: {len(raw)} bytes (expected {expected_size})")
if len(raw) != expected_size:
    print(f"ERROR: Size mismatch! Ratio: {len(raw) / expected_size:.4f}")
    # Try to guess real dimensions
    for w in [640, 800, 1024, 1280]:
        h_exp = len(raw) / (w * 4)
        if h_exp.is_integer():
            print(f"  Could be {w}x{int(h_exp)}")
    sys.exit(1)

# Convert to PIL Image for analysis
# The dump format is RGBA8888 [R, G, B, A] in memory
img = Image.frombytes("RGBA", (W, H), raw, "raw", ("RGBA", 0, 1))
img_rgb = img.convert("RGB")

# Load original PNG
orig = Image.open(PNG).convert("RGB")

print()
print("=== PIXEL-LEVEL ANALYSIS ===")

# 1. Check the checkerboard pattern at (0,0) - 1px black/white
# In a full-res render, pixel (0,0) should be white and (1,0) should be black
p00 = img_rgb.getpixel((0, 0))
p10 = img_rgb.getpixel((1, 0))
p01 = img_rgb.getpixel((1, 1))
print(f"1px checkerboard (0,0): {p00} (expect white=255,255,255)")
print(f"1px checkerboard (1,0): {p10} (expect black=0,0,0)")
print(f"1px checkerboard (1,1): {p01} (expect white=255,255,255)")
matches_1px = (p00 == (255, 255, 255) and p10 == (0, 0, 0) and p01 == (255, 255, 255))

# 2. Check color bars (y=300, full-width at red bar x=50)
red_bar = img_rgb.getpixel((50, 300))
green_bar = img_rgb.getpixel((400, 300))
blue_bar = img_rgb.getpixel((750, 300))
print(f"\nRed bar at x=50: {red_bar} (expect 255,0,0)")
print(f"Green bar at x=400: {green_bar} (expect 0,255,0)")
print(f"Blue bar at x=750: {blue_bar} (expect 0,0,255)")

# 3. Check gradient section (y=600, x=1280 should have ~(128, 235, 99))
grad = img_rgb.getpixel((1280, 600))
print(f"\nGradient at (1280,600): {grad}")

# 4. Check 1px vertical lines pattern (y=1400)
# Every third pixel should be R, G, B
vR = img_rgb.getpixel((0, 1400))
vG = img_rgb.getpixel((1, 1400))
vB = img_rgb.getpixel((2, 1400))
print(f"\n1px vertical lines at y=1400:")
print(f"  x=0: {vR} (expect 255,0,0)")
print(f"  x=1: {vG} (expect 0,255,0)")
print(f"  x=2: {vB} (expect 0,0,255)")

# 5. Check alternating pixel columns (y=1700)
# Even columns = 128,128,128, odd columns = 192,192,192
alt_even = img_rgb.getpixel((0, 1700))
alt_odd = img_rgb.getpixel((1, 1700))
print(f"\nAlternating pixel columns at y=1700:")
print(f"  x=0 (even): {alt_even} (expect 128,128,128)")
print(f"  x=1 (odd): {alt_odd} (expect 192,192,192)")

# 6. UNIQUE COLORS COUNT — a critical metric
# If the image is downscaled and then upscaled, unique colors drops massively
all_colors = set()
for y in range(0, H, 8):  # Sample every 8th row for speed
    for x in range(0, W, 8):  # Sample every 8th column
        all_colors.add(img_rgb.getpixel((x, y)))
print(f"\nSampled unique colors: {len(all_colors)} (sampled every 8th pixel)")

# Full check of alternating pixel region (y=1700-1720)
# Should have 2 unique grays: 128 and 192
grays = set()
for x in range(1600, 1700):
    grays.add(img_rgb.getpixel((x, 1700)))
print(f"Gray values in alternating region: {sorted(grays)} (expect 2: (128,128,128) and (192,192,192))")

print()
print("=== VERDICTS ===")
print(f"1px checkerboard: {'PASS' if matches_1px else 'FAIL'} (1px detail preserved)")
if alt_even == (128, 128, 128) and alt_odd == (192, 192, 192):
    print("Alternating pixel columns: PASS (single-pixel alternation works)")
else:
    print("Alternating pixel columns: FAIL (pixel-level precision lost)")
if vR == (255, 0, 0) and vG == (0, 255, 0) and vB == (0, 0, 255):
    print("Vertical 1px RGB lines: PASS")
else:
    print("Vertical 1px RGB lines: FAIL")

# Compare with original
diff = 0
total = 0
for y in range(0, H, 32):
    for x in range(0, W, 32):
        total += 1
        if img_rgb.getpixel((x, y)) != orig.getpixel((x, y)):
            diff += 1
print(f"\nPixel differences vs original (sampled every 32px): {diff}/{total}")
print(f"Match percentage: {(1 - diff/total)*100:.1f}%")
