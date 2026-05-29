# Building the ScummVM HD Fork

## Prerequisites

### MSYS2 + MinGW (recommended on Windows)

1. Download and install MSYS2 from https://www.msys2.org/
2. Open "MSYS2 MinGW x64" terminal
3. Update and install build tools:

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

### Visual Studio 2022 (alternative)

- VS2022 with "Desktop development with C++"
- Use `dists/msvc/scummvm.sln`

## Get the Source

```bash
# Clone ScummVM (shallow is fine)
git clone --depth 1 --single-branch https://github.com/scummvm/scummvm.git
cd scummvm

# Download the COMI HD fork patches from our repo
curl -O https://raw.githubusercontent.com/harrytyp/comiupscale/main/patches/scumm-hd-fork.patch
curl -O https://raw.githubusercontent.com/harrytyp/comiupscale/main/patches/hd_asset_manager.h
curl -O https://raw.githubusercontent.com/harrytyp/comiupscale/main/patches/hd_asset_manager.cpp

# Apply the patch
git apply scumm-hd-fork.patch
mv hd_asset_manager.h engines/scumm/
mv hd_asset_manager.cpp engines/scumm/
```

## Configure

From the MSYS2 MINGW64 terminal:

```bash
export CC=gcc CXX=g++
./configure --host=mingw64 --backend=sdl \
  --enable-optimizations --enable-release \
  --disable-all-engines --enable-engine=scumm
```

**Important:** After configure, verify `config.mk` has:
```
ENABLE_SCUMM_7_8 = 1
```
If it's commented out (`# ENABLE_SCUMM_7_8`), uncomment it.

## Build

```bash
# Build with 12 parallel jobs (adjust for your CPU)
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

## Files Modified

| File | Change |
|------|--------|
| `engines/scumm/hd_asset_manager.h` | **New** — HD asset manager header |
| `engines/scumm/hd_asset_manager.cpp` | **New** — loads 4x PNGs via Image::PNGDecoder |
| `engines/scumm/scumm.h` | Added `_hdAssetManager`, `_hdScale`, `_hdBackgroundSurface`, `_hdCurrentRoom` |
| `engines/scumm/scumm.cpp` | Init HD path in `init()`, constructor/destructor |
| `engines/scumm/room.cpp` | HD background load in `startScene()` after room setup |
| `engines/scumm/gfx.cpp` | HD overlay in `drawDirtyScreenParts()` via `lockScreen()` |
| `engines/scumm/module.mk` | Added `hd_asset_manager.o` |
