#!/usr/bin/env bash
# ============================================================
# Build ScummVM HD Fork for Linux
# Output: build/out/scummvm
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Ensure output dir
mkdir -p "$BUILD_DIR/out"

# Check if already built and up to date
SCUMMVM_LINUX="$BUILD_DIR/out/scummvm"
if [ -f "$SCUMMVM_LINUX" ]; then
    info "Linux binary already exists at $SCUMMVM_LINUX"
    info "Remove it to rebuild, or run: make -C $FORK_DIR/build-linux"
    exit 0
fi

# Build or find SDL2
if [ -f "$SDL2_NATIVE_DIR/bin/sdl2-config" ]; then
    export SDL_CONFIG="$SDL2_NATIVE_DIR/bin/sdl2-config"
    export PATH="$SDL2_NATIVE_DIR/bin:$PATH"
    info "Using locally built SDL2 from $SDL2_NATIVE_DIR"
elif command -v sdl2-config &>/dev/null; then
    info "Using system SDL2: $(sdl2-config --version)"
else
    err "SDL2 not found! Build SDL2 first with _build-sdl2-native.sh"
    err "Or install system SDL2: sudo apt install libsdl2-dev"
    exit 1
fi

# ── Build libpng + zlib natively (if not already) ────────
NATIVE_PREFIX="$INSTALL_DIR/native-prefix"
if [ ! -f "$NATIVE_PREFIX/lib/libpng16.a" ] || [ ! -f "$NATIVE_PREFIX/lib/libz.a" ]; then
    info "Building zlib natively..."
    cd "$DEPS_DIR/zlib-1.3.1"
    CC=gcc CXX=g++ ./configure --prefix="$NATIVE_PREFIX" --static 2>&1 | tail -3
    make -j$(ncores) 2>&1 | tail -3
    make install 2>&1 | tail -3

    info "Building libpng natively..."
    cd "$DEPS_DIR/libpng-1.6.44"
    CC=gcc CXX=g++ LDFLAGS="-L$NATIVE_PREFIX/lib" CPPFLAGS="-I$NATIVE_PREFIX/include" \
        ./configure --prefix="$NATIVE_PREFIX" --enable-static --disable-shared 2>&1 | tail -3
    make -j$(ncores) 2>&1 | tail -3
    make install 2>&1 | tail -3

    ok "libpng + zlib built natively"
fi
export CPPFLAGS="-I$NATIVE_PREFIX/include"
export LDFLAGS="-L$NATIVE_PREFIX/lib"
export PKG_CONFIG_PATH="$NATIVE_PREFIX/lib/pkgconfig"

# Create build directory in fork
BUILD_DIR_LINUX="$FORK_DIR/build-linux"
mkdir -p "$BUILD_DIR_LINUX"

cd "$BUILD_DIR_LINUX"

# Only configure if not already configured
if [ ! -f "config.mk" ]; then
    info "Configuring ScummVM for Linux..."
    "$FORK_DIR/configure" \
        --opengl-mode=gl \
        --enable-verbose-build \
        --disable-nasm \
        --disable-all-engines \
        --enable-engine=scumm \
        --enable-engine=scumm_7_8 \
        --with-png-prefix="$NATIVE_PREFIX" \
        --with-zlib-prefix="$NATIVE_PREFIX" \
        2>&1 | tail -5

    # Verify scumm_7_8 is enabled
    if ! grep -q "ENABLE_SCUMM_7_8 = 1" config.mk 2>/dev/null; then
        err "SCUMM v7-8 engine not enabled! Check configure flags."
        err "Hint: use --enable-engine=scumm,scumm-7-8 (hyphen, not underscore)"
        exit 1
    fi
    ok "ScummVM configured for Linux"
else
    info "Already configured — reusing config.mk"
    # Verify PNG support is enabled (reconfigure if not)
    if ! grep -q "USE_PNG = 1" config.mk 2>/dev/null; then
        info "PNG support not enabled — reconfiguring..."
        rm -f config.mk config.h config.log
        "$FORK_DIR/configure" \
            --opengl-mode=gl \
            --enable-verbose-build \
            --disable-nasm \
            --disable-all-engines \
            --enable-engine=scumm \
            --enable-engine=scumm_7_8 \
            --with-png-prefix="$NATIVE_PREFIX" \
            --with-zlib-prefix="$NATIVE_PREFIX" \
            2>&1 | tail -5
    fi
fi

info "Building ScummVM (Linux)..."
make -j$(ncores) 2>&1 | tail -5

# Check result
if [ ! -f "scummvm" ]; then
    err "Build failed — scummvm binary not found"
    exit 1
fi

# Copy to output
cp scummvm "$SCUMMVM_LINUX"

# Strip
info "Stripping Linux binary..."
strip "$SCUMMVM_LINUX"

ok "Linux binary: $SCUMMVM_LINUX ($(du -h "$SCUMMVM_LINUX" | cut -f1))"
