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
# Autotools statt cmake. Cmake baut fuer MinGW nur wasapi/disk/dummy; autotools baut
# winmm, directsound und wasapi - nachgewiesen: 7.75 MB DLL gegen 1.66 MB, und nur mit
# diesen Treibern hat das Spiel Ton (Issue #32). Der Aufruf ist der im Repo und im Skill
# dokumentierte Weg (SKILL.md, "SDL2 Audio Build (Windows)").
SDL2_CONF_LOG="$BUILD_DIR_SDL2/configure.log"
if ! "$SDL2_SRC/configure" \
        --host=x86_64-w64-mingw32 \
        --prefix="$SDL2_MINGW_DIR" \
        --enable-audio --enable-wasapi \
        --disable-joystick --disable-haptic --disable-hidapi \
        > "$SDL2_CONF_LOG" 2>&1 ; then
    err "SDL2 configure failed, last lines of $SDL2_CONF_LOG:"
    tail -20 "$SDL2_CONF_LOG"
    exit 1
fi
grep -E "Audio drivers" "$SDL2_CONF_LOG" | tail -1
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
