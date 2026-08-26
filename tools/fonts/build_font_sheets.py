#!/usr/bin/env python3
"""Build clean HD font sheets for COMI from the original NUT resources.

This is the ONE pipeline for fonts: NUT -> per-glyph bitmaps -> clean
HD sheets with alpha channel, uniform cell size, no checkerboard/magenta.

Output: <outdir>/FONT<N>.NUT_chars.png  (RGBA, 16x16 grid)
Cell size: CELL_W x CELL_H base pixels (default 32x48), glyph centered.
The engine (HdFontManager) then needs NO color filtering — just cut the
cell and blit, alpha already correct.

Usage:
    python3 build_font_sheets.py <resource_dir> <outdir> [--cell-w 32] [--cell-h 48] [--scale 4]
"""
import os, sys, argparse
import numpy as np
from PIL import Image

from nutcracker.smush import anim
from nutcracker.smush.decode import generate_frames, DECODE_FRAME_IMAGE
from nutcracker.graphics import image as nut_image

CELL_W_DEF = 32
CELL_H_DEF = 48


def extract_glyphs(nut_path):
    """Return list of (idx, pil_image, xoff, yoff) for each character."""
    root = anim.from_path(nut_path)
    header, frames = anim.parse(root)
    chars = [ctx.screen for ctx in generate_frames(header, frames, DECODE_FRAME_IMAGE)]
    glyphs = []
    for idx, (loc, im) in enumerate(chars):
        img = nut_image.convert_to_pil_image(im)
        glyphs.append((idx, img, loc.x1, loc.y1))
    return glyphs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('resource_dir')
    ap.add_argument('outdir')
    ap.add_argument('--cell-w', type=int, default=CELL_W_DEF)
    ap.add_argument('--cell-h', type=int, default=CELL_H_DEF)
    ap.add_argument('--scale', type=int, default=4)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    grid = 16
    cellW, cellH = args.cell_w, args.cell_h

    for fi in range(5):
        nut = os.path.join(args.resource_dir, f'FONT{fi}.NUT')
        if not os.path.exists(nut):
            continue
        glyphs = extract_glyphs(nut)
        # Sheet in HD: grid * cell * scale
        sheetW = grid * cellW * args.scale
        sheetH = grid * cellH * args.scale
        sheet = Image.new('RGBA', (sheetW, sheetH), (0, 0, 0, 0))

        for idx, img, xoff, yoff in glyphs:
            if idx >= grid * grid:
                continue
            # NUT glyphs are palette images; palette index 39 is the
            # official transparency color (decode_nut uses transparency=39).
            # Everything else is glyph ink. Convert to RGBA and build the
            # alpha mask from the palette index.
            if img.mode == 'P':
                palette = img.getpalette()
                # Build RGBA: index 39 -> alpha 0, others -> opaque
                rgba = img.convert('RGBA')
                pa = np.array(img)  # palette indices
                alpha = np.where(pa == 39, 0, 255).astype(np.uint8)
                r, g, b, a = rgba.split()
                img = Image.merge('RGBA', (r, g, b, Image.fromarray(alpha, 'L')))
            else:
                img = img.convert('RGBA')

            # Place in cell: crop glyph to its bounding box (no padding),
            # then 4x LANCZOS upscale to HD (smooth edges — the NUT glyphs
            # are 1x; nearest-neighbor gives hard pixel blocks that look
            # fat/blurry on screen).
            w, h = img.size
            # Auto-crop transparent borders
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            w, h = img.size
            # 4x lanczos upscale
            img = img.resize((w * args.scale, h * args.scale), Image.LANCZOS)
            # LEFT-ALIGN in cell (drawChar scans the real glyph width via
            # alpha; centering would misplace the scan). Vertical: center.
            row = idx // grid
            col = idx % grid
            cell_x = col * cellW * args.scale
            cell_y = row * cellH * args.scale
            px_off = cell_x + 2 * args.scale   # small left pad
            py_off = cell_y + (cellH * args.scale - img.size[1]) // 2
            sheet.paste(img, (px_off, py_off), img)

        out = os.path.join(args.outdir, f'FONT{fi}.NUT_chars.png')
        sheet.save(out)
        print(f'FONT{fi}: {len(glyphs)} glyphs -> {out} ({sheetW}x{sheetH})')


if __name__ == '__main__':
    main()
