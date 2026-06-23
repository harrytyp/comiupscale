# Building the ScummVM HD Fork

Cross-platform build for **Windows** (MSYS2) and **Linux/macOS**.

## Quick Start (Recommended)

The fork includes pre-configured source files — no patching needed:

```bash
# Clone the repo
git clone https://github.com/harrytyp/comiupscale.git
cd comiupscale/scummvm/fork

# Auto-detect platform and build
bash build.sh
```

## Prerequisites

### Linux (Ubuntu/Debian)

```bash
sudo apt install build-essential pkg-config \
  libsdl2-dev libfreetype-dev libpng-dev \
  libvorbis-dev libflac-dev libgl-dev \
  libglu1-mesa-dev libjpeg-dev zlib1g-dev
```

### Linux (Fedora/RHEL)

```bash
sudo dnf groupinstall 'Development Tools'
sudo dnf install SDL2-devel freetype-devel libpng-devel \
  libvorbis-devel flac-devel mesa-libGL-devel \
  mesa-libGLU-devel libjpeg-turbo-devel zlib-devel
```

### Linux (Arch)

```bash
sudo pacman -S base-devel pkgconf sdl2 freetype2 libpng \
  libvorbis flac mesa libglvnd
```

### Windows (MSYS2 — recommended)

1. Download and install MSYS2 from https://www.msys2.org/
2. Open "MSYS2 MinGW x64" terminal
3. Install build tools:

```bash
pacman -Syu
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-make \
          mingw-w64-x86_64-cmake mingw-w64-x86_64-SDL2 \
          mingw-w64-x86_64-freetype mingw-w64-x86_64-libpng \
          mingw-w64-x86_64-zlib mingw-w64-x86_64-flac \
          mingw-w64-x86_64-libmad mingw-w64-x86_64-libvorbis \
          mingw-w64-x86_64-libtheora mingw-w64-x86_64-fluidsynth \
          mingw-w64-x86_64-faad2 mingw-w64-x86_64-libjpeg-turbo \
          git diffutils
```

### Windows (Visual Studio 2022 — alternative)

- VS2022 with "Desktop development with C++"
- Use `dists/msvc/scummvm.sln`

## Manual Build (Advanced)

If you prefer manual control, or if `build.sh` doesn't work for your setup:

### Linux

```bash
cd scummvm/fork

# Configure (only SCUMM engine)
./configure --backend=sdl \
  --enable-optimizations --enable-release \
  --disable-all-engines --enable-engine=scumm

# Verify SCUMM v7/8 support
grep "ENABLE_SCUMM_7_8" config.mk
# Should show: ENABLE_SCUMM_7_8 = 1

# Build
make -j$(nproc)
```

### Windows (MSYS2)

```bash
cd scummvm/fork

# Configure
export CC=gcc CXX=g++
./configure --host=mingw64 --backend=sdl \
  --enable-optimizations --enable-release \
  --disable-all-engines --enable-engine=scumm

# Verify
grep "ENABLE_SCUMM_7_8" config.mk

# Build
mingw32-make -j12
```

**Note:** If the build fails on `dists/scummvm.o` with a sed error about an
"unterminated s command", it's a known MSYS2 GNU sed 4.9 issue. Workaround:

```bash
# Generate dependency files first
mingw32-make -j12 dists/scummvm_rc_engine_data_core.rh \
  dists/scummvm_rc_engine_data.rh \
  dists/scummvm_rc_engine_data_big.rh

# Touch the object file so make skips it
touch dists/scummvm.o dists/.deps/scummvm.d

# Then build normally
mingw32-make -j12
```

## Configure Options

After `./configure`, verify `config.mk` has these enabled:

```makefile
USE_OPENGL = 1
USE_OPENGL_GAME = 1
USE_OPENGL_SHADERS = 1
ENABLE_SCUMM_7_8 = 1
```

If `ENABLE_SCUMM_7_8` is commented out, uncomment it:
```bash
sed -i 's/^# ENABLE_SCUMM_7_8/ENABLE_SCUMM_7_8/' config.mk
```

## Set Up HD Assets

```bash
# Create HD directory next to game data
mkdir -p /path/to/game/hd

# Place 4x upscaled backgrounds named bg_XXXX.png
# Example: room 19 (the stage) → bg_0019.png
cp /path/to/upscaled/backgrounds/0019_stage.png /path/to/game/hd/bg_0019.png
```

## Run

```bash
# Linux
./scummvm --path=/path/to/game

# Windows
./scummvm.exe --path=/path/to/game
```

On first run, you should see warnings confirming HD mode:
```
WARNING: HDAssetManager: HD mode ENABLED at .../hd!
WARNING: HD mode enabled, scale=4, path=.../hd!
```

When entering a room with an HD background:
```
WARNING: Loaded HD background for room 19 (2560x1920)
```

## Headless/Server Rendering (No GPU)

For running on a server without a GPU, use Mesa LLVMpipe:

```bash
# Install Mesa software renderer
sudo apt install mesa-utils libgl1-mesa-dri

# Run with software OpenGL
LIBGL_ALWAYS_SOFTWARE=1 ./scummvm --path=/path/to/game
```

## Video Player Support

The HD video player (MP4 replacement for cutscenes) works on:
- **Windows**: CreateProcess + pipe (full support)
- **Linux/macOS**: popen + fread (full support)

Requires `ffmpeg` in PATH. Set custom path in ScummVM config:
```
[comi]
ffmpeg_path=/usr/bin/ffmpeg
```

## Files Modified from Vanilla ScummVM

| File | Change |
|------|--------|
| `engines/scumm/hd_asset_manager.h` | **New** — HD asset manager header |
| `engines/scumm/hd_asset_manager.cpp` | **New** — loads 4x PNGs via Image::PNGDecoder |
| `engines/scumm/hd_costume_manager.h` | **New** — HD costume manager header |
| `engines/scumm/hd_costume_manager.cpp` | **New** — HD costume compositing |
| `engines/scumm/hd_font_manager.h` | **New** — HD font manager header |
| `engines/scumm/hd_font_manager.cpp` | **New** — HD font rendering |
| `engines/scumm/hd_object_manager.h` | **New** — HD object manager header |
| `engines/scumm/hd_object_manager.cpp` | **New** — HD object compositing |
| `engines/scumm/hd_video_player.h` | **New** — HD video player header (cross-platform) |
| `engines/scumm/hd_video_player.cpp` | **New** — ffmpeg pipe player (Windows + POSIX) |
| `engines/scumm/scumm.h` | Added `_hdAssetManager`, `_hdScale`, `_hdBackgroundSurface`, `_hdCurrentRoom` |
| `engines/scumm/scumm.cpp` | Init HD path in `init()`, constructor/destructor |
| `engines/scumm/room.cpp` | HD background load in `startScene()` after room setup |
| `engines/scumm/gfx.cpp` | HD overlay in `drawDirtyScreenParts()` via `lockScreen()` |
| `engines/scumm/module.mk` | Added `hd_asset_manager.o`, `hd_costume_manager.o`, `hd_font_manager.o`, `hd_object_manager.o`, `hd_video_player.o` |
| `config.mk` | `USE_OPENGL = 1`, `ENABLE_SCUMM_7_8 = 1` |
