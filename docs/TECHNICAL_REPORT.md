# COMI-HD Technical Report

## How extraction, upscaling, build & runtime-overlay work.

---

## 1. Extraction

**NUTcracker** (`tools/nutcracker/`) decodes COMI's SCUMM v8 archives into PNGs.

### Backgrounds
```
sputm --room N COMI.LA0 → ROOM/ → IMAG/WRAP blocks → PNG
```
Each room's 640×480 background is decoded from the OBIM/IMAG hierarchy. 81 rooms extracted.

### Costumes (the hard part)
```
nutcracker.sputm.costume.akos COMI.LA0 → AKPL indices → Room Palette (APAL) → 8-bit PNG
```
Default NUTcracker uses RGBS → black costumes. **Fix:** map AKPL indices through the room's APAL palette (768-byte RGB table in ROOM/PALS/WRAP/APAL) instead.

25,304 costume frames extracted across 473 costumes.

### Objects, Fonts, Cutscenes
- Objects: OBIM/IMAG decode → 600 object PNGs + 633 layer PNGs
- Fonts: charset extraction from room scripts → 5 fonts
- Cutscenes: HNM → ffmpeg → MP4 (15 videos)

---

## 2. Upscaling

**RealESRGAN** `x4plus_anime_6B` via `realesrgan-ncnn-vulkan`.

```
realesrgan-ncnn-vulkan -i input.png -o output.png -s 4 -m models/x4plus-anime
```

All 38,689 PNGs at 4×:
- Backgrounds: 640×480 → 2560×1920
- Costume frames: variable → 4×
- Objects: variable → 4×
- Videos: processed separately with Topaz Video AI (by ubertrout)

---

## 3. Build

**MinGW cross-compile** (Windows binary) from Linux.

```
./configure --host=x86_64-w64-mingw32 \
  --enable-engine=scumm,scumm-7-8 \
  --with-sdl-prefix=/tmp/mingw_prefix
```

Trap: engine name is `scumm-7-8` (hyphen), not `scumm_7_8`. Underscore is silently ignored by configure → only builds v0–6.

Make produces `scummvm.exe` (~88 MB). Bundled: `SDL2.dll`, `zlib1.dll`.

---

## 4. Runtime Overlay Architecture

The fork adds an independent HD rendering pipeline that runs **after** the original 8-bit engine renders. No game data is modified.

### Entry point: `ScummEngine::drawDirtyScreenParts()` (gfx.cpp:537)

The existing ScummVM render loop. After all 8-bit drawing completes, it calls `renderHDComposite()`.

### Core: `renderHDComposite()` (gfx.cpp:1228)

Four-step compositing onto a 2560×1920 RGBA surface:

```
           HD Composite Buffer (2560×1920 RGBA)
    ┌────────────────────────────────────────────┐
    │ Step 1: HD background (from PNG)           │  ← HDAssetManager::loadBackground()
    ├────────────────────────────────────────────┤
    │ Step 2: Objects overlay (alpha-blended)     │  ← HDObjectManager
    ├────────────────────────────────────────────┤
    │ Step 3: Costumes overlay (alpha-blended)    │  ← HDCostumeManager
    ├────────────────────────────────────────────┤
    │ Step 4: Fonts overlay (text/dialogue)       │  ← HDFontManager
    └────────────────────────────────────────────┘
                       ↓
             copyRectToScreen() → display
```

**Step 1** — `HDAssetManager::loadBackground(room, surf)` loads `hd/backgrounds/bg_NNNN.png` from disk. Converted from RGB→RGBA for compositing. If no HD background exists, the 8-bit framebuffer is software-upscaled (nearest-neighbor + palette lookup) as fallback.

**Step 2** — `HDObjectManager` draws HD object PNGs at their scaled screen coordinates. Objects from OBIMs with `img_count > 0` are rendered alpha-blended over the background. Objects without image data (trigger volumes, hotspots) are skipped.

**Step 3** — `HDCostumeManager` tracks visible actors in the current frame, loads the corresponding HD costume frame PNG (`hd/costumes/LFLF_NNNN_AKOS_NNNN_aframe_NNN.png`) by matching AKOS index + frame number. Alpha-blended at 4× scaled position.

**Step 4** — `HDFontManager` intercepts `drawChar()` calls. HD font glyphs (`hd/fonts/font_NN/`) replace the 8-bit bitmap font characters. Dialogue and UI text rendered at HD resolution.

### Coordinate scaling

SD coordinates ↦ HD coordinates via `_hdScale` (= `hdBackground.w / _screenWidth`). Each 8-bit pixel maps to a 4×4 HD block. Objects/costumes are positioned at `(sdX * scale, sdY * scale)`.

### HDAssetManager (patches/hd_asset_manager.cpp)

Reads PNGs from the `hd/` subdirectory (configurable via `hd_path` in scummvm.ini). Uses ScummVM's `PNGDecoder`. Caches nothing — disk reads per frame (ponytail: add LRU cache if frame-rate becomes a problem).

### Files

| File | Purpose |
|------|---------|
| `gfx.cpp:renderHDComposite()` | Orchestrates 4-step compositing |
| `hd_asset_manager.cpp` | PNG loader for backgrounds |
| `hd_object_manager.cpp` | HD object overlay (alpha, culling, masks) |
| `hd_costume_manager.cpp` | HD costume frame matching + overlay |
| `hd_font_manager.cpp` | HD font glyph rendering |
| `hd_video_player.cpp` | SMUSH→HD video passthrough |
| `room.cpp` | Room state → HD costume/object coordination |

### Debug (gfx.cpp:1814)

`hdDebugDump()` writes composite/background/SD-compare/diff RAW files for pixel-level verification. One-shot per room change when `hd_dump_frame=N` is set. Produces the `composite.raw` used for screenshot capture.

---

Skipped: cache layer, multithreaded loading, partial-frame compositing. Add when profiling shows they're needed.
