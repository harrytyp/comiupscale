#!/usr/bin/env bash
# ============================================================
# Build SDL2 from source for Linux native
# Output: build/install/sdl2-native/
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Check if SDL2 already built
if [ -f "$SDL2_NATIVE_DIR/lib/libSDL2.a" ] || [ -f "$SDL2_NATIVE_DIR/lib/x86_64-linux-gnu/libSDL2.a" ]; then
    info "SDL2 (native) already built — skipping"
    exit 0
fi

SDL2_SRC="$DEPS_DIR/$DEP_SDL2_DIR"

if [ ! -d "$SDL2_SRC" ]; then
    err "SDL2 source not found at $SDL2_SRC — run build-all.sh first"
    exit 1
fi

mkdir -p "$SDL2_NATIVE_DIR"
BUILD_DIR_SDL2="$SDL2_SRC/build-native"
mkdir -p "$BUILD_DIR_SDL2"

info "Configuring SDL2 (native)..."
# Build SDL2 with X11 and OpenGL support.
# We try to use system X11 if available; if not, we build without X11
# (will fall back to offscreen driver for headless builds).
X11_OPT="ON"
if ! has_pkg x11; then
    warn "X11 development headers not found (libx11-dev / libX11-devel)"
    warn "Building SDL2 without X11 — only offscreen/software rendering will work."
    warn ""
    warn "For desktop use, install X11 dev headers and rebuild:"
    warn "  sudo apt install libx11-dev libxext-dev libxcursor-dev \\"
    warn "                     libxi-dev libxfixes-dev libxrandr-dev"
    warn ""
    X11_OPT="OFF"
fi

# OpenGL check (needed by ScummVM)
if ! has_pkg gl; then
    warn "OpenGL development headers not found (libgl-dev / Mesa)"
    warn "The HD renderer needs OpenGL. Install with:"
    warn "  sudo apt install libgl-dev libglu1-mesa-dev"
fi

cd "$BUILD_DIR_SDL2"
cmake "$SDL2_SRC" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$SDL2_NATIVE_DIR" \
    -DSDL_X11="$X11_OPT" \
    -DSDL_WAYLAND=OFF \
    -DSDL_VIDEO_DRIVER_X11="$X11_OPT" \
    -DSDL_VIDEO_DRIVER_OFFSCREEN=ON \
    -DSDL_VIDEO_OPENGL=ON \
    -DSDL_VIDEO_OPENGL_EGL=OFF \
    -DSDL_AUDIO=ON \
    -DSDL_HIDAPI=OFF \
    -DSDL_JOYSTICK=OFF \
    -DSDL_GAMEPAD=OFF \
    -DSDL_HAPTIC=OFF \
    -DSDL_POWER=OFF \
    -DSDL_SENSOR=OFF \
    2>&1 | tail -5

info "Building SDL2 (native)..."
make -j$(ncores) 2>&1 | tail -5

info "Installing SDL2 (native)..."
make install 2>&1 | tail -5

# Create sdl2-config if cmake didn't
if [ ! -f "$SDL2_NATIVE_DIR/bin/sdl2-config" ]; then
    cat > "$SDL2_NATIVE_DIR/bin/sdl2-config" << 'SDLCONF'
#!/bin/sh
prefix="$(cd -P -- "$(dirname -- "$0")/.." && printf '%s\n' "$(pwd -P)")"
libdir="$prefix/lib"
includedir="$prefix/include"
usage="Usage: sdl2-config [--prefix|--exec-prefix|--version|--cflags|--libs|--static-libs]"
if [ "$#" -eq 0 ]; then
    echo "${usage}" 1>&2
    exit 1
fi
while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix) echo "$prefix" ;;
        --exec-prefix) echo "$prefix" ;;
        --version) echo "2.30.11" ;;
        --cflags) echo "-I${includedir}/SDL2 -D_REENTRANT" ;;
        --libs) echo "-L${libdir} -lSDL2" ;;
        --static-libs) echo "-L${libdir} -lSDL2 -lm -ldl -lpthread" ;;
        *) echo "${usage}" 1>&2; exit 1 ;;
    esac
    shift
done
SDLCONF
    chmod +x "$SDL2_NATIVE_DIR/bin/sdl2-config"
fi

ok "SDL2 (native) built and installed to $SDL2_NATIVE_DIR"
