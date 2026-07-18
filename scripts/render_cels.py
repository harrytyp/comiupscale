#!/usr/bin/env python3
"""Render HD costume PNGs with alpha onto a gray background for visual inspection."""
import struct, zlib, os

def read_png(path):
    with open(path, 'rb') as f:
        sig = f.read(8)
        idat_data = b''
        w, h, ct = 0, 0, 0
        while True:
            data = f.read(8)
            if len(data) < 8: break
            length = struct.unpack('>I', data[:4])[0]
            ctype = data[4:8].decode('ascii', errors='replace')
            chunk_data = f.read(length)
            crc = f.read(4)
            if ctype == 'IHDR':
                w, h, bd, ct = struct.unpack('>IIBB', chunk_data[:10])
            elif ctype == 'IDAT':
                idat_data += chunk_data
    raw = zlib.decompress(idat_data)
    return w, h, ct, raw

def render_with_bg(path, bg_color=(64, 64, 64)):
    w, h, ct, raw = read_png(path)
    bpp = 4 if ct == 6 else 3
    
    pixels = []
    for y in range(h):
        row_start = 1 + y * (1 + w * bpp)
        for x in range(w):
            px_start = row_start + x * bpp
            if px_start + bpp <= len(raw):
                r_val = raw[px_start]
                g_val = raw[px_start + 1]
                b_val = raw[px_start + 2]
                a = raw[px_start + 3] if bpp == 4 else 255
                alpha = a / 255.0
                fr = int(r_val * alpha + bg_color[0] * (1 - alpha))
                fg = int(g_val * alpha + bg_color[1] * (1 - alpha))
                fb = int(b_val * alpha + bg_color[2] * (1 - alpha))
                pixels.append((fr, fg, fb))
            else:
                pixels.append(bg_color)
    return w, h, pixels

def write_ppm(path, w, h, pixels):
    with open(path, 'wb') as out:
        out.write(f'P6\n{w} {h}\n255\n'.encode())
        for r, g, b in pixels:
            out.write(bytes([r, g, b]))

base = '/opt/data/local/scummvm-build/hd/costumes/'
out = '/opt/data/local/scummvm-build/hd/'

for frame in [22, 105, 188]:
    fname = f'LFLF_0001_AKOS_0002_aframe_{frame}.png'
    path = base + fname
    if os.path.exists(path):
        w, h, px = render_with_bg(path)
        # Count sprite pixels (not background)
        sprite = sum(1 for r, g, b in px if not (60 <= r <= 68 and 60 <= g <= 68 and 60 <= b <= 68))
        ppm_path = out + f'cel{frame}_on_gray.ppm'
        write_ppm(ppm_path, w, h, px)
        print(f"cel{frame}: {w}x{h}, sprite pixels: {sprite}/{w*h} ({100*sprite/(w*h):.1f}%), saved {ppm_path}")
    else:
        print(f"cel{frame}: NOT FOUND at {path}")
