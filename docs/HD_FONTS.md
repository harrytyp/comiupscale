# HD Fonts — Pipeline & Rendering (Issue #17)

Status: **FIXED** on `main` (commit `74caeac0`). This document describes how
the HD fonts work end-to-end: extraction, upscaling, and the runtime
rendering path. Read `docs/v8-rendering-pipeline.md` for the general HD
compositing context.

## Overview

COMI (SCUMM v8) renders ALL text through the **Nut path**
(`CharsetRendererNut` → `NutRenderer`), not the classic charset renderer.
The HD fork intercepts every glyph, records it, and re-draws it from HD
font sheets on top of the composite (Step 2.7 in `gfx.cpp`). The 8-bit
draw is skipped — the HD glyph replaces it.

Files involved:

| File | Role |
|------|------|
| `scripts/extract_all_raw.py` | Extracts the 5 NUT fonts → `FONT<N>/chars.png` (RGBA sheets) |
| `scripts/upscale_fonts_esrgan.py` | 4x upscale (RealESRGAN, CPU) → `FONT<N>.NUT_chars.png` (3584×3584) |
| `hd_font_manager.cpp/.h` | Loads sheets, `drawChar()` blits glyphs 1:1 |
| `charset.cpp` | `CharsetRendererNut::drawCharV7` hook → records `HdFontChar`, skips 8-bit draw |
| `gfx.cpp` | Step 2.7: scales positions to HD, tints with palette color, calls `drawChar` |

## 1. Extraction (inside `extract_all_raw.py`)

**`decode_nut`'s `create_char_grid` is BROKEN for FONT0** — it produces
sheets with NO glyphs, only black placeholder rectangles on the
blue/magenta checkerboard (the black boxes are the glyph bounding boxes,
not the glyphs). Verified in BOTH the 1x `chars.png` and the waifu-upscaled
sheets. The 8-bit game text still renders fine because
`NutRenderer::loadFont` decodes the NUT FRME/FOBJ chunks directly — only
the chars.png grid pipeline loses FONT0's glyphs.

**Fix:** extract glyphs directly from the NUT frames:

```python
from nutcracker.smush.decode import generate_frames, DECODE_FRAME_IMAGE
from nutcracker.graphics import image as nut_image
chars = [ctx.screen for ctx in generate_frames(header, frames, DECODE_FRAME_IMAGE)]
```

### NUT glyph encoding (CRITICAL — outline vs fill)

Each glyph frame is a palette image with exactly three indices:

| Index | Meaning | 8-bit renderer behavior |
|-------|---------|------------------------|
| `0` | **Outline** (black contour) | drawn as **0 (black)** |
| `1` | **Fill** (the letter body) | replaced with the **text color** (`col`) |
| `39` | Transparent | skipped |

This is the original COMI design: **fat black outline + palette-colored
fill** (user-confirmed: "fette Schrift in Schwarz im Hintergrund und die
andere Schrift in Palettenfarbig für den Vordergrund"). The 8-bit renderer
does exactly this in `NutRenderer::drawCharV7`:

```cpp
if (value == 1)
    dst[i] = color;                 // fill -> text color
else if (value != _chars[chr].transparency)
    dst[i] = 0;                     // outline -> black
```

**Pipeline encoding:** the extraction maps the palette indices to RGBA so
the runtime renderer can reproduce this:

- Index 0 (outline) → **black** pixels
- Index 1 (fill) → **white** pixels (the tint target)
- Index 39 → **transparent** (alpha 0)

```python
is_outline = (pa == 0)
is_fill = (pa == 1)
r_out = np.where(is_fill, 255, np.where(is_outline, 0, r_arr))
```

### Frame size vs alpha bbox — keep the FULL frame

Cropping each glyph to its alpha bounding box destroys proportions: COMI
glyphs are ~13×27 (frame header `x2=17, y2=27`) but the ink bbox is only
~16×18. **Keep the full frame size and paste at the cell origin (no
padding)** — the transparent rows above the ink are the glyph's baseline
positioning. Cropping them makes the text top-aligned instead of sitting
on the text baseline.

```python
fw = max(1, loc.x2 - loc.x1); fh = max(1, loc.y2 - loc.y1)
if img.size != (fw, fh):
    pad = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
    pad.paste(img, (loc.x1, loc.y1), img)
    img = pad
```

Sheets: 16×16 grid of 56×56-base cells → 896×896 (1x), 3584×3584 (4x).
FONT1 == FONT2 (identical MD5, both NUT and sheet).

## 2. Upscaling (CPU, offline)

`scripts/upscale_fonts_esrgan.py` — 4x upscale with **spandrel** +
`realesr-animevideov3` (the light anime model, 2.4 MB — fast on CPU,
ideal for COMI's cartoon fonts):

```bash
# one-time setup (Python 3.13)
uv venv /tmp/upscale_venv --python python3.13
uv pip install --python /tmp/upscale_venv/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python /tmp/upscale_venv/bin/python spandrel
curl -L -o /tmp/esrgan_models/realesr-animevideov3.pth \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth

python scripts/upscale_fonts_esrgan.py extracted/fonts hd/fonts /tmp/esrgan_models/realesr-animevideov3.pth
```

Key facts:

- **Do NOT use `realesrgan`/`basicsr` pip packages** — their builds FAIL on
  Python 3.13 (`KeyError: '__version__'` in the setup `get_version`).
  Use `spandrel` (loads the same `.pth` files).
- `RealESRGAN_x4plus.pth` (67 MB) needs `torchvision::nms` — torch AND
  torchvision must be installed and version-matched (torch 2.8.0+cpu +
  torchvision 0.23.0+cpu). Full RRDB x4plus is far too slow on CPU;
  `realesr-animevideov3` finishes 896×896 → 3584×3584 in seconds.
- **Alpha channel: upscale with LANCZOS** (NEAREST gives blocky glyph
  outlines). The RGB channels go through the model, alpha through PIL
  `resize(..., Image.LANCZOS)`.

## 3. Runtime rendering (`hd_font_manager.cpp`)

User directive (binding): **"einfach nur zeichnen"** — the sheets are
already the final HD resolution. `drawChar` must blit the glyph 1:1 with
alpha. NO rescaling, NO nearest-neighbour sampling, NO LANCZOS in the
renderer — any renderer-side resampling makes the text look "fetter und
unscharf" (blocky NN) or "verschmiert" (LANCZOS).

### Glyph bounding box — alpha threshold 128

The LANCZOS alpha upscale leaves **faint alpha noise across the whole
cell** (thousands of pixels with alpha 1–50). A naive `alpha > 0` scan
finds a bounding box spanning the FULL cell (224 px wide) and draws a
giant smeared box. **Use `alpha > 128`** for both the bbox scan and the
blit — only solid glyph pixels (alpha > 128) count; the noise is skipped:

```cpp
byte pa = (p >> src.format.aShift) & 0xFF;
if (pa > 128) { /* update bbox */ }
...
if (a < 128) continue;   // skip faint noise in the blit
```

### Vertical placement — draw from cell top, no offset

Because the pipeline keeps the frame's transparent top padding, the ink
sits at the correct baseline position already. Draw from the cell TOP
(`y`) down to the bottom-most ink pixel — **no `+minY` offset** (that was
the top-aligned bug: cropping the bbox and adding minY moved glyphs up).

```cpp
int glyphW = maxX - minX + 1;
int glyphH = maxY + 1;          // cell top -> bottom ink
// blit srcX+minX+sx, srcY+sy -> x+sx, y+sy
```

### Tinting — outline stays black, fill gets the text color

The pipeline encodes outline=black / fill=white. At draw time:

```cpp
int lum = (r + g + b) / 3;
if (lum < 60) {
    r = g = b = 0;              // outline: keep black
} else {
    r = tR; g = tG; b = tB;     // fill: tint with text color
}
a = 255;
```

The tint color comes from the game palette (`col` → `_currentPalette`).
This happens in **gfx.cpp Step 2.7**, NOT in HdFontManager — the palette
accessors (`_currentPalette`, `getPalettePtr`) are protected, and
`HdFontManager` cannot reach them. `gfx.cpp` is a friend of the engine.

**Do NOT tint everything with the text color** — the outline must stay
black or the glyph becomes a fat solid blob with a fake double-edge look
(this was a long debugging arc: "doppelter Rand").

## 4. The hook (`charset.cpp`) — CRITICAL pitfalls

The hook lives in `CharsetRendererNut::drawCharV7` (NOT
`NutRenderer::drawCharV7` — NutRenderer is a separate class with no
`_curId`, and the Windows/MinGW build fails on member access into the
incomplete HdFontManager type; Linux-only green is not proof).

```cpp
// in CharsetRendererNut::drawCharV7, after pushing HdFontChar
NutRenderer *nut = dynamic_cast<NutRenderer *>(_current);
if (nut)
    return nut->getCharWidth(chr);   // real 8-bit advance, in 8-bit px
```

- **`string_v7.cpp:173` does `x += _gr->drawCharV7(...)`** — the return
  value IS the horizontal advance. Returning `1` stacks every letter on
  top of each other. Returning the 8-bit draw call double-draws. Return
  `getCharWidth(chr)`.
- **Do NOT multiply by `_scale`** — the caller advances in 8-bit coords;
  Step 2.7 scales positions to HD separately (`hdX = x * hdW / visW`).
- The old Classic hook (`CharsetRendererClassic::drawChar`, charset.cpp
  ~1391) also pushes HdFontChar — harmless for COMI (never reaches it),
  but both push if a game uses both renderers.

## 5. Step 2.7 (gfx.cpp) — position + tint

```cpp
int hdX = fi->x * hdW / MAX(1, visW);
int hdY = fi->y * hdH / MAX(1, visH);
hdX += (int)(vs->xstart) * hdW / MAX(1, _roomWidth);
byte tR = 255, tG = 255, tB = 255;
if (fi->col >= 0 && fi->col < 256) {
    tR = _currentPalette[fi->col * 3 + 0];
    tG = _currentPalette[fi->col * 3 + 1];
    tB = _currentPalette[fi->col * 3 + 2];
}
if (_hdFontManager->drawChar(fi->fontSlot, fi->chr, _hdComposite, hdX, hdY, tR, tG, tB))
    step27_drawn++;
```

`_hdFontChars` is cleared after each frame's Step 2.7 pass.

## 6. Verification workflow

- Headless screenshot: temporary frame-triggered PPM dump in gfx.cpp
  (Frames 120/240/360 → `/tmp/hd_shot_*.ppm`), convert with Pillow, send
  via `MEDIA:` for the user to judge ("ich sage dir die Wahrheit").
- The `_hdComposite` surface is **BGRA** (rShift=0, bShift=16) — PPM
  export must swap: `pr = px & 0xFF; pb = (px >> 16) & 0xFF`.
- Check the sheets themselves first (user: "Assets sehen gut aus, nur
  dieses ganze Post Processing ist kacke") — isolate asset quality from
  renderer issues before touching the renderer.
- Font slots are selected by the game via `_curId` (0–4) — the hook uses
  the same `_curId`, so the right sheet is loaded automatically.

## Known limitations

- The archive.org OST only covers the state cues (1xxx); sequence cues
  (2xxx) keep the original bundle music (additive override, automatic
  fallback) — see `docs/CD_QUALITY_MUSIC.md`.
- Cutscene/video text uses a different path (SMUSH) — HD fonts apply to
  in-game text only.
