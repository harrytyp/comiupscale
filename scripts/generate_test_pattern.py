#!/usr/bin/env python3
"""Generate a 2560x1920 test pattern PNG for HD background quality testing."""

from PIL import Image
import struct

W, H = 2560, 1920
img = Image.new('RGB', (W, H))
px = img.load()

# 1. Fine checkerboard in top-left 256x256 region (1px and 2px patterns)
# This will show if any downscaling is happening — 1px checkerboard
# would blur to gray if resolution is halved.
for y in range(256):
    for x in range(256):
        if (x + y) % 2 == 0:
            px[x, y] = (255, 255, 255)  # white
        else:
            px[x, y] = (0, 0, 0)        # black

# 2px checkerboard (256-512)
for y in range(256):
    for x in range(256, 512):
        if ((x // 2) + (y // 2)) % 2 == 0:
            px[x, y] = (255, 255, 255)
        else:
            px[x, y] = (0, 0, 0)

# 4px checkerboard (512-768)
for y in range(256):
    for x in range(512, 768):
        if ((x // 4) + (y // 4)) % 2 == 0:
            px[x, y] = (255, 255, 255)
        else:
            px[x, y] = (0, 0, 0)

# 8px checkerboard (768-1024)
for y in range(256):
    for x in range(768, 1024):
        if ((x // 8) + (y // 8)) % 2 == 0:
            px[x, y] = (255, 255, 255)
        else:
            px[x, y] = (0, 0, 0)

# 2. Color bars across top (y=256-512), full height bars
bar_w = W // 7
colors = [
    (255, 0, 0),     # Red
    (0, 255, 0),     # Green
    (0, 0, 255),     # Blue
    (255, 255, 0),   # Yellow
    (0, 255, 255),   # Cyan
    (255, 0, 255),   # Magenta
    (255, 255, 255), # White
]
for i, c in enumerate(colors):
    for x in range(bar_w * i, bar_w * (i + 1)):
        for y_ in range(256, 512):
            px[x, y_] = c

# 3. Smooth 24-bit gradient (y=512-768)
for y in range(512, 768):
    for x in range(W):
        r = (x * 255) // W
        g = (y * 255) // H
        b = ((x + y) * 255) // (W + H) if (x + y) > 0 else 0
        px[x, y] = (r, g, b)

# 4. Numerical position markers at multiples of 100px (y=768-800)
for y in range(768, 800):
    for mx in range(0, W, 100):
        px[mx, y] = (255, 255, 0)
        if mx + 1 < W:
            px[mx + 1, y] = (255, 255, 0)

# 5. Checkerboard at native game resolution (would be 640x480 if
# downscaled). These large 20px checks = 5px at 640x480 — easy to
# verify if the image is being rendered at native 640x480.
for y in range(800, 1280):
    for x in range(0, 1280):
        if ((x // 20) + (y // 20)) % 2 == 0:
            px[x, y] = (255, 255, 255)
        else:
            px[x, y] = (0, 0, 0)

# 6. Pure red (255,0,0) fill in 1536-1792, y=800-1280
for y in range(800, 1280):
    for x in range(1536, 1792):
        px[x, y] = (255, 0, 0)

# 7. Bottom area: ultra-fine alternating vertical lines (y=1280-1920)
# 1-pixel wide lines of R, G, B alternating
for y in range(1280, 1600):
    for x in range(W):
        if x % 3 == 0:
            px[x, y] = (255, 0, 0)
        elif x % 3 == 1:
            px[x, y] = (0, 255, 0)
        else:
            px[x, y] = (0, 0, 255)

# 8. Very bottom: alternating pixel columns (y=1600-1920)
# Every other column is 50% gray, the other 75% gray
# This is the ULTIMATE test for full-resolution rendering
for y in range(1600, 1920):
    for x in range(W):
        if x % 2 == 0:
            px[x, y] = (128, 128, 128)
        else:
            px[x, y] = (192, 192, 192)

img.save('test_pattern_2560x1920.png')
print(f"Generated test_pattern_2560x1920.png ({W}x{H})")
