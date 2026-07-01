# COMI-HD — Build, Extract, Upscale & Deploy

This document records the **actual build process** used to produce the
v1.0.2 release. All paths, commands, and tools are the ones that were
executed — not generic examples.

---

## 1. Build the ScummVM HD Fork

### 1.1 LLVM MinGW Cross-Compile (Windows Binary)

Used to build `scummvm.exe` for Windows from a Linux host.

**Toolchain:** [llvm-mingw](https://github.com/mstorsjo/llvm-mingw) 20260616
(UCRT, Ubuntu 22.04 x86_64)

**Dependencies (pre-extracted):**
- `/tmp/mingw_prefix/` — zlib, libpng compiled for mingw
- `/tmp/sdl2_mingw/SDL2-2.30.11/x86_64-w64-mingw32/` — SDL2 for mingw

**Build steps:**

```bash
export PATH="/tmp/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64/bin:$PATH"
export PKG_CONFIG_LIBDIR=

cd scummvm/fork

# Clean slate (if rebuilding)
make clean

# Configure — IMPORTANT: use scumm-7-8 (hyphen), NOT scumm_7_8 (underscore)!
./configure --host=x86_64-w64-mingw32 \
  --with-zlib-prefix=/tmp/mingw_prefix \
  --with-png-prefix=/tmp/mingw_prefix \
  --with-sdl-prefix=/tmp/sdl2_mingw/SDL2-2.30.11/x86_64-w64-mingw32 \
  --opengl-mode=gl \
  --enable-verbose-build \
  --disable-nasm \
  --disable-all-engines \
  --enable-engine=scumm,scumm-7-8

# Verify scumm_7_8 is enabled
grep -E "ENABLE_SCUMM" config.mk
# Expected output:
#   ENABLE_SCUMM = STATIC_PLUGIN
#   ENABLE_SCUMM_7_8 = 1

# Build (parallel)
make -j$(nproc)
```

**Expected result:** `scummvm.exe` (~84 MB).

**Verify the binary has scumm_7_8:**
```bash
strings scummvm.exe | grep "ScummEngine_v7"
# Should show many occurrences

strings scummvm.exe | grep "SCUMM \[v0-v6"
# Should show: SCUMM [v0-v6 games, v7 & v8 games]
```

**Verify the binary does NOT have debug auto-warp:**
```bash
# Run the binary — it should stay in the launcher, not jump to room 9
# The HD debug auto-start code is disabled (if (false && ...))
```

### 1.2 Linux Native Build

```bash
cd scummvm/fork

# SDL2-config must be in PATH
export PATH="/opt/data/local/bin:$PATH"

./configure --opengl-mode=gl \
  --enable-verbose-build \
  --disable-all-engines \
  --enable-engine=scumm,scumm-7-8

make -j$(nproc)
```

**Note:** Requires `libsdl2-dev` and `libx11-dev` for the SDL backend.
On headless systems, use Mesa LLVMpipe:
```bash
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe ./scummvm
```

### 1.3 Windows (MSYS2 Native Build)

Not used for v1.0.2, but documented for reference:

```bash
cd scummvm/fork
export CC=gcc CXX=g++
./configure --host=mingw64 --backend=sdl \
  --enable-optimizations --enable-release \
  --disable-all-engines --enable-engine=scumm,scumm-7-8
mingw32-make -j12
```

### 1.4 Critical: `scumm-7-8` vs `scumm_7_8`

| Flag | Effect |
|------|--------|
| `--enable-engine=scumm,scumm-7-8` | ✅ **Works** — `ENABLE_SCUMM_7_8 = 1` in config.mk |
| `--enable-engine=scumm,scumm_7_8` | ❌ **Silently ignored** — only v0-v6 built |

The configure script uses **hyphen** (`scumm-7-8`), not underscore.
The underscore variant is silently accepted but does nothing — there's
no error message. Always verify with:

```bash
grep "ENABLE_SCUMM_7_8" config.mk
# Must show: ENABLE_SCUMM_7_8 = 1 (not commented out)
```

---

## 2. Extract Game Assets

### 2.1 Requirements

```bash
pip install numpy pillow parse deal
```

NUTcracker Python source is at `tools/nutcracker/src/`.

### 2.2 Extract All Assets

```bash
cd scripts
bash export_all.sh
```

### 2.3 Extract Costumes (AKOS Frames)

The NUTcracker AKOS decoder is at `tools/nutcracker/src/nutcracker/sputm/costume/akos.py`.
It was patched to use the **room palette** (APAL, 256-color, 768 bytes from
ROOM/PALS/WRAP/APAL) instead of the 16-color RGBS table for correct colors.

```bash
PYTHONPATH=tools/nutcracker/src python3 -m nutcracker.sputm.costume.akos COMI.LA0
```

**Results:** 25,304 costume frames. Notable fix: `npp.resize()` in graphics/image.py
does not modify in-place — must use `npp = npp.reshape()` (critical bug that
was producing black frames).

### 2.4 Extraction Output Structure

```
CMI UPSCALED/extracted/COMI/
├── IMAGES/
│   ├── backgrounds/       # 40 room backgrounds (8-bit palette PNGs)
│   ├── objects/            # 600 OBIM objects (8-bit palette PNGs)
│   └── objects_layers/    # 234 layer-separated objects
├── costuumes/             # 25,304 AKOS frames (BMP/PNG)
├── cutscenes/             # 12,506 frames across 15 cutscenes
└── fonts/                 # 5 font sets
```

---

## 3. Upscale Assets

### 3.1 RealESRGAN Upscaling

Uses [RealESRGAN](https://github.com/xinntao/RealESRGAN) with the
**`x4plus_anime_6B`** model (6-block RRDBNet architecture).

**Critical model detail:** The `x4plus_anime_6B` model uses `* 0.2` residual
scaling factor. Without it, weights produce ±trillions. Weight mapping:
- `body` → `trunk`
- `conv_trunk` → `trunk_conv`
- `conv_up1` → `upconv1`
- `conv_up2` → `upconv2`
- `conv_hr` → `hr_conv`
- `conv_last` → `final_conv`

Always use `strict=True` when loading state dict.

```bash
# Upscale all costumes
python3 scripts/batch_upscale_costumes.py

# Upscale a single room's assets
python3 scripts/upscale_room9.py

# Batch upscale via shell script
bash hd_config/batch_upscale.sh
```

### 3.2 Post-Processing

After upscaling, objects need alpha transparency fixes because RealESRGAN
outputs 24-bit RGB PNGs without alpha. The fix detects border pixels matching
the original background color and makes them transparent.

```bash
# Fix object transparency (removes white/light-gray borders)
python3 scripts/add_object_alpha.py

# Apply ChaiKin blending for smoother costume edges
python3 scripts/apply_chaikin_alpha.py

# Build the object manifest
python3 scripts/build_object_map.py
```

**Alpha handling for objects:**
- `loadPNG()` must respect existing alpha channel when `bytesPerPixel == 4`
- For RGB-only PNGs: detect border color by examining corner pixels,
  then set all matching pixels to transparent (corner-sampling)
- HD object PNGs in `objects/` are RGB without alpha — loaded via
  `GALLIUM_DRIVER=llvmpipe` OpenGL path

### 3.3 HD Backgrounds

81 backgrounds at 2560×1920 (4x original 640×480), placed in `hd/backgrounds/`
named `bg_{room:04d}.png` (e.g. `bg_0009.png` for room 9).

---

## 4. Assemble Release

### 4.1 Release Directory Structure

```
/tmp/comi_hd_complete/comi_hd_v1.0.2/
├── game/
│   ├── COMI.LA0           # Original game data file 0
│   ├── COMI.LA1           # Original game data file 1
│   └── COMI.LA2           # Original game data file 2
│   └── RESOURCE/          # Extracted resources (25 files, ~915 MB)
├── hd/
│   ├── backgrounds/       # 81 HD backgrounds (2560×1920)
│   ├── costumes/          # 25,302 HD costume frames
│   ├── videos/            # 15 upscaled cutscenes (MP4)
│   ├── objects/           # 600 HD objects
│   ├── objects_layers/    # Layer-separated objects
│   ├── fonts/             # 5 HD font sets
│   └── object_map.json    # Object→HD mapping manifest
├── scummvm.exe            # ~84 MB Windows binary (scumm_7_8 enabled)
├── scummvm                 # ~65 MB Linux binary
├── scummvm.ini
├── SDL2.dll               # 1.7 MB SDL2 runtime
├── zlib1.dll              # 100 KB zlib runtime
├── start_comi_hd.bat      # Windows launcher
├── start_comi_hd.sh       # Linux launcher
└── RELEASE_README.md
```

### 4.2 Copy New Binary After Rebuild

```bash
cp scummvm/fork/scummvm.exe /tmp/comi_hd_complete/scummvm.exe
cp scummvm/fork/scummvm /tmp/comi_hd_complete/scummvm
```

### 4.3 GitHub Release (Upload)

```bash
# Upload all 8 assets to the release
gh release upload v1.0.2 \
  /tmp/release_zips/comi_hd_game.zip \
  /tmp/release_zips/comi_hd_build.zip \
  /tmp/hd_zips/hd_assets_part1.zip \
  /tmp/hd_zips/hd_assets_part2.zip \
  /tmp/hd_zips/hd_assets_part3.zip \
  /tmp/hd_zips/hd_assets_part4.zip \
  /tmp/hd_zips/hd_assets_part5.zip \
  /tmp/hd_zips/hd_assets_part6.zip \
  --clobber
```

HD assets are split into 6 ZIPs (max 1.9 GB each) to stay under GitHub's 2 GB per-file limit. All 6 must be extracted into the same directory.

### 4.4 GitHub Release (Create)

```bash
# Tag and create release
gh release create v1.0.2 \
  --title "COMI-HD v1.0.2" \
  --repo harrytyp/comiupscale \
  --notes "..." \
  /tmp/release_zips/comi_hd_game.zip \
  /tmp/release_zips/comi_hd_build.zip
```

### 4.5 NAS Copy (SMB)

```bash
# Mount SMB share
mount -t cifs //192.168.2.152/kolja /mnt/nas \
  -o username=kolja,password=forever

cp -r /tmp/comi_hd_complete/* /mnt/nas/comi_hd_v1.0.2/
```

---

## 5. Start the Game

### 5.1 Windows

Double-click `start_comi_hd.bat` or run:

```cmd
scummvm.exe --config=scummvm.ini --auto-detect --renderer=opengl
```

### 5.2 Linux

```bash
chmod +x scummvm start_comi_hd.sh
./start_comi_hd.sh
```

### 5.3 Headless (Docker / Server)

```bash
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  SDL_VIDEO_WINDOW_POS=50,50 \
  ./scummvm --config=scummvm.ini --auto-detect --renderer=opengl
```

**Required for ScummVM HD mode under Docker:**
- Mesa LLVMpipe for software OpenGL
- NEVER disable OpenGL backend — the SDL software renderer asserts
  `bytesPerPixel==1` in `setPalette()` and crashes with 32-bit RGBA screens

### 5.4 Screenshots / Verification

ScummVM renders off-screen via OpenGL — Xvfb/Xlib screenshots produce
black frames. Use the **Composite Dump** feature:

```bash
# Enable one-shot dump in scumm.cpp: _hdDebugDumpCount = <room_number>
# Rebuild, then check logs/ for:
#   hd_dump_<frame>_composite.raw  (2560×1920 RGBA)
#   hd_dump_<frame>_hdcomposite.raw (HD overlay only)
#   hd_dump_<frame>_sdcomposite.raw (SD reference)

# Convert to PNG with PIL:
python3 -c "
import numpy as np
from PIL import Image
raw = np.fromfile('hd_dump_1_composite.raw', dtype=np.uint8).reshape(1920, 2560, 4)
Image.fromarray(raw[:,:,:3][:,:,::-1]).save('screenshot.png')
"
```

---

## 6. Known Issues & Workarounds

### 6.1 White Borders on Objects
**Cause:** 24-bit RGB PNGs from RealESRGAN have no alpha. Border pixels
matching the original background (r,g,b > 230) aren't transparent.

**Fix:** `python3 scripts/add_object_alpha.py`

### 6.2 "SCUMM v7-8 support is not compiled in"
**Cause:** `--enable-engine=scumm_7_8` (underscore) instead of
`--enable-engine=scumm,scumm-7-8` (hyphen).

**Fix:** Reconfigure with correct flag, `make clean && make -j$(nproc)`.

### 6.3 Room Warps to Test Room on Start
**Cause:** Debug code in `scumm.cpp` sets `_hdDebugDumpCount = 9`,
and `room.cpp` forces room 9 for HD testing.

**Fix:** Both disabled with `if (false && ...)` guards in v1.0.2.

### 6.4 `zip` command not available
**Workaround:** Use Python `zipfile` module:
```python
import zipfile, os
with zipfile.ZipFile('output.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('input_dir'):
        for f in files:
            z.write(os.path.join(root, f),
                    os.path.relpath(os.path.join(root, f), 'input_dir'))
```

---

## 7. Files Modified from Upstream ScummVM

| File | Change |
|------|--------|
| `engines/scumm/hd_asset_manager.h/cpp` | **New** — 4x PNG loader, coordinate scaling |
| `engines/scumm/hd_costume_manager.h/cpp` | **New** — HD costume compositing |
| `engines/scumm/hd_font_manager.h/cpp` | **New** — HD font rendering |
| `engines/scumm/hd_object_manager.h/cpp` | **New** — HD object compositing |
| `engines/scumm/hd_video_player.h/cpp` | **New** — ffmpeg pipe player |
| `engines/scumm/scumm.h` | Added `_hdAssetManager`, `_hdScale`, etc. |
| `engines/scumm/scumm.cpp` | HD init, auto-start new game (disabled) |
| `engines/scumm/room.cpp` | HD background load, room-force (disabled) |
| `engines/scumm/gfx.cpp` | HD overlay, debug dump, SD-vs-HD diff |
| `engines/scumm/module.mk` | Added HD manager `.o` files |
| `config.mk.win` | Reference Windows config with `scumm-7-8` |
| `config.mk.linux` | Reference Linux config |
| `scripts/full_pipeline.sh` | Full build + deploy pipeline |
