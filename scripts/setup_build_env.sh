#!/usr/bin/env bash
# ScummVM COMI Upscaled - Build Environment Setup
#
# Sets up MSYS2 for building the ScummVM HD fork.
# Run this in an "MSYS2 MinGW64" terminal.
#
# Usage:
#   bash scripts/setup_build_env.sh
#
# After setup:
#   cd scummvm/fork
#   bash build.sh
#

set -e

echo "=== Updating MSYS2 ==="
pacman -Syu --noconfirm

echo "=== Installing MinGW64 toolchain ==="
pacman -S --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-make

echo "=== Installing ScummVM build dependencies ==="
pacman -S --noconfirm \
  mingw-w64-x86_64-SDL2 \
  mingw-w64-x86_64-libpng \
  mingw-w64-x86_64-zlib \
  mingw-w64-x86_64-freetype \
  mingw-w64-x86_64-libvorbis \
  mingw-w64-x86_64-libogg \
  mingw-w64-x86_64-flac \
  mingw-w64-x86_64-libmad \
  mingw-w64-x86_64-libtheora \
  mingw-w64-x86_64-faad2 \
  mingw-w64-x86_64-curl \
  mingw-w64-x86_64-fluidsynth \
  mingw-w64-x86_64-fribidi

echo ""
echo "=== DONE ==="
echo ""
echo "Build the fork:"
echo "  cd <repo>/scummvm/fork"
echo "  bash build.sh"
echo ""
echo "Run the game:"
echo "  export PATH=/mingw64/bin:/usr/bin:\$PATH"
echo "  ./scummvm.exe --path=../../game"
echo ""
