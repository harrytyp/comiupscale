#!/usr/bin/env bash
# ScummVM COMI Upscaled - Build Environment Setup for GPU Computer
#
# Step 1: Install MSYS2
#   Download from https://www.msys2.org/ and run the installer
#   Use defaults (install to C:\msys64)
#
# Step 2: Open "MSYS2 MinGW64" from Start Menu
#   Then paste and run the commands below:
#
# ============================================================================

set -e

echo "=== Updating MSYS2 ==="
pacman -Syu --noconfirm

echo "=== Installing MinGW64 toolchain ==="
pacman -S --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-make

echo "=== Installing ScummVM libraries ==="
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
  mingw-w64-x86_64-faad2

echo ""
echo "=== DONE ==="
echo ""
echo "Now extract the fork and build:"
echo ""
echo "  cd /c/Users/<yourname>"
echo '  tar xzf "scummvm-fork.tar.gz"'
echo '  cd scummvm/fork'
echo '  mingw32-make -j$(nproc)'
echo ""
echo "  # Build (from MSYS2 MinGW64 terminal):"
echo '  PATH="/mingw64/bin:/usr/bin:$PATH" mingw32-make -j$(nproc)'
echo ""
echo "  # Run:"
echo '  PATH="/mingw64/bin:/usr/bin:$PATH" ./scummvm.exe --path=game'
