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

# PNG/zlib must be visible to configure (USE_PNG), otherwise the build
# silently ships without HD texture support. Same env as the Linux build.
export CPPFLAGS="-I$MINGW_PREFIX/include"
export LDFLAGS="-L$MINGW_PREFIX/lib"
export PKG_CONFIG_PATH="$MINGW_PREFIX/lib/pkgconfig"

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
        --with-zlib-prefix="$MINGW_PREFIX"
        --with-png-prefix="$MINGW_PREFIX"
        --opengl-mode=gl
        --enable-verbose-build
        --disable-nasm
        --disable-all-engines
        --enable-engine=scumm,scumm-7-8
    )

    "$FORK_DIR/configure" "${CONFIG_ARGS[@]}" 2>&1 | tail -5

    # Verify scumm_7_8 is enabled
    if ! grep -q "ENABLE_SCUMM_7_8 = 1" config.mk 2>/dev/null; then
        err "SCUMM v7-8 engine not enabled!"
        exit 1
    fi

    # Verify PNG support (anchored: the commented '# USE_PNG = 1' line
    # must NOT count as enabled — that silent failure broke Linux builds)
    if ! grep -qE "^USE_PNG = 1" config.mk 2>/dev/null; then
        err "PNG support not enabled — USE_PNG missing from config.mk!"
        err "Check PKG_CONFIG_PATH and --with-png-prefix (libpng.pc must be found)"
        exit 1
    fi

    ok "ScummVM configured for Windows"
else
    info "Already configured — reusing config.mk"
    # Re-verify PNG even when reusing (config.mk may be stale/broken)
    if ! grep -qE "^USE_PNG = 1" config.mk 2>/dev/null; then
        err "PNG support not enabled in existing config.mk — delete build-windows/ and rebuild"
        exit 1
    fi
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

# ── Verify SDL2.dll audio (the released bundle ships this DLL) ──
# NOTE: use grep -c, NOT grep -q — with `set -o pipefail`, grep -q closes
# the pipe after the first match, strings gets SIGPIPE, and the check
# fails even though the DLL is fine.
if [ "$(strings "$SDL2_MINGW_DIR/bin/SDL2.dll" 2>/dev/null | grep -cE "directsound|wasapi|winmm")" -eq 0 ]; then
    err "SDL2.dll has no audio support — rebuild SDL2 with audio enabled"
    err "  cd build/deps/SDL2-2.30.11 && ./configure --host=x86_64-w64-mingw32 --enable-audio --enable-directsound --enable-wasapi --enable-winmm"
    exit 1
fi

ok "Windows binary: $SCUMMVM_WIN ($(du -h "$SCUMMVM_WIN" | cut -f1))"
