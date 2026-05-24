# HD Background Quality Analysis

## Problem
The 2560×1920 RealESRGAN-upscaled PNG backgrounds look noticeably worse when
displayed in our ScummVM fork compared to viewing the same PNG in Windows
Photo Viewer. The image appears "limited at the resolution" — blocky and
lacking detail — despite the PNG loading at full 2560×1920 × 24-bit RGB.

## What We've Verified (Works Correctly)
- PNG loads at 2560×1920 × 24-bit RGB via libpng (verified via `file` command)
- Conversion to 32-bit RGBA8888 with correct [R, G, B, A] byte order (R/G/B test patches)
- SDL display initialized at 2560×1920 × 32bpp (reported by `_system->getScreenFormat()`)
- Smooth color gradient — NO banding, full 24-bit color depth works
- Nearest-neighbor and linear scaling both tried — minimal visible difference
- HD surface is 2560×1920 with pitch=10240 (verified)
- SDL texture format: SDL_PIXELFORMAT_RGBA32 (set explicitly, not 16-bit)
- Red, green, blue test patches render as pure correct colors

## NEW KEY FINDING — `loadGFXMode()` is NEVER Called
Despite extensive debugging with `warning()` calls placed at the entry of
`loadGFXMode()`, those warnings NEVER appear in the console output. This
means the `initGraphics(2560, 1920)` call in `setupScumm()` does NOT trigger
a full graphics mode reload — even though `initSize()` is called (the size
change is detected) and `endGFXTransaction()` runs.

The `loadGFXMode()` function is what calls `initGraphicsSurface()`, which
creates the `_hwScreen` (window surface), and the scaler surfaces. Without
this call, the window and surfaces from the FIRST `initGraphics(640, 480)`
call remain in place. The SECOND call only sets `_videoMode.screenWidth`
and `_videoMode.screenHeight` to 2560×1920 but never re-creates the actual
surfaces at the new size.

**Implication**: The `_screen` surface is still 640×480 (the original game
resolution) even though `_system->getWidth()` returns 2560. The `copyRectToScreen()`
calls for the 2560×1920 HD background MAY write beyond the 640×480 surface,
causing memory corruption or clipping.

**Root cause**: The `initGraphicsAny()` function at `engines/engine.cpp:427`
calls `g_system->endGFXTransaction()`, but our `initGraphics(2560, 1920)` call
in `setupScumm()` may be issuing a different transaction type that doesn't
trigger `loadGFXMode()`.

### Why This Explains the Quality Gap
If `_screen` is only 640×480, then every `copyRectToScreen()` for the
2560×1920 HD background writes well beyond the surface bounds. The buffer
might wrap, truncate, or alias — explaining the "lower resolution" look.
The 640×480 surface has only 307,200 pixels. Writing 4,915,200 pixels
(2560×1920) will overflow significantly.

## Revised Root Cause Guesses

### Guess 1 (Most Likely): `_screen` Surface Never Resized
`loadGFXMode()` is not triggered by our second `initGraphics()` call.
The `_screen` surface remains at the original 640×480 size. Our 2560×1920
`copyRectToScreen()` calls overflow the surface, causing truncation or
memory corruption that manifests as reduced visual quality.

**Fix**: Force a hardware mode reload. Instead of calling `initGraphics()`,
call `g_system->beginGFXTransaction()` + `g_system->initSize()`
+ `g_system->endGFXTransaction()` directly, OR call `loadGFXMode()` explicitly.

### Guess 2: Transaction Failure Fallback
The second `initGraphics()` might create a transaction that FAILS (because
2560×1920 with 32-bit RGBA isn't supported by the GPU/driver on this laptop).
The failure triggers a fallback to CLUT8 (8-bit palette), and the
`initGraphicsAny()` returns the fallback mode. `_screen` is then recreated
at 640×480 in 8-bit mode. Our 32-bit `copyRectToScreen` data is interpreted
as 8-bit paletted, causing terrible quality.

**Fix**: Check the return value of `initGraphics()` and verify that
`_outputPixelFormat` matches our requested format.

### Guess 3: Scaler Processing Even at 1x
Even if `loadGFXMode()` IS called (we couldn't verify due to logging issues),
the scaler at lines 1440-1458 of `internUpdateScreen()` processes every pixel
from `_tmpscreen` → `_hwScreen`. The scaler might be doing format conversion
even at factor=1, reducing 32-bit to 16-bit internally.

**Fix**: Add the HD background as a separate SDL texture bypassing the scaler
entirely. Use `SDL_RenderCopy()` directly.

### Guess 4: libpng sRGB/Gamma Mismatch
libpng reads sRGB-encoded PNG data. If ScummVM's default decoding applies
gamma correction while Windows Photo Viewer uses WIC's color-managed pipeline,
the pixel values would differ. This manifests as "flat" or "dark" appearance —
which matches "lower quality" perception.

**Fix**: Apply `png_set_gamma()` or manually correct after decoding.

### Guess 5: HW Surface Format
The `initGraphicsSurface()` function uses `SDL_SetVideoMode(... , 16, ...)` 
— hardcoded to 16 bpp (line 954). For SDL2, the wrapper overrides this,
but if the wrapper isn't called (because `loadGFXMode()` isn't triggered),
the original SDL1.2 `SDL_SetVideoMode` might create a 16-bit surface.

**Fix**: We already changed `16 → 32` in `initGraphicsSurface()`. But if
`loadGFXMode()` is never called, this change never takes effect.

## Next Steps
1. **Force `loadGFXMode()`**: Add `g_system->setFeatureState(...)` or call
   the resize path explicitly after our `initGraphics()` override.
2. **Verify surface dimensions**: Add debug that dumps `_screen->w/h` and
   `_hwScreen->w/h` to confirm they're 2560×1920.
3. **Check transaction return**: After `initGraphics(2560, 1920)`, check
   if the transaction succeeded by verifying format matches.
4. **Bypass transaction**: Directly call `g_system->beginGFXTransaction()`,
   `initSize()`, `initGraphicsSurface()` to force a clean setup.
5. **Gamma fix**: Apply `png_set_gamma()` in hd_asset_manager if all else
   fails.
