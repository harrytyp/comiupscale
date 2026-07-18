#!/usr/bin/env python3
"""Convert SD composite raw RGBA dump to JPG for visual inspection."""
import subprocess, os

RAW = '/opt/data/local/logs/hd_dump_120_sdcomposite.raw'
OUT = '/opt/data/local/scummvm-build/sd_composite.jpg'

w, h = 2560, 1920
bpp = 4  # RGBA

with open(RAW, 'rb') as f:
    raw = f.read()

print(f"Raw: {len(raw):,} bytes, expected: {w*h*bpp:,}")

# Create downsampled PPM (skip every 4th pixel, extract RGB only)
scale = 4
sw, sh = w // scale, h // scale
ppm_path = '/tmp/sd_comp.ppm'
with open(ppm_path, 'wb') as f:
    f.write(f'P6\n{sw} {sh}\n255\n'.encode())
    for y in range(0, h, scale):
        for x in range(0, w, scale):
            di = (y * w + x) * bpp
            if di + 2 < len(raw):
                f.write(bytes([raw[di], raw[di+1], raw[di+2]]))
            else:
                f.write(b'\x00\x00\x00')

print(f"PPM: {sw}x{sh}")

r = subprocess.run(
    ['ffmpeg', '-y', '-i', ppm_path, '-q:v', '2', OUT],
    capture_output=True, timeout=30
)
if os.path.exists(OUT):
    print(f"Saved: {OUT} ({os.path.getsize(OUT):,} bytes)")
else:
    print(f"ffmpeg failed: {r.stderr.decode()[:300]}")
