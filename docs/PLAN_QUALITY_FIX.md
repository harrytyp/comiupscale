# HD Quality — Root Cause & Solution Plan

## Problem (Confirmed)
Monkey Island 3 patched with 4K RealESRGAN-upscaled textures. In ScummVM,
the images look visibly worse than in Windows Photo Viewer — artifacts and
aliasing at edges, especially at non-integer window sizes. Happens in both
OpenGL and SDL backends, both when upscaling AND downscaling.

## Root Cause
ScummVM only uses **bilinear filtering** or **nearest neighbor** for texture
resampling. Both produce artifacts with already-high-resolution assets:

- **Nearest neighbor**: non-uniform texel picking at non-1:1 ratios → aliasing
- **Bilinear**: blurs details, creates shimmering at edges

Windows Photo Viewer uses a fundamentally better pipeline:
- **Fant/Area Sampling** when downscaling — all affected source pixels are
  weighted, not just 2×2 or 1 texel
- **Subpixel-accurate anti-aliasing** via Direct2D for final compositing
- **GPU-accelerated compositing** via DWM/DXGI with proper mip-mapping

## Solution (Two Parts)

### Part 1 — Downsampling Quality (GLSL Shader)
Implement a **Lanczos** or **Bicubic** downsampling shader as a `.glslp`
preset. This replaces bilinear filtering during downscaling with proper
area sampling.

Reference: existing xBRZ shaders in `dists/engine-data/shaders/` in the
ScummVM source tree.

Implementation:
- Pass texel size as a uniform so the shader computes the correct
  sampling window
- Ensure the shader path activates during downsampling too (currently
  the pipeline is mainly designed for upscaling via libretro shaders)

### Part 2 — Subpixel Anti-Aliasing for Final Blit
Add subpixel-accurate anti-aliasing during the final compositing step
(texture → screen).

- **OpenGL path**: Use `textureGrad()` instead of `texture()` in the
  fragment shader, so the GPU computes correct mip gradients based on
  screen-space derivatives
- **Windows-only alternative** (more work): Use Direct2D instead of
  OpenGL for the final blit, which gives hardware-accelerated
  subpixel AA and proper gamma handling via DXGI

## Entry Points in ScummVM Code
- **Shader logic**: `dists/engine-data/shaders/`
- **OpenGL rendering**: `backends/graphics/openglsdl/`
- **Software scaler (CPU alternative)**: `graphics/scalerplugin.cpp`
- **Libretro pipeline**: `backends/graphics/opengl/pipelines/libretro.cpp`
- **Texture class**: `graphics/opengl/texture.h`
- **OpenGL graphics manager**: `backends/graphics/opengl/opengl-graphics.cpp`

## Current State (as of last session)

### What's Proven Working
- `_hdBackgroundSurface` is **100% pixel-perfect** (pixel dump vs PNG match)
- OpenGL backend is active with **GL_NEAREST** (no bilinear blur)
- Pipeline bypasses the software scaler (direct texture upload)
- Texture format is correct (RGBA8888, full 24-bit color)

### What Was Being Debugged
- Why the quality is CONSTANT across display sizes (same on 2560×1440
  and 1280×800)
- Why quality only improves when window is STRETCHED LARGER than intended
- Hypothesis: sRGB gamma mismatch (PNG is gamma-encoded, OpenGL renders linear)
- **NEW UNDERSTANDING**: The real issue is inadequate texture resampling —
  nearest neighbor at non-1:1 ratios creates aliasing, and the OpenGL
  pipeline has no proper downsampling shader

## Key Files
- `/z/Projekte/COMI-Upscaled/HD_QUALITY_ANALYSIS.md` — full analysis history
- `/z/Projekte/COMI-Upscaled/scripts/` — test patterns + analysis tools
- `/c/Users/go75bel/scummvm-fork/` — ScummVM fork source
- `/z/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/` — 4K background PNGs
