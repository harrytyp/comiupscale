# Building the ScummVM HD Fork

## Prerequisites

### Option A: MSYS2 + MinGW (recommended)

1. Download and install MSYS2 from https://www.msys2.org/
2. Open "MSYS2 MinGW x64" terminal
3. Install build dependencies:

```bash
pacman -Syu
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake \
          mingw-w64-x86_64-sdl2 mingw-w64-x86_64-freetype \
          mingw-w64-x86_64-libpng mingw-w64-x86_64-zlib \
          mingw-w64-x86_64-flac mingw-w64-x86_64-mad \
          mingw-w64-x86_64-vorbis mingw-w64-x86_64-theora \
          mingw-w64-x86_64-fluidsynth mingw-w64-x86_64-faad \
          make git
```

### Option B: Visual Studio 2022

- Install VS2022 with "Desktop development with C++"
- ScummVM ships `dists/msvc/scummvm.sln` — open and build
- Requires vcpkg for dependencies or use the prebuilt libs from ScummVM's site

## Clone

The ScummVM repo is ~800MB with 23K+ files. Clone locally (not on NAS),
then reference from the project.

```bash
# Clone to local SSD (fast)
git clone --depth 1 --single-branch https://github.com/scummvm/scummvm.git \
  /c/Users/go75bel/scummvm-fork

# Navigate to work
cd /c/Users/go75bel/scummvm-fork
```

## Configure

```bash
# MinGW
./configure --backend=sdl --enable-optimizations --enable-release

# Or with debug symbols for development
./configure --backend=sdl --enable-optimizations --enable-debug
```

## Build

```bash
# MinGW
make -j$(nproc)

# The binary will be at: scummvm-fork/scummvm.exe
```

## Testing

```bash
# Point the fork at our game data
./scummvm.exe --path=/z/Projekte/COMI-Upscaled/ScummVM/monkey3

# Or copy the binary to ScummVM/ and run from there
cp scummvm.exe /z/Projekte/COMI-Upscaled/ScummVM/
```

## HD Test Structure

Place HD backgrounds:

```
/z/Projekte/COMI-Upscaled/ScummVM/monkey3/hd/
├── bg_0019.png    # stage room (already upscaled via RealESRGAN)
└── hd_manifest.json
```

The first test: load room 19 (the stage) and verify the HD background
renders at 2560x1920 with actors in correct positions.
