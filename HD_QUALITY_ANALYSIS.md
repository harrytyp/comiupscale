# HD Background Quality Analysis

## Problem
The 2560×1920 RealESRGAN-upscaled PNG backgrounds look worse when displayed
in our ScummVM fork compared to viewing the same PNG in Windows Photo Viewer.
The image appears "blocky" / "oversharpened at edges" / lacking detail.

## What We've Verified (Proven Correct)

### 1. `_hdBackgroundSurface` is 100% Pixel-Perfect
We dumped `_hdBackgroundSurface` to a raw file and compared it pixel-by-pixel
with the original PNG. **100% match** — every pixel at full 2560×1920 RGBA
matches the original source PNG. The PNG decode + RGBA8888 conversion in
`hd_asset_manager.cpp` is flawless.

### 2. R/G/B Byte Order is Correct
Test patches (pure R, G, B blocks) render with correct color — no channel
swapping.

### 3. Smooth Gradient Shows No Banding
Full 24-bit color precision is maintained through the pipeline.

### 4. OpenGL Backend is Active (NOT SurfaceSDL)
Confirmed via `OGL-CR: w=2560 h=1920` debug output from
`OpenGLGraphicsManager::copyRectToScreen`. The SurfaceSDL backend patches
(HD texture bypass, scaler bypass) are in the WRONG code path — they don't
execute because the OpenGL backend is used instead.

### 5. GL_NEAREST Texture Filtering is Active
The OpenGL texture filter defaults to `GL_NEAREST` (line 40 of
`graphics/opengl/texture.cpp`). No linear filtering is applied unless
explicitly enabled via `kFeatureFilteringMode`.

### 6. OpenGL Pipeline Bypasses the Scaler
The OpenGL backend copies pixels directly to a texture via
`_gameScreen->copyRectToTexture()`. No intermediate `_hwScreen`, no scaler,
no `_tmpscreen`. The data goes straight: engine → CPU texture → OpenGL texture.

### 7. Texture Upload is Correct
`glTexSubImage2D` uploads the full 2560×1920 RGBA data to the OpenGL texture.
`Graphics::Surface::copyRectToTexture()` uses a single `memcpy` when pitch matches.

## Root Cause Not Yet Found

Despite all the above being verified, the visual quality still doesn't match
Windows Photo Viewer. Here's what we've learned about the gap:

### Window Size vs Texture Size Mismatch (Important Clue)
- On a 2560×1440 display: quality is subpar
- On a 1280×800 laptop display: quality looks the SAME (same level of blockiness)
- When STRETCHED across two displays (larger window): quality IMPROVES
- **Quality is independent of display resolution** — same at any screen size
- Quality ONLY improves when the window is LARGER than the intended render size

This contradicts a simple "DWM scales the window" theory — if DWM were scaling,
quality would vary by display size. The CONSTANT quality at all display sizes
suggests a FIXED processing step in the pipeline that always produces the same
output.

### Gamma Correction (Most Likely Remaining Cause)
Windows Photo Viewer uses WIC (Windows Imaging Component) which properly
handles sRGB gamma. The PNG files are sRGB-encoded. Photo Viewer decodes
the gamma curve before display, making colors richer and edges smoother.

ScummVM / OpenGL renders raw pixel values WITHOUT gamma correction. The
linear display of sRGB-encoded data makes midtones darker and contrast edges
harsher — matching the "oversharpened edges" and "blockiness" description.

**Fix**: Apply gamma correction in the OpenGL shader or in `hd_asset_manager.cpp`
after decoding the PNG:
- Option A: `png_set_gamma(pngPtr, 2.2, 0.45455)` in PNG decoder
- Option B: Gamma LUT after RGBA conversion in `loadBackground()`
- Option C: sRGB framebuffer or shader correction in OpenGL pipeline

### RealESRGAN Upscale Artifacts
The RealESRGAN upscaler may produce ringing/sharpening artifacts around
high-contrast edges. These artifacts are inherent in the source PNG and
would be visible at 100% zoom in any viewer. Photo Viewer's fit-to-window
downsampling smooths them out; the game's nearest-neighbor display preserves
them. This is likely a contributor to the perceived quality gap.

### OpenGL Framebuffer Resolution
On a 1280×800 laptop, `glReadPixels` from the default framebuffer returned
813×480 pixels — far smaller than the requested 2560×1920. This suggests
the OpenGL window/surface may not actually be created at the requested
resolution when the hardware can't support it. The window creation might
be silently downscaled by the driver, and then the 2560×1920 texture is
drawn into this smaller viewport with nearest-neighbor sampling — causing
non-uniform texel selection that looks blocky.

## Key Files Modified (as of last session)

### engine/scumm/scumm.cpp — `init()` override
- Changed `initGraphics(2560, 1920, &rgbaFmt)` to direct backend transaction

### engine/scumm/hd_asset_manager.h
- Added `setTargetSize(w, h)` method (for future display-size matching)

### engine/scumm/input.cpp
- Added `Ctrl+Shift+T` — loads test pattern `bg_0000.png`
- Added `Ctrl+Shift+D` — dumps `_hdBackgroundSurface` to `hd_surface_dump.raw`

### engine/scumm/gfx.cpp
- `drawDirtyScreenParts()` renders HD background via `copyRectToScreen`

### backends/graphics/surfacesdl/surfacesdl-graphics.cpp
- Added `uploadHDTexture()` — direct texture upload bypassing scaler
- `SDL_UpdateRects()` renders HD texture if active (no blend, no filter)
- `copyRectToScreen()` detects HD-sized copies and triggers HD texture upload

### backends/graphics/opengl/opengl-graphics.cpp
- Added framebuffer dump (`glReadPixels`) for pixel-level analysis

## Test Infrastructure

### scripts/generate_test_pattern.py
Creates `test_pattern_2560x1920.png` with:
- 1px, 2px, 4px, 8px checkerboard (tests resolution fidelity)
- 7 color bars (R, G, B, Y, C, M, W — tests byte order)
- Smooth gradient (tests color depth)
- 1px vertical RGB lines (tests pixel-level precision)
- Alternating pixel columns (128/192 gray — ultimate resolution test)

### scripts/analyze_dump.py
Compares a raw RGBA dump against the original PNG pixel-by-pixel.
Reports unique color counts, channel check, pixel match percentage.

### scripts/analyze_framebuffer.py
Attempts to parse a `glReadPixels` framebuffer dump — tries to determine
actual window dimensions and compare with original.

## Files to Check Next Session
1. `graphics/opengl/texture.cpp` — texture creation, GL filtering params
2. `backends/graphics/opengl/opengl-graphics.cpp` — updateScreen pipeline
3. `backends/graphics/opengl/pipelines/libretro.cpp` — shader pipeline
4. `backends/graphics/opengl/pipelines/pipeline.h` — drawTexture interface
5. `graphics/opengl/texture.cpp` — glTexImage2D, glTexSubImage2D calls
6. `backends/graphics/opengl/framebuffer.cpp` — projection matrix setup
7. `backends/graphics/openglsdl/openglsdl-graphics.cpp` — SDL→OpenGL bridge

## Next Steps to Try

1. **Gamma correction**: Apply sRGB→linear conversion in `loadBackground()`
   using a simple lookup table. This is the most likely remaining cause.
   
2. **Force SurfaceSDL backend**: Set `gfx_mode=normal` in scummvm.ini or
   `ConfMan` to use the SurfaceSDL renderer, which has the HD texture
   bypass already implemented.

3. **Verify actual window size**: `_windowWidth` / `_windowHeight` in the
   OpenGL backend. The frame 5 dump showed 813×480 on a 1280×800 laptop
   — this needs investigation.

4. **Compare side-by-side**: Take a photo/screenshot of the game window and
   the PNG in Photo Viewer to visually compare.

5. **Try fullscreen exclusive mode**: `SDL_WINDOW_FULLSCREEN` (not
   `SDL_WINDOW_FULLSCREEN_DESKTOP`) to bypass DWM composition.
