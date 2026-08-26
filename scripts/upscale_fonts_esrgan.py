#!/usr/bin/env python3
"""Upscale font sheets 4x with RealESRGAN (animevideov3) on CPU.

The font sheets from extract_all_raw.py are RGBA (glyph + transparent
background, 16x16 grid of 56x56-base cells, 896x896 total). RealESRGAN
works on RGB, so we upscale the RGB channels and keep the alpha channel
upscaled separately with NEAREST (alpha is a mask, no smoothing).

Usage:
  upscale_fonts_esrgan.py <src_dir> <dst_dir> <model.pth>
    src_dir: dir with FONT<N>/chars.png (pipeline output)
    dst_dir: output dir -> FONT<N>.NUT_chars.png (3584x3584 RGBA)
"""
import sys, os
from pathlib import Path


def main():
    src_dir, dst_dir, model_path = sys.argv[1], sys.argv[2], sys.argv[3]
    src_dir, dst_dir = Path(src_dir), Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    import torch
    from spandrel import ModelLoader
    from PIL import Image
    import numpy as np

    torch.set_num_threads(os.cpu_count() or 4)
    model = ModelLoader().load_from_file(model_path)
    model = model.cpu().eval()

    for font_dir in sorted(src_dir.glob('FONT*')):
        src = font_dir / 'chars.png'
        if not src.exists():
            print(f'skip {font_dir.name} (no chars.png)', flush=True)
            continue
        name = font_dir.name
        img = Image.open(src).convert('RGBA')
        rgb = img.convert('RGB')
        alpha = img.split()[3]

        print(f'Upscaling {name} ({rgb.size[0]}x{rgb.size[1]}) ...', flush=True)
        t = torch.from_numpy(np.array(rgb).transpose(2, 0, 1)).unsqueeze(0).float() / 255.0
        with torch.no_grad():
            out = model(t)
        out_rgb = (out.squeeze(0).clamp(0, 1).permute(1, 2, 0).numpy() * 255).astype(np.uint8)

        # Alpha upscaled with LANCZOS (smooth mask edges — NEAREST gives
        # hard pixel steps that look blocky on the glyph outlines)
        out_alpha = alpha.resize((rgb.size[0] * 4, rgb.size[1] * 4), Image.LANCZOS)

        out_img = Image.fromarray(out_rgb).convert('RGBA')
        out_img.putalpha(out_alpha)
        dst = dst_dir / f'{name}.NUT_chars.png'
        out_img.save(dst)
        print(f'  -> {dst} ({out_img.size[0]}x{out_img.size[1]})', flush=True)


if __name__ == '__main__':
    main()
