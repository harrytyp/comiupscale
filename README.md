# COMI Upscaled — Project Documentation

## Overview

This project extracts all visual assets from **"The Curse of Monkey Island"**
(LucasArts, 2000, SCUMM V8), upscales them 4x using AI (RealESRGAN-NCNN-Vulkan),
and delivers them via a **modified ScummVM fork** with HD overlay support.

**Strategy:** Instead of patching original game data (the reimport approach which
breaks coordinate-based structures), we fork ScummVM's SCUMM engine to load 4x
replacement textures from an external `hd/` directory at runtime. See [PLAN.md](PLAN.md).

**Project root:** `Z:\Projekte\COMI-Upscaled\` (NAS, Windows) / `~/comiupscale/` (Linux/macOS)

---

## Documentation Index

| File | Description |
|------|-------------|
| `PLAN.md` | **Main plan** — ScummVM HD fork strategy, phases, milestones |
| `README.md` | This file — project overview and structure |
| `AGENTS.md` | AI agent handoff document (session context) |
| `PATH_A_ANALYSIS.md` | Technical analysis of HD reimport requirements |
| `RESEARCH.md` | Research on existing solutions, forums, techniques |
| `scripts/export_all.sh` | Automated full-export script |
| `requirements.txt` | Python dependencies for AKOS decoding |
| `docs/FORK_PLAN.md` | Detailed technical plan for ScummVM fork |
| `docs/HD_MANIFEST_SPEC.md` | hd_manifest.json format specification |
| `docs/BUILD.md` | Build instructions for the ScummVM fork |
| `scummvm/fork/` | **Pre-configured ScummVM fork** (all HD patches applied) |
| `scummvm/fork/build.sh` | Cross-platform build script (Linux/macOS/Windows) |

---

## Extracted Asset Summary

| Category | PNGs | Location |
|----------|------|----------|
| Backgrounds | 40 | `CMI UPSCALED/extracted/COMI/IMAGES/backgrounds/` |
| Objects | 600 | `CMI UPSCALED/extracted/COMI/IMAGES/objects/` |
| Object layers | 234 | `CMI UPSCALED/extracted/COMI/IMAGES/objects_layers/` |
| Cutscene frames | 12,506 | `CMI UPSCALED/extracted/COMI/cutscenes/*/` (15 dirs) |
| Fonts | 5 | `CMI UPSCALED/extracted/COMI/fonts/*/chars.png` |
| Costumes/sprites | 25,304 | `CMI UPSCALED/extracted/COMI/costumes/` |
| **TOTAL** | **38,689** | |

---

## Project Structure

```
Z:\Projekte\COMI-Upscaled\
├── PLAN.md                       # ScummVM HD fork plan (READ FIRST)
├── README.md                     # This file
├── AGENTS.md                     # AI handoff doc
├── INDEX.md                      # Legacy file index
├── PATH_A_ANALYSIS.md            # HD reimport technical analysis
├── RESEARCH.md                   # Research findings
├── requirements.txt              # Python deps (numpy, pillow, typer)
│
├── patches/                      # ScummVM HD fork patches
│   ├── scumm-hd-fork.patch       # Git patch for 5 modified engine files
│   ├── hd_asset_manager.h        # New HD asset manager header
│   └── hd_asset_manager.cpp      # New HD asset manager implementation
│
├── docs/
│   ├── FORK_PLAN.md              # Detailed ScummVM fork tech plan
│   ├── HD_MANIFEST_SPEC.md       # hd_manifest.json format
│   └── BUILD.md                  # ScummVM fork build instructions (reproducible)
│
├── setup.sh                       # Quick setup script (download + run)
├── scripts/
│   ├── export_all.sh             # Automated export (chmod +x)
│   ├── full_pipeline.sh          # Extract → upscale → build → play
│   ├── demo_upscale.py           # Lanczos upscale demo
│   ├── demo_upscale_stage.py     # Stage room demo
│   └── hd_manifest_gen.py        # hd_manifest.json generator
│
├── hd_config/
│   └── batch_upscale.sh          # Batch RealESRGAN upscale script
│
├── nutcracker/
│   ├── src/nutcracker/           # Python source (for AKOS decoding)
│   └── pyproject.toml            # Python package definition
│
├── nutcracker-Windows_X64/
│   └── nutcracker.exe            # Prebuilt Windows binary
│
├── scummvm-fork/ -> /c/Users/go75bel/scummvm-fork  # ScummVM source (localhost clone)
│
├── ScummVM/
│   ├── scummvm.exe               # Stock ScummVM binary
│   ├── monkey3/
│   │   ├── COMI.LA0, .LA1, .LA2 # Game resource archives
│   │   └── RESOURCE/             # SAN cutscenes, NUT fonts, BUN audio
│   │   └── hd/                   # HD manifest + upscaled assets (future)
│   └── ...
│
├── scummvm-tools/                # ScummVM utilities (compress, etc.)
├── scummeditor/                   # ScummEditor C# source
│
├── COMI/                          # Raw resource dump
│   ├── LECF_0001/                # Rooms 1-38
│   ├── LECF_0002/                # Rooms 39-93
│   └── rpdump.xml
│
├── CMI UPSCALED/
│   ├── extracted/COMI/
│   │   ├── IMAGES/
│   │   │   ├── backgrounds/      # 40 PNGs (original)
│   │   │   ├── objects/          # 600 PNGs (original)
│   │   │   └── objects_layers/   # 234 PNGs (original)
│   │   ├── cutscenes/            # 15 dirs, ~12,506 frames
│   │   ├── fonts/                # 5 dirs
│   │   └── costumes/             # 25,304 frames
│   ├── upscaled/                 # HD output dir (4x AI-upscaled)
│   │   ├── backgrounds/
│   │   ├── objects/
│   │   ├── cutscenes/
│   │   ├── costumes/
│   │   └── objects_layers/
│   ├── hd/                       # HD manifest + assets for ScummVM fork
│   ├── demo/                     # Lanczos demo (room 0015)
│   ├── demo_stage/               # RealESRGAN demo (room 0019)
│   └── repackaged/               # Legacy reimport output (unused)
│
├── MMUCS/                        # Godot SCUMM V8 viewer
└── tools/
    └── realesrgan-ncnn-vulkan-v0.2.0-windows/
```

---

## Key Tools

### NUTcracker Binary
- **Path:** `nutcracker-Windows_X64/nutcracker.exe`
- **Usage:** Backgrounds, objects, cutscenes, fonts
- **Commands:** `sputm room decode`, `smush decode`, `sputm room encode`, `sputm build`

### NUTcracker Python Source
- **Path:** `nutcracker/src/nutcracker/`
- **Usage:** AKOS costume decoding
- **Run:** `PYTHONPATH=nutccker/src python -m nutcracker.sputm.costume.akos <LA0>`
- **Deps:** numpy, pillow, typer

### RealESRGAN-NCNN-Vulkan
- **Path:** `tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe`
- **Model:** `realesrgan-x4plus-anime` (best for COMI's hand-drawn cartoon style)
- **Usage:** `realesrgan-ncnn-vulkan.exe -i input.png -o output.png -m models/ -n realesrgan-x4plus-anime`

### Python Setup
- System Python: `C:\Users\go75bel\AppData\Local\Programs\Python\Python313\python.exe`
- Hermes venv: no pip — use system Python instead

---

## Quick Start (Fast Path — Pre-built Binary + HD Assets)

**You need:** Your own copy of Curse of Monkey Island (COMI.LA0/1/2).

```bash
# 1. Clone this repo (works on Linux, macOS, and Windows)
git clone https://github.com/harrytyp/comiupscale.git
cd comiupscale

# 2. Build from source (recommended — cross-platform)
cd scummvm/fork
bash build.sh              # Auto-detects Linux/macOS/Windows

# 3. Or download pre-built binary from GitHub Releases
```

### How to get assets

| Asset | Where to get it |
|-------|----------------|
| **Game files** (`COMI.LA0/1/2`) | Your original game disc or GOG/Steam install |
| **ScummVM HD binary** (`scummvm-hd.exe`) | [GitHub Releases](https://github.com/harrytyp/comiupscale/releases) |
| **HD backgrounds** (`hd/bg_XXXX.png`) | [GitHub Releases](https://github.com/harrytyp/comiupscale/releases) or run `scripts/full_pipeline.sh` to upscale yourself |
| **HD cutscene videos** | [archive.org — COMI_4k](https://archive.org/details/COMI_4k) (download and place in `monkey3/hd/videos/`) |

### Creating a GitHub Release

To make the fast path work for others, create a Release on GitHub:

1. Go to https://github.com/harrytyp/comiupscale/releases
2. Click **"Create a new release"**
3. Tag: `v1.0.0` 
4. Title: `v1.0.0 — Initial HD release`
5. Attach these files:
   - `scummvm-hd.exe` — the pre-built binary from your local build
   - `hd-backgrounds.zip` — the HD backgrounds package
6. Publish release

Then `setup.sh` will download these automatically.

### Build from Source (Recommended)

The repo includes a **pre-configured ScummVM fork** in `scummvm/fork/` with all HD
patches already applied. No need to clone vanilla ScummVM or apply patches manually.

```bash
# Quick build (cross-platform):
cd scummvm/fork
bash build.sh

# Or manual build:
# Linux
./configure --backend=sdl --disable-all-engines --enable-engine=scumm
make -j$(nproc)

# Windows (MSYS2 MinGW64)
./configure --host=mingw64 --backend=sdl --disable-all-engines --enable-engine=scumm
mingw32-make -j$(nproc)

# Verify SCUMM v7/8 support
grep "ENABLE_SCUMM_7_8" config.mk
# Should show: ENABLE_SCUMM_7_8 = 1

# Run
./scummvm --path=/path/to/game          # Linux/macOS
./scummvm.exe --path=/path/to/game      # Windows
```

### Generate HD Backgrounds from Game Files

To extract and upscale backgrounds yourself (requires RealESRGAN):

```bash
bash scripts/full_pipeline.sh --game /path/to/COMI
```

This will:
1. Extract original 640×480 backgrounds from COMI.LA0 using NUTcracker
2. Upscale 4× using RealESRGAN (takes ~30 min on a GPU)
3. Place HD PNGs in `monkey3/hd/`
4. Optionally build the ScummVM fork

---

## Critical Gotchas

1. **sputm room decode has NO --target flag** — output always relative to CWD
2. **AKOS costumes** are NOT extracted by sputm — use Python decoder
3. **NAS (Z:) is slow** — bulk operations on 25K+ files may time out
4. **Shell is Git Bash** — POSIX syntax, NOT PowerShell
   (On Linux/macOS, use your native shell — no Git Bash needed)
5. **ScummVM fork approach** replaces the old reimport plan — coordinate patching
   is handled at runtime in C++, not in the asset files

---

## HD Rendering Pipeline (How It Works)

The ScummVM fork uses the **OpenGL backend** (not SurfaceSDL). HD backgrounds are loaded
at 2560×1920 32-bit RGBA from the `hd/` directory. Here's every technique used:

### 1. Screen Setup — `scumm.cpp:init()`

After the engine initializes the game at 640×480 (the original resolution), the HD
init block detects upscaled backgrounds in `game-dir/hd/`, computes the scale factor
(4× = 2560×1920 for COMI), and reinitializes the graphics system:

```cpp
_system->beginGFXTransaction();
_system->initSize(2560, 1920, &rgbaFormat);  // 32-bit RGBA
_system->endGFXTransaction();
```

This makes the OGL backend's virtual screen 2560×1920 RGBA32 instead of the original
640×480 CLUT8. The engine's internal coordinate system stays 640×480.

### 2. Background Loading — `room.cpp:startScene()`

When a room loads, `HDAssetManager::loadBackground()` loads the matching
`hd/bg_{room:04d}.png` at its native HD resolution (no downscaling).

### 3. Composite Rendering — `gfx.cpp:drawDirtyScreenParts()`

The game engine renders to the 8-bit virtual screen (`_virtscr[kMainVirtScreen]`)
at 640×480 as usual. After each frame, the HD compositing function:

1. Copies the HD background as-is (2560×1920 RGBA) to the composite buffer
2. For each 640×480 virtual-screen pixel, determines if it's "foreground" (actor,
   object, UI element) by comparing against the saved clean background
3. **Foreground pixels** are palette-converted (8-bit index → 32-bit RGBA via
   `_currentPalette`) and placed at 4× coordinates in the composite buffer
4. **Background pixels** (unchanged from clean) keep the HD background color
5. The composite buffer is `copyRectToScreen`'d to the OGL backend

This **diff-against-clean** technique separates game content from the original 8-bit
background, letting the HD background show through everywhere the game hasn't drawn.

### 4. Clean Background — `redrawBGStrip()`

When the engine draws a background strip (via `_gdi->drawBitmap`), the result is
saved as the "clean" reference for that strip before any actors/objects are drawn.
Pixels that differ from clean are composited as foreground on the HD background.

### 5. Palette — `opengl-graphics.cpp:setPalette()`

**Critical fix:** In RGBA32 mode, `_gameScreen->hasPalette()` returns false. The
original ScummVM code would skip palette updates, breaking 8-bit→32-bit conversion
for both the compositing pipeline AND the cursor. The fix ALWAYS updates the
`_gamePalette` copy and ALWAYS calls `updateCursorPalette()`, regardless of screen
format:

```cpp
void OpenGLGraphicsManager::setPalette(...) {
    memcpy(_gamePalette + start * 3, colors, num * 3);  // always
    if (_gameScreen->hasPalette())
        _gameScreen->setPalette(start, num, colors);
    updateCursorPalette();  // always
}
```

### 6. Mouse Coordinates — `input.cpp`

The OGL backend delivers mouse coordinates in 2560×1920 space (because
`initSize` set those dimensions). But all game logic expects 640×480. The fix
rescales at the input layer:

```cpp
if (HD mode active) {
    mouse.x = mouse.x * 640 / hdBackground.w;
    mouse.y = mouse.y * 480 / hdBackground.h;
}
```

### 7. Cursor Rendering — `opengl-graphics.cpp`

Three issues had to be solved to get the cursor working at HD resolution:

**a) Cursor Format (the big one):** The SCUMM engine calls
`CursorMan.replaceCursor()` with 8-bit CLUT8 cursor data, but passes
`_system->getScreenFormat()` (which returns RGBA32 after HD init) as the pixel
format. The OpenGL backend would interpret 8-bit indices as 32-bit RGBA pixels,
producing garbage. **Fix:** In `setMouseCursor()`, override the format to CLUT8
when the reported format has >1 byte per pixel:

```cpp
if (inputFormat.bytesPerPixel != 1)
    inputFormat = Graphics::PixelFormat::createFormatCLUT8();
```

**b) Cursor Palette:** Because `setPalette()` was skipping palette updates in
RGBA32 mode (fixed in #5), the cursor texture never got the correct palette
colors. The cursor `updateCursorPalette()` is now called unconditionally.

**c) Cursor Size:** The cursor at 2560×1920 is tiny (20×20 pixels) without
scaling. The `recalculateCursorScaling()` method computes the scale factor
from `_gameDrawRect` / `_gameScreen->getWidth()`, both of which are 2560
(scale = 1.0). **Fix:** After standard scaling, multiply cursor dimensions by
the ratio of game screen width to 640 (the original game width):

```cpp
if (_gameScreen && _gameScreen->getWidth() > 640) {
    int hdScale = _gameScreen->getWidth() / 640;  // = 4
    _cursorHotspotXScaled *= hdScale;
    _cursorWidthScaled    *= hdScale;
    // ... same for Y
}
```

### 8. Cursor Texture Recreation (Anti-pattern removed)

An earlier attempt deleted and recreated the cursor in `endGFXTransaction()` when
the game screen format changed to RGBA32. This was WRONG — it made the cursor null
until the engine next called `setMouseCursor()`. The `TextureSurfaceCLUT8GPU` and
`FakeTextureSurface` classes already handle CLUT8→RGBA conversion via palette
lookup during texture upload; no recreation is needed.

### 9. High-Quality Display (Lanczos Shader)

The `LibRetroPipeline` constructor initializes its `_inputPipeline` with the
`kLanczos` shader for high-quality area sampling. This is applied automatically
when scaling passes are active (requires `shaders.dat` in the executable
directory; falls back to default bilinear filtering otherwise).

---

## Current Status

### Working
- **HD backgrounds** — 40 rooms with 2560×1920 32-bit RGBA backgrounds load
  and display correctly
- **Game compositing** — actors, objects, UI elements render on top of HD
  backgrounds via diff-against-clean compositing
- **Palette handling** — 8-bit→32-bit conversion works correctly with the
  per-frame palette synced to the OpenGL backend
- **Mouse interaction** — all click targets work at correct positions
  (coordinates rescaled from 2560×1920 to 640×480)
- **Cursor** — rendered at correct size (4× scaled) with proper palette colors

### Not Working
- **Video cutscenes (SMUSH/SAN)** — the original game videos play at 640×480
  and don't display over the HD framebuffer. **Upscaled videos** are available from
  [archive.org](https://archive.org/details/COMI_4k) — place them in `monkey3/hd/videos/`.
  The fork doesn't yet intercept video playback to use these HD replacements.
- **HD objects/costumes** — only backgrounds have HD replacements so far.
  The compositing pipeline works with original-resolution objects.

### Remaining Work
- SMUSH/SAN video rendering support through the HD pipeline
- HD costume/object/sprite loading and display
- Cutscene frame upscaling pipeline
- Performance optimization (Lanczos on Intel UHD)

---

## Build Instructions

### Prerequisites
## Build Instructions

### Prerequisites

#### Linux (Ubuntu/Debian)
```bash
sudo apt install build-essential pkg-config \
  libsdl2-dev libfreetype-dev libpng-dev \
  libvorbis-dev libflac-dev libgl-dev \
  libglu1-mesa-dev libjpeg-dev zlib1g-dev
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf groupinstall 'Development Tools'
sudo dnf install SDL2-devel freetype-devel libpng-devel \
  libvorbis-devel flac-devel mesa-libGL-devel \
  libjpeg-turbo-devel zlib-devel
```

#### Linux (Arch)
```bash
sudo pacman -S base-devel pkgconf sdl2 freetype2 libpng \
  libvorbis flac mesa libglvnd
```

#### Windows (MSYS2)
See [docs/BUILD.md](docs/BUILD.md) for full MSYS2 setup.

Quick install (MSYS2 MinGW64 terminal):
```bash
pacman -S --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-make \
  mingw-w64-x86_64-SDL2 mingw-w64-x86_64-libpng mingw-w64-x86_64-zlib \
  mingw-w64-x86_64-freetype mingw-w64-x86_64-libvorbis mingw-w64-x86_64-libogg \
  mingw-w64-x86_64-flac mingw-w64-x86_64-libmad mingw-w64-x86_64-libtheora \
  mingw-w64-x86_64-faad2 mingw-w64-x86_64-curl mingw-w64-x86_64-fluidsynth \
  mingw-w64-x86_64-fribidi
```

### Build Steps

```bash
# 1. Install prerequisites (see Prerequisites above)

# 2. Clone the repo
git clone git@github.com:harrytyp/comiupscale.git
cd comiupscale/scummvm/fork

# 3. Build (config is pre-configured, no ./configure needed)
bash build.sh              # Auto-detects platform (Linux/macOS/Windows)

# 4. Prepare game data
mkdir -p ../../game
# Copy COMI.LA0/1/2 + RESOURCE/ from your game install into ../../game/

# 5. Run
./scummvm --path=../../game    # Linux/macOS
bash launch.cmd                # Windows
```

### Debug Dumps

The fork can write per-frame debug dumps for compositing analysis. Set
`hd_dump_frame=N` in `scummvm.ini` under `[comi]` to trigger a dump at a
specific frame number (e.g., `hd_dump_frame=4` for room 4). This writes:
- `hd_dump_N_composite.raw` — final 2560×1920 RGBA output
- `hd_dump_N_hdcomposite.raw` — HD composite before copy to screen
- `hd_dump_N_virtscr.raw` — 640×480 8-bit virtual screen
- `hd_dump_N_clean.raw` — 640×480 8-bit clean background reference
- `hd_dump_N_valid.raw` — per-pixel valid mask (1 = clean available)
- `hd_dump_N_state.txt` — engine state at dump frame

### HD Asset Tracing

To see which HD files the fork is looking up and whether they exist, add to
`scummvm.ini` under `[comi]`:

```ini
[comi]
hd_trace=true
```

This prints every HD file access at runtime:

```
hd_trace: OK   game/hd/bg_0019.png
hd_trace: MISS game/hd/objects/0087_easyhard-choice-object_0000.png
hd_trace: OK   game/hd/costumes/LFLF_0001_AKOS_0001_aframe_0.png
```

Use this to debug missing assets, wrong paths, or unexpected fallback to
8-bit rendering. Works for backgrounds, objects, costumes, fonts, and videos.

### Diagnostics Suite

Run these tools to check if HD rendering is working correctly:

```bash
# 1. Validate that all project paths and dependencies are correct
python scripts/check_setup.py
python scripts/check_setup.py --debug   # show every resolved path

# 2. Check HD dump files after the game writes them
python scripts/check_hd_dumps.py /path/to/dump/dir

# 3. Trace HD asset access during gameplay (requires hd_trace=true in config)
#    The trace output appears in the ScummVM console/log.

# 4. Full validation pipeline
bash scripts/full_pipeline.sh
```

The dump analyzer checks:
- Raw file sizes match expected HD (2560×1920) or SD (640×480) dimensions
- Whether pixel data is all zeros (no content) or all the same (clipping)
- State info per room (scale factor, room IDs)

