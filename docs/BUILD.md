# COMI-HD — Build, Extract, Upscale & Start

This document covers everything needed to build the ScummVM HD fork,
extract game assets, upscale them, and run the game with HD textures.

---

## 1. Build the ScummVM HD Fork

### Prerequisites

#### Linux (Ubuntu/Debian)
```bash
sudo apt install build-essential pkg-config \
  libsdl2-dev libpng-dev libgl-dev \
  libglu1-mesa-dev zlib1g-dev
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf groupinstall 'Development Tools'
sudo dnf install SDL2-devel libpng-devel \
  mesa-libGL-devel mesa-libGLU-devel zlib-devel
```

#### Windows (Cross-Compile with LLVM MinGW)
See `scripts/full_pipeline.sh` for the automated cross-compile setup using
[LLVM MinGW](https://github.com/mstorsjo/llvm-mingw) on Linux.

### Linux Build

```bash
cd scummvm/fork

# Configure — only SCUMM engine with v7/v8 support
./configure --opengl-mode=gl \
  --enable-verbose-build \
  --disable-all-engines \
  --enable-engine=scumm,scumm-7-8

# Verify config
grep "ENABLE_SCUMM" config.mk
# Should show:
#   ENABLE_SCUMM = STATIC_PLUGIN
#   ENABLE_SCUMM_7_8 = 1

# Build
make -j$(nproc)
```

### Windows (Cross-Compile from Linux)

```bash
export PATH="/path/to/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64/bin:$PATH"
export PKG_CONFIG_LIBDIR=

cd scummvm/fork

./configure --host=x86_64-w64-mingw32 \
  --with-zlib-prefix=/path/to/mingw_prefix \
  --with-png-prefix=/path/to/mingw_prefix \
  --with-sdl-prefix=/path/to/sdl2_mingw/SDL2-2.30.11/x86_64-w64-mingw32 \
  --opengl-mode=gl \
  --enable-verbose-build \
  --disable-nasm \
  --disable-all-engines \
  --enable-engine=scumm,scumm-7-8

# Verify
grep "ENABLE_SCUMM" config.mk
# Should show ENABLE_SCUMM = STATIC_PLUGIN and ENABLE_SCUMM_7_8 = 1

make -j$(nproc)
```

Reference configs for both platforms are in the repository:
- `scummvm/fork/config.mk.win` — Windows cross-compile config
- `scummvm/fork/config.mk.linux` — Linux config

### Windows (MSYS2 Native)

```bash
cd scummvm/fork

export CC=gcc CXX=g++
./configure --host=mingw64 --backend=sdl \
  --enable-optimizations --enable-release \
  --disable-all-engines --enable-engine=scumm,scumm-7-8

mingw32-make -j12
```

### Important: `scumm-7-8` vs `scumm_7_8`

The configure flag is **`scumm-7-8`** (with hyphen), **NOT** `scumm_7_8` (underscore).
The underscore variant is silently ignored by configure — the engine won't be compiled.

Always verify in `config.mk`:
```makefile
ENABLE_SCUMM_7_8 = 1
```

---

## 2. Extract Game Assets

The HD pipeline requires extracting original game resources (backgrounds, objects,
costumes, fonts) from the COMI data files into PNG format.

### Requirements
- Python 3 with `numpy`, `pillow`, `parse`, `deal`
  ```bash
  pip install numpy pillow parse deal
  ```
- [NUTcracker](https://github.com/Akari1989/nutcracker) (Python source)

### Extract Everything

The master script handles all extraction at once:

```bash
cd scripts
bash export_all.sh
```

This extracts into `CMI UPSCALED/extracted/COMI/`:

| Category | Count | Location |
|----------|-------|----------|
| Backgrounds | 40 | `IMAGES/backgrounds/` |
| Objects | 600 | `IMAGES/objects/` |
| Object layers | 234 | `IMAGES/objects_layers/` |
| Cutscene frames | 12,506 | `cutscenes/*/` |
| Fonts | 5 | `fonts/*/chars.png` |
| Costumes | 25,304 | `costumes/` |

### Extract Costumes Only

```bash
PYTHONPATH=tools/nutcracker/src python3 -m nutcracker.sputm.costume.akos COMI.LA0
```

Note: AKOS costume extraction maps palette indices through the room palette (APAL),
not through the RGBS table. The correct method is:
1. Read AKPL indices (0-254) from the AKOS costume data
2. Map through the 256-color room palette (APAL, 768 bytes in ROOM/PALS/WRAP/APAL)
3. Not through the 16-color RGBS table

---

## 3. Upscale Assets

### Requirements
- [RealESRGAN](https://github.com/xinntao/RealESRGAN) with `x4plus_anime_6B` model
- Python 3 with `torch`, `numpy`, `pillow`

### Upscale Everything

```bash
bash hd_config/batch_upscale.sh
```

This batch-upscales all extracted assets using the RealESRGAN `x4plus_anime_6B` model.

### Upscale a Single Room

```bash
python3 scripts/upscale_room9.py
```

### Manual Upscaling with ncnn (no GPU)

```bash
# Use the ncnn Vulkan implementation for systems without NVIDIA GPU
tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe \
  -i input.png -o output.png \
  -n realesr-animevideov3-x4
```

### Post-Processing

After upscaling, apply alpha transparency fixes:

```bash
# Fix object transparency (remove white backgrounds from RGB-only PNGs)
python3 scripts/add_object_alpha.py

# Build the object manifest
python3 scripts/build_object_map.py

# Apply ChaiKin alpha to costume borders
python3 scripts/apply_chaikin_alpha.py
```

---

## 4. Start the Game

### Directory Structure

```
comi_hd_v1.0.2/
├── game/
│   ├── COMI.LA0
│   ├── COMI.LA1
│   ├── COMI.LA2
│   └── RESOURCE/          # Extracted HD resources
├── hd/
│   ├── backgrounds/       # 4x upscaled backgrounds (2560×1920 PNGs)
│   ├── costumes/          # 25,303 HD costume frames
│   ├── videos/            # 15 upscaled cutscenes (MP4)
│   ├── objects/           # 600 HD objects
│   ├── objects_layers/    # Layer-separated objects
│   ├── fonts/             # 5 HD font sets
│   └── object_map.json    # Object manifest
├── scummvm.exe            # Windows binary (or scummvm for Linux)
├── SDL2.dll
├── zlib1.dll
├── scummvm.ini
├── start_comi_hd.bat      # Windows launcher
└── start_comi_hd.sh       # Linux launcher
```

### Windows

Double-click `start_comi_hd.bat` or run:

```cmd
scummvm.exe --config=scummvm.ini --auto-detect --renderer=opengl
```

### Linux

```bash
chmod +x scummvm start_comi_hd.sh
./start_comi_hd.sh
```

Or manually:

```bash
SDL_VIDEO_WINDOW_POS=50,50 ./scummvm \
  --config=scummvm.ini \
  --auto-detect \
  --renderer=opengl
```

### Headless / Server (No GPU)

```bash
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  ./scummvm --config=scummvm.ini --auto-detect --renderer=opengl
```

### Verify HD Mode

On successful start, the log should show:

```
WARNING: HDAssetManager: HD mode ENABLED at .../hd!
WARNING: HD mode enabled, scale=4, path=.../hd!
WARNING: HD: loaded bg for room XX (2560x1920) scale=4!
```

### Command Line Options

| Flag | Description |
|------|-------------|
| `--config=FILE` | Use custom config file |
| `--auto-detect` | Auto-detect game from current dir |
| `--boot-param=N` | Start directly in room N (debug) |
| `--renderer=opengl` | Force OpenGL renderer |
| `--window-size=WxH` | Window size (e.g. 1280x960) |

### INI Configuration (`scummvm.ini`)

```ini
[scummvm]
last_window_width=1280
last_window_height=960

[comi]
hd_path=./hd
```

---

## Troubleshooting

### "SCUMM v7-8 support is not compiled in"

Cause: The configure flag used `scumm_7_8` (underscore) instead of `scumm-7-8` (hyphen).

Fix: Reconfigure with `--enable-engine=scumm,scumm-7-8`, then `make clean && make -j$(nproc)`.

### Room warps to test room on start

Cause: Debug code sets `_hdDebugDumpCount = 9`, forcing all rooms to room 9.

Fix: Already removed in v1.0.2. Update to latest build.

### White outlines on objects

Cause: 24-bit RGB PNGs without alpha channel — the background color (254,254,254)
is not transparent.

Fix: Run `python3 scripts/add_object_alpha.py` to post-process the upscaled objects.

### Shadows are solid black instead of transparent

Cause: Shadow pixels are stored as pure black in the upscaled output without
alpha information.

Fix: Improve the post-processing pipeline to preserve alpha from the original
extraction.

---

## Files Modified from Vanilla ScummVM

| File | Change |
|------|--------|
| `engines/scumm/hd_asset_manager.h/cpp` | **New** — loads 4x PNGs, scales coordinates |
| `engines/scumm/hd_costume_manager.h/cpp` | **New** — HD costume compositing |
| `engines/scumm/hd_font_manager.h/cpp` | **New** — HD font rendering |
| `engines/scumm/hd_object_manager.h/cpp` | **New** — HD object compositing |
| `engines/scumm/hd_video_player.h/cpp` | **New** — ffmpeg pipe video player |
| `engines/scumm/scumm.h` | HD fields: `_hdAssetManager`, `_hdScale`, etc. |
| `engines/scumm/scumm.cpp` | HD init, debug dump, auto-start disabled |
| `engines/scumm/room.cpp` | HD background load, room-force disabled |
| `engines/scumm/gfx.cpp` | HD overlay compositing pipeline |
| `engines/scumm/module.mk` | Added HD manager `.o` files |
| `config.mk` / `config.mk.win` | `ENABLE_SCUMM_7_8 = 1`, OpenGL flags |
