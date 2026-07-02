#!/usr/bin/env bash
# ============================================================
# Build zlib + libpng for MinGW cross-compile
# Output: build/install/mingw-prefix/
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Check if already built
if [ -f "$MINGW_PREFIX/lib/libpng16.a" ]; then
    info "MinGW libs (zlib + libpng) already built — skipping"
    exit 0
fi

LLVM_TOOLCHAIN="$LLVM_MINGW_DIR/bin"
if [ ! -f "$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++" ]; then
    err "LLVM MinGW toolchain not found at $LLVM_MINGW_DIR"
    exit 1
fi

export PATH="$LLVM_TOOLCHAIN:$PATH"
export CC=x86_64-w64-mingw32-gcc
export CXX=x86_64-w64-mingw32-g++
export AR=x86_64-w64-mingw32-ar
export RANLIB=x86_64-w64-mingw32-ranlib
export STRIP=x86_64-w64-mingw32-strip

mkdir -p "$MINGW_PREFIX"

# ── zlib ──────────────────────────────────────────────────
ZLIB_SRC="$DEPS_DIR/$DEP_ZLIB_DIR"
if [ ! -d "$ZLIB_SRC" ]; then
    err "zlib source not found at $ZLIB_SRC"
    exit 1
fi

if [ ! -f "$MINGW_PREFIX/lib/libz.a" ]; then
    info "Building zlib (MinGW cross-compile)..."
    cd "$ZLIB_SRC"
    make -f win32/Makefile.gcc \
        PREFIX=x86_64-w64-mingw32- \
        prefix="$MINGW_PREFIX" \
        BINARY_PATH="$MINGW_PREFIX/bin" \
        INCLUDE_PATH="$MINGW_PREFIX/include" \
        LIBRARY_PATH="$MINGW_PREFIX/lib" \
        -j$(ncores) \
        2>&1 | tail -3

    make -f win32/Makefile.gcc \
        PREFIX=x86_64-w64-mingw32- \
        prefix="$MINGW_PREFIX" \
        BINARY_PATH="$MINGW_PREFIX/bin" \
        INCLUDE_PATH="$MINGW_PREFIX/include" \
        LIBRARY_PATH="$MINGW_PREFIX/lib" \
        install \
        2>&1 | tail -3
    ok "zlib built for MinGW"
else
    info "zlib already built — skipping"
fi

# ── libpng ────────────────────────────────────────────────
PNG_SRC="$DEPS_DIR/$DEP_LIBPNG_DIR"
if [ ! -d "$PNG_SRC" ]; then
    err "libpng source not found at $PNG_SRC"
    exit 1
fi

if [ ! -f "$MINGW_PREFIX/lib/libpng16.a" ]; then
    info "Building libpng (MinGW cross-compile)..."
    mkdir -p "$PNG_SRC/build-mingw"
    cd "$PNG_SRC/build-mingw"
    cmake "$PNG_SRC" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX" \
        -DCMAKE_SYSTEM_NAME=Windows \
        -DCMAKE_SYSTEM_PROCESSOR=x86_64 \
        -DCMAKE_C_COMPILER="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-gcc" \
        -DCMAKE_CXX_COMPILER="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++" \
        -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
        -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
        -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
        -DZLIB_ROOT="$MINGW_PREFIX" \
        -DPNG_SHARED=OFF \
        -DPNG_TESTS=OFF \
        -DPNG_DEBUG=OFF \
        -DSKIP_INSTALL_EXECUTABLES=ON \
        2>&1 | tail -3

    make -j$(ncores) 2>&1 | tail -3
    make install 2>&1 | tail -3
    ok "libpng built for MinGW"
else
    info "libpng already built — skipping"
fi

ok "MinGW libs (zlib + libpng) ready at $MINGW_PREFIX"
