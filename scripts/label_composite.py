#!/usr/bin/env python3
"""Render SD composite with actor positions marked using ffmpeg drawbox."""
import subprocess, os

RAW = '/opt/data/local/logs/hd_dump_120_sdcomposite.raw'
OUT = '/opt/data/local/scummvm-build/sd_composite_labeled.jpg'
PPM = '/tmp/sd_comp_label.ppm'

w, h = 2560, 1920
bpp = 4

with open(RAW, 'rb') as f:
    raw = f.read()

# Create PPM
scale = 2
sw, sh = w // scale, h // scale
with open(PPM, 'wb') as f:
    f.write(f'P6\n{sw} {sh}\n255\n'.encode())
    for y in range(0, h, scale):
        for x in range(0, w, scale):
            di = (y * w + x) * bpp
            f.write(raw[di:di+3])

print(f"PPM: {sw}x{sh}")

# Actor positions at half res (scale=2)
# Actor 1: costume=0002, pos=(320,427) HD=(1280,1708) half=(640,854)
# Actor 2: costume=0025, pos=(0,381) → half=(0,762)
# Actor 11: costume=0028, pos=(0,381) → half=(0,762)  
# Actor 12: costume=0026, pos=(0,380) → half=(0,760)

actors = [
    (1, 640, 854, 'red'),
    (2, 0, 762, 'green'),
    (11, 0, 762, 'blue'),
    (12, 0, 760, 'yellow'),
]

# Use ffmpeg drawbox to mark actors
filters = []
for aid, ax, ay, color in actors:
    box = 80  # half-size in half-res
    x1 = max(0, ax - box)
    y1 = max(0, ay - box)
    w_box = box * 2
    h_box = box * 2
    filters.append(f"drawbox=x={x1}:y={y1}:w={w_box}:h={h_box}:color={color}@0.5:t=3")

# Add text labels
for aid, ax, ay, color in actors:
    filters.append(f"drawtext=text='Actor {aid}':x={ax-30}:y={ay-90}:fontsize=20:fontcolor={color}")

filter_str = ','.join(filters)

r = subprocess.run([
    'ffmpeg', '-y', '-i', PPM,
    '-vf', filter_str,
    '-q:v', '2', OUT
], capture_output=True, timeout=30)

if os.path.exists(OUT):
    print(f"Saved: {OUT} ({os.path.getsize(OUT):,} bytes)")
else:
    print(f"Failed: {r.stderr.decode()[:300]}")
