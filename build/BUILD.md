# COMI-HD — Build Guide

This document explains how to build the ScummVM HD fork from source.
The build system is fully automated — no system packages beyond the
basic C++ toolchain are required.

---

## Quick Start

```bash
# 1. Install system build tools (Ubuntu/Debian)
sudo apt install build-essential cmake pkg-config curl

# 2. Build everything (Linux + Windows binaries)
bash build/build-all.sh

# 3. Build just the Linux binary
bash build/build-all.sh linux

# 4. Build just the Windows binary (cross-compile from Linux)
bash build/build-all.sh windows
```

**Build artifacts:**
- `build/out/scummvm` — Linux binary
- `build/out/scummvm.exe` — Windows binary

---

## What the Build Script Does

The build system (`build/`) is fully **self-contained** — it downloads and
builds every dependency from source:

| Step | What | For |
|------|------|-----|
| 1 | Downloads LLVM MinGW toolchain | Windows cross-compile |
| 1 | Downloads SDL2 source | Both |
| 1 | Downloads zlib + libpng source | Windows cross-compile |
| 2 | Builds SDL2 from source | Linux native |
| 3 | Builds SDL2 from source (MinGW) | Windows cross-compile |
| 4 | Builds zlib + libpng (MinGW) | Windows cross-compile |
| 5 | Builds ScummVM | Linux + Windows |

### Dependency Cache

All downloaded tarballs go to `build/deps/` and all built libraries go to
`build/install/`. Subsequent runs are incremental — already-built
components are skipped.

To force a clean rebuild:
```bash
rm -rf build/deps build/install build/out
bash build/build-all.sh
```

---

## Detailed Build Steps

### 1. System Requirements

| Tool | Purpose | Install (Debian/Ubuntu) |
|------|---------|------------------------|
| gcc, g++ | C++ compiler | `sudo apt install build-essential` |
| cmake | Build system generator | `sudo apt install cmake` |
| pkg-config | Library detection | `sudo apt install pkg-config` |
| make | Build orchestrator | (included in build-essential) |
| curl | File download | `sudo apt install curl` |

**Note:** The build script builds SDL2 from source using cmake. If SDL2
development headers are already installed on your system (from
`libsdl2-dev`), the script will detect and use them instead.

### 2. Linux Build

```bash
bash build/build-all.sh linux
```

This will:
1. Check for SDL2 on the system (via `pkg-config` or `sdl2-config`)
2. If not found, build SDL2 from source into `build/install/sdl2-native/`
3. Configure ScummVM with only the SCUMM v7-8 engine enabled
4. Run `make` with parallel jobs
5. Copy the binary to `build/out/scummvm`

### 3. Windows Build (Cross-Compile from Linux)

```bash
bash build/build-all.sh windows
```

This will:
1. Download the LLVM MinGW toolchain (170 MB) to `build/deps/`
2. Download and build SDL2 for MinGW to `build/install/sdl2-mingw/`
3. Download and build zlib + libpng for MinGW to `build/install/mingw-prefix/`
4. Configure ScummVM with MinGW cross-compilation
5. Build and strip the Windows binary
6. Copy the binary to `build/out/scummvm.exe`

### 4. Complete Build

```bash
bash build/build-all.sh
```

Runs both the Linux and Windows builds sequentially.

---

## File Structure

```
build/
├── build-all.sh                # Main entry point
├── _common.sh                  # Shared functions (paths, colors, helpers)
├── _build-sdl2-native.sh       # Build SDL2 for Linux
├── _build-sdl2-mingw.sh        # Build SDL2 for Windows cross-compile
├── _build-mingw-libs.sh        # Build zlib + libpng for Windows cross-compile
├── _build-scummvm-linux.sh     # Configure + make ScummVM (Linux)
├── _build-scummvm-windows.sh   # Configure + make ScummVM (Windows)
├── _toolchain-mingw.cmake      # CMake toolchain file for MinGW
├── deps.list                   # URL manifest of all dependencies
├── deps/                       # Downloaded source tarballs + extracted sources
├── install/                    # Built libraries (SDL2, zlib, libpng)
└── out/                        # Build artifacts (scummvm, scummvm.exe)
```

---

## Verify the Build

### Check scumm_7_8 engine is included

```bash
# Linux
strings build/out/scummvm | grep "SCUMM \[v0-v6"
# Should show: SCUMM [v0-v6 games, v7 & v8 games]

# Windows
strings build/out/scummvm.exe | grep "ScummEngine_v7" | head -3
```

### Quick launch test (Linux, requires game data)

```bash
# Without HD assets:
./build/out/scummvm --path=/path/to/COMI/game

# With HD assets (place hd/ directory next to game data):
./build/out/scummvm --path=/path/to/COMI/game --renderer=opengl
```

### Headless/server launch

```bash
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  SDL_VIDEO_WINDOW_POS=50,50 \
  ./build/out/scummvm --path=/path/to/COMI/game --renderer=opengl
```

---

## Troubleshooting

### "SDL2 not found"

The Linux build tries to find SDL2 on your system first. If it fails:
```bash
# Option A: Install system SDL2
sudo apt install libsdl2-dev

# Option B: Let the build script build it from source (automatic)
# Just ensure cmake is installed: sudo apt install cmake
```

### "Missing: x86_64-w64-mingw32-g++"

The Windows build needs the LLVM MinGW toolchain. The build script
downloads it automatically, but ensure you have ~500 MB free disk space.

### "SCUMM v7-8 support is not compiled in"

The configure flag `--enable-engine=scumm,scumm-7-8` uses a **hyphen**
(`scumm-7-8`), not underscore. The underscore variant is silently ignored.
The build scripts use the correct flag.

### Build fails with missing OpenGL

The ScummVM HD fork requires OpenGL for rendering. Install Mesa dev headers:
```bash
sudo apt install libgl-dev libglu1-mesa-dev
```

For headless/CI environments, software rendering via LLVMpipe also works:
```bash
sudo apt install mesa-utils libgl1-mesa-dri
# Then run with: LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
```
