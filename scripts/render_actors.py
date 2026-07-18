#!/usr/bin/env python3
"""Convert 8-bit palette-indexed virtual screen dump to PNG for each actor."""
import os, struct, zlib, subprocess

LOGS = '/opt/data/local/logs'
OUT = '/opt/data/local/scummvm-build/sd_costumes'
os.makedirs(OUT, exist_ok=True)

# Load palette
palette = []
with open(f'{LOGS}/hd_dump_palette.txt') as f:
    for line in f:
        parts = line.split()
        if len(parts) >= 4:
            idx, r, g, b = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            palette.append((r, g, b))

print(f"Palette: {len(palette)} colors")

# Load virtual screen (640x480, 1 byte per pixel)
w, h = 640, 480
with open(f'{LOGS}/hd_dump_virtual_screen.raw', 'rb') as f:
    vs_data = f.read()

print(f"Virtual screen: {len(vs_data)} bytes, expected {w*h}")

# Write PNG helper
def write_png(path, w, h, rgb_data):
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    raw_filtered = bytearray()
    for y in range(h):
        raw_filtered.append(0)
        raw_filtered.extend(rgb_data[y * w * 3:(y + 1) * w * 3])
    compressed = zlib.compress(bytes(raw_filtered), 1)
    with open(path, 'wb') as f:
        f.write(sig)
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', compressed))
        f.write(chunk(b'IEND', b''))

# Save full screen
rgb_full = bytearray()
for py in range(h):
    for px in range(w):
        idx = py * w + px
        if idx < len(vs_data):
            p = vs_data[idx]
            r, g, b = palette[p] if p < len(palette) else (0, 0, 0)
        else:
            r, g, b = 0, 0, 0
        rgb_full.extend([r, g, b])

write_png(f'{OUT}/full_screen.png', w, h, bytes(rgb_full))
print(f"Full screen: {OUT}/full_screen.png")

# Actor positions from debug (at frame 30):
# Actor 1: costume=0002, pos=(320,427) — Guybrush
# Actor 2: costume=0025, pos=(0,381) 
# Actor 11: costume=0028, pos=(0,381)
# Actor 12: costume=0026, pos=(0,380)

# Crop each actor with generous bounding box
actors = [
    (1, '0002', 320, 427),
    (2, '0025', 0, 381),
    (11, '0028', 0, 381),
    (12, '0026', 0, 380),
]

for aid, akos, ax, ay in actors:
    # Crop 200x200 around actor position
    crop_w, crop_h = 200, 200
    x1 = max(0, ax - crop_w // 2)
    y1 = max(0, ay - crop_h // 2)
    x2 = min(w, x1 + crop_w)
    y2 = min(h, y1 + crop_h)
    
    cw = x2 - x1
    ch = y2 - y1
    
    rgb_crop = bytearray()
    for py in range(y1, y2):
        for px in range(x1, x2):
            idx = py * w + px
            if idx < len(vs_data):
                p = vs_data[idx]
                r, g, b = palette[p] if p < len(palette) else (0, 0, 0)
            else:
                r, g, b = 0, 0, 0
            rgb_crop.extend([r, g, b])
    
    png_path = f'{OUT}/actor_{aid}_akos_{akos}.png'
    write_png(png_path, cw, ch, bytes(rgb_crop))
    print(f"Actor {aid} (AKOS {akos}): {png_path} ({cw}x{ch})")
