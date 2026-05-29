#!/usr/bin/env bash
# Build the ScummVM COMI Upscaled fork.
# Handles the MSYS2 sed 4.9 bug workaround automatically.
#
# Usage:
#   cd <repo>/scummvm/fork
#   bash build.sh
#
# Requirements: MSYS2 MinGW64 toolchain installed.

set -e

# Ensure MinGW64 tools are in PATH
export PATH="/mingw64/bin:/usr/bin:$PATH"

# MSYS2 temp directory fix (prevents "Cannot create temporary file in C:\WINDOWS\")
export TMP="/tmp"
export TEMP="/tmp"
mkdir -p /tmp

echo "=== Building ScummVM HD Fork ==="

# Workaround for MSYS2 sed 4.9 bug (crashes on Makefile.common sed patterns)
# Generate the resource header files first, then compile manually
mkdir -p dists dists/.deps
mingw32-make -j$(nproc) \
  dists/scummvm_rc_engine_data_core.rh \
  dists/scummvm_rc_engine_data.rh \
  dists/scummvm_rc_engine_data_big.rh \
  2>/dev/null || true

# Compile the resource file manually (avoids the broken sed dependency rule)
windres -DHAVE_CONFIG_H -DRELEASE_BUILD -DWIN32 -DSDL_BACKEND -DUSE_SDL2 \
  -I. -I./engines -I./base \
  dists/scummvm.rc -o dists/scummvm.o 2>/dev/null || true

# Full build
mingw32-make -j$(nproc)

echo ""
echo "=== Build complete ==="
ls -la scummvm.exe
