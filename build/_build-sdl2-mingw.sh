#!/usr/bin/env bash
# ============================================================
# Build SDL2 from source for MinGW cross-compile
# Output: build/install/sdl2-mingw/
# Uses: build/install/llvm-mingw/ toolchain
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Check if SDL2-mingw already built
if [ -f "$SDL2_MINGW_DIR/lib/libSDL2.a" ] || [ -f "$SDL2_MINGW_DIR/lib/libSDL2.dll.a" ]; then
    info "SDL2 (MinGW) already built — skipping"
    exit 0
fi

# Verify LLVM MinGW toolchain
LLVM_TOOLCHAIN="$LLVM_MINGW_DIR/bin"
if [ ! -f "$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++" ]; then
    err "LLVM MinGW toolchain not found at $LLVM_MINGW_DIR"
    err "Run build-all.sh first or ensure the toolchain is downloaded"
    exit 1
fi

SDL2_SRC="$DEPS_DIR/$DEP_SDL2_DIR"

if [ ! -d "$SDL2_SRC" ]; then
    err "SDL2 source not found at $SDL2_SRC"
    exit 1
fi

mkdir -p "$SDL2_MINGW_DIR"

# Add LLVM MinGW to PATH
export PATH="$LLVM_TOOLCHAIN:$PATH"

BUILD_DIR_SDL2="$SDL2_SRC/build-mingw"
mkdir -p "$BUILD_DIR_SDL2"

info "Configuring SDL2 (MinGW cross-compile)..."
cd "$BUILD_DIR_SDL2"
cmake "$SDL2_SRC" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$SDL2_MINGW_DIR" \
    -DCMAKE_SYSTEM_NAME=Windows \
    -DCMAKE_SYSTEM_PROCESSOR=x86_64 \
    -DCMAKE_C_COMPILER="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-gcc" \
    -DCMAKE_CXX_COMPILER="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++" \
    -DCMAKE_RC_COMPILER="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-windres" \
    -DCMAKE_FIND_ROOT_PATH="$LLVM_MINGW_DIR/x86_64-w64-mingw32" \
    -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
    -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
    -DSDL_X11=OFF \
    -DSDL_WAYLAND=OFF \
    -DSDL_VIDEO_DRIVER_WINDOWS=ON \
    -DSDL_VIDEO_OPENGL=ON \
    -DSDL_AUDIO=OFF \
    -DSDL_HIDAPI=OFF \
    -DSDL_JOYSTICK=OFF \
    -DSDL_GAMEPAD=OFF \
    -DSDL_HAPTIC=OFF \
    -DSDL_POWER=OFF \
    -DSDL_SENSOR=OFF \
    -DSDL_RENDER=OFF \
    -DSDL_TIMERS=ON \
    -DSDL_FILE=ON \
    -DSDL_LOADSO=ON \
    -DSDL_CPUINFO=OFF \
    -DSDL_IMMEVENT=OFF \
    2>&1 | tail -5

info "Building SDL2 (MinGW cross-compile)..."
make -j$(ncores) 2>&1 | tail -5

info "Installing SDL2 (MinGW cross-compile)..."
make install 2>&1 | tail -5

# Create sdl2-config for MinGW
cat > "$SDL2_MINGW_DIR/bin/sdl2-config" << 'SDLCONF'
#!/bin/sh
prefix="$(cd -P -- "$(dirname -- "$0")/.." && printf '%s\n' "$(pwd -P)")"
libdir="$prefix/lib"
includedir="$prefix/include"
if [ "$#" -eq 0 ]; then
    echo "Usage: sdl2-config [--prefix|--exec-prefix|--version|--cflags|--libs|--static-libs]" 1>&2
    exit 1
fi
while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix) echo "$prefix" ;;
        --exec-prefix) echo "$prefix" ;;
        --version) echo "2.30.11" ;;
        --cflags) echo "-I${includedir}/SDL2 -Dmain=SDL_main" ;;
        --libs) echo "-L${libdir} -lmingw32 -lSDL2main -lSDL2 -mwindows" ;;
        --static-libs) echo "-L${libdir} -lmingw32 -lSDL2main -lSDL2 -mwindows -lopengl32 -lgdi32 -lwinmm" ;;
        *) echo "${usage}" 1>&2; exit 1 ;;
    esac
    shift
done
SDLCONF
chmod +x "$SDL2_MINGW_DIR/bin/sdl2-config"

ok "SDL2 (MinGW) built and installed to $SDL2_MINGW_DIR"
