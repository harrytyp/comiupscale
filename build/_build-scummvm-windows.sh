#!/usr/bin/env bash
# ============================================================
# Build ScummVM HD Fork for Windows (cross-compile)
# Output: build/out/scummvm.exe
# Uses:  LLVM MinGW toolchain + SDL2/MinGW + zlib/libpng
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

mkdir -p "$BUILD_DIR/out"

SCUMMVM_WIN="$BUILD_DIR/out/scummvm.exe"
if [ -f "$SCUMMVM_WIN" ]; then
    info "Windows binary already exists at $SCUMMVM_WIN"
    exit 0
fi

# ── Verify dependencies ─────────────────────────────────
LLVM_TOOLCHAIN="$LLVM_MINGW_DIR/bin"
if [ ! -f "$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++" ]; then
    err "LLVM MinGW toolchain not found at $LLVM_MINGW_DIR"
    exit 1
fi

if [ ! -f "$SDL2_MINGW_DIR/bin/sdl2-config" ]; then
    err "SDL2 for MinGW not found at $SDL2_MINGW_DIR"
    exit 1
fi

# Add toolchain to PATH
export PATH="$LLVM_TOOLCHAIN:$SDL2_MINGW_DIR/bin:$PATH"
export SDL_CONFIG="$SDL2_MINGW_DIR/bin/sdl2-config"

# ── Configure ───────────────────────────────────────────
BUILD_DIR_WIN="$FORK_DIR/build-windows"
mkdir -p "$BUILD_DIR_WIN"
cd "$BUILD_DIR_WIN"

if [ ! -f "config.mk" ]; then
    info "Configuring ScummVM for Windows (cross-compile)..."

    # Build the configure arguments
    CONFIG_ARGS=(
        --host=x86_64-w64-mingw32
        --backend=sdl
        --opengl-mode=gl
        --disable-nasm
        --disable-all-engines
        --enable-engine=scumm
        --enable-engine=scumm_7_8
        --enable-verbose-build
        # Disable all optional audio/video codecs (not needed for COMI)
        --disable-vorbis
        --disable-flac
        --disable-mad
        --disable-ogg
        --disable-theoradec
        --disable-faad
        # Disable zlib/png — we provide them manually via LDFLAGS
        --disable-zlib
        --disable-png
    )

    "$FORK_DIR/configure" "${CONFIG_ARGS[@]}" 2>&1 | tail -5

    # Verify scumm_7_8 is enabled
    if ! grep -q "ENABLE_SCUMM_7_8 = 1" config.mk 2>/dev/null; then
        err "SCUMM v7-8 engine not enabled!"
        exit 1
    fi

    # Add our prefix to LDFLAGS for zlib + libpng
    # (configure flags like --with-zlib-prefix don't work well without pkg-config)
    if [ -d "$MINGW_PREFIX/lib" ]; then
        echo "" >> config.mk
        echo "# COMI-HD: additional lib paths" >> config.mk
        echo "LDFLAGS += -L$MINGW_PREFIX/lib" >> config.mk
        echo "INCLUDES += -I$MINGW_PREFIX/include" >> config.mk
    fi

    ok "ScummVM configured for Windows"
else
    info "Already configured — reusing config.mk"
fi

# ── Build ───────────────────────────────────────────────
info "Building ScummVM (Windows cross-compile)..."
make -j$(ncores) 2>&1 | tail -5

if [ ! -f "scummvm.exe" ]; then
    err "Build failed — scummvm.exe not found"
    exit 1
fi

# ── Strip ───────────────────────────────────────────────
info "Stripping Windows binary..."
x86_64-w64-mingw32-strip scummvm.exe -o "$SCUMMVM_WIN"

ok "Windows binary: $SCUMMVM_WIN ($(du -h "$SCUMMVM_WIN" | cut -f1))"
