# COMI-HD — Build Guide

The build system is in the `build/` directory. See [`build/BUILD.md`](../build/BUILD.md)
for the complete build documentation.

## Quick Start

```bash
# Install system build tools (Ubuntu/Debian)
sudo apt install build-essential cmake pkg-config curl

# Build both Linux + Windows binaries
bash build/build-all.sh

# Build just the Linux binary
bash build/build-all.sh linux

# Build just the Windows binary (cross-compile from Linux)
bash build/build-all.sh windows
```

**Build artifacts appear in `build/out/`:**
- `build/out/scummvm` — Linux binary
- `build/out/scummvm.exe` — Windows binary

The build system downloads all dependencies (LLVM MinGW toolchain, SDL2 source,
zlib, libpng) from their official sources — no system packages beyond the
basic C++ compiler are needed. See `build/BUILD.md` for details.
