#!/usr/bin/env bash
# ============================================================
# COMI-HD — Build Everything
# ============================================================
# Usage:
#   bash build/build-all.sh           # alles, was auf diesem Rechner geht (native + Windows-Cross)
#   bash build/build-all.sh native    # nur das System, auf dem du gerade bist
#   bash build/build-all.sh linux     # Linux-Binary (auch von macOS aus)
#   bash build/build-all.sh macos     # macOS-Binary (nur auf macOS sinnvoll)
#   bash build/build-all.sh windows   # Windows-exe, per llvm-mingw aus Linux ODER macOS
#
# Erzeugte Dateien:
#   build/out/scummvm     (Linux / macOS)
#   build/out/scummvm.exe (Windows)
#
# Dependencies are downloaded to build/deps/ and built into
# build/install/ — no system packages needed beyond the
# basic build toolchain (gcc, g++, make, cmake, pkg-config, curl).
# ============================================================

set -euo pipefail

# ── Bootstrap ───────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# ── Parse target ────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --no-deps) NO_DEPS=1 ;;
        linux|macos|windows|native|all) TARGET="$arg" ;;
        -h|--help) sed -n "2,20p" "$0"; exit 0 ;;
        *) err "Usage: bash build/build-all.sh [native|linux|macos|windows|all] [--no-deps]"; exit 1 ;;
    esac
done
TARGET="${TARGET:-all}"
case "$TARGET" in
    all|linux|macos|windows|native) ;;
    *) err "Usage: bash build/build-all.sh [native|linux|macos|windows|all] [--no-deps]"; exit 1 ;;
esac

# "native" meint immer das System, auf dem gerade gebaut wird: Linux-Binary auf Linux,
# macOS-Binary auf macOS, scummvm.exe unter MSYS2. Damit braucht niemand zu wissen,
# welcher Zielname zu seinem Rechner passt.
HOST_OS="$(uname -s)"
case "${MSYSTEM:-}" in MINGW*|MSYS*|UCRT*) HOST_OS="Windows" ;; esac
if [ "$TARGET" = "native" ] || [ "$TARGET" = "all" ]; then
    if [ "$HOST_OS" = "Darwin" ]; then NATIVE_TARGET="macos"; else NATIVE_TARGET="linux"; fi
    [ "$HOST_OS" = "Windows" ] && NATIVE_TARGET="windows"
fi
[ "$TARGET" = "linux" ] && NATIVE_TARGET="linux"
[ "$TARGET" = "macos" ] && NATIVE_TARGET="macos"

# Windows-Cross nur, wenn wir nicht schon auf Windows sind (dort ist der native Build
# bereits ein Windows-Binary).
BUILD_CROSS_WIN=0
if { [ "$TARGET" = "windows" ] || [ "$TARGET" = "all" ]; } && [ "$HOST_OS" != "Windows" ]; then
    BUILD_CROSS_WIN=1
fi
export NO_DEPS="${NO_DEPS:-0}"

# ── System-Abhaengigkeiten ─────────────────────────────
# Ein Befehl fuer den Nutzer: fehlt etwas, wird es hier installiert. Wer das nicht will,
# ruft mit --no-deps auf und bekommt nur die Liste.
if [ "${NO_DEPS:-0}" != "1" ] && [ -x "$(dirname "$0")/install-deps.sh" ]; then
    if ! bash "$(dirname "$0")/install-deps.sh" --check >/dev/null 2>&1; then
        info "Missing build dependencies, installing them now (this asks for sudo once)..."
        bash "$(dirname "$0")/install-deps.sh" || {
            error "Dependency install failed. Run it yourself: bash build/install-deps.sh"
            exit 1
        }
    fi
fi

# ── Check system tools ─────────────────────────────────
info "Checking system build tools..."
for cmd in gcc g++ make cmake pkg-config curl; do
    require_cmd "$cmd"
done
ok "All system build tools found"

# ── Load dependency URLs (auto-loaded via _common.sh) ──

# ── Step 1: Download ALL dependencies ──────────────────
echo ""
info "=== Step 1/5: Downloading dependencies ==="
mkdir -p "$DEPS_DIR"

# LLVM MinGW (needed for Windows build)
if [ "$BUILD_CROSS_WIN" = "1" ]; then
    ensure_downloaded "$DEP_LLVM_MINGW_URL" "$DEP_LLVM_MINGW_DIR"
    # Symlink to a predictable path
    mkdir -p "$INSTALL_DIR"
    ln -sfn "$DEPS_DIR/$DEP_LLVM_MINGW_DIR" "$LLVM_MINGW_DIR" 2>/dev/null || true
fi

# SDL2 source (needed for both)
ensure_downloaded "$DEP_SDL2_URL" "$DEP_SDL2_DIR"

# zlib + libpng (needed for Windows cross-compile)
if [ "$BUILD_CROSS_WIN" = "1" ]; then
    ensure_downloaded "$DEP_ZLIB_URL" "$DEP_ZLIB_DIR"
    ensure_downloaded "$DEP_LIBPNG_URL" "$DEP_LIBPNG_DIR"
fi

ok "All dependencies downloaded"

# ── Step 2: Build SDL2 for Linux native ────────────────
if [ -n "${NATIVE_TARGET:-}" ]; then
    echo ""
    info "=== Step 2/5: Building SDL2 ($NATIVE_TARGET) ==="
    bash "$SCRIPT_DIR/_build-sdl2-native.sh"
fi

# ── Step 3: Build SDL2 + libs for MinGW cross-compile ─
if [ "$BUILD_CROSS_WIN" = "1" ]; then
    echo ""
    info "=== Step 3/5: Building SDL2 (MinGW cross-compile) ==="
    bash "$SCRIPT_DIR/_build-sdl2-mingw.sh"

    echo ""
    info "=== Step 4/5: Building zlib + libpng (MinGW cross-compile) ==="
    bash "$SCRIPT_DIR/_build-mingw-libs.sh"
fi

# ── Step 5: Build ScummVM ──────────────────────────────
mkdir -p "$BUILD_DIR/out"

# $NATIVE_TARGET ist "linux" oder "macos" (beide bauen das POSIX-Skript) oder "windows"
# unter MSYS2, wo dasselbe Skript scummvm.exe erzeugt.
if [ -n "${NATIVE_TARGET:-}" ]; then
    echo ""
    info "=== Step 5/5: Building COMI-HD ($NATIVE_TARGET) ==="
    bash "$SCRIPT_DIR/_build-scummvm-linux.sh"

    if [ -f "$BUILD_DIR/out/scummvm" ]; then
        ok "Native binary: $BUILD_DIR/out/scummvm"
        ls -lh "$BUILD_DIR/out/scummvm"
    fi
fi

if [ "$BUILD_CROSS_WIN" = "1" ]; then
    echo ""
    info "=== Step 5b/5: Building COMI-HD (Windows) ==="
    bash "$SCRIPT_DIR/_build-scummvm-windows.sh"

    if [ -f "$BUILD_DIR/out/scummvm.exe" ]; then
        ok "Windows binary: $BUILD_DIR/out/scummvm.exe"
        ls -lh "$BUILD_DIR/out/scummvm.exe"
    fi
fi

# ── Done ────────────────────────────────────────────────
echo ""
echo "============================================"
echo -e "${GREEN}  COMI-HD Build Complete!${NC}"
echo "============================================"
if [ -f "$BUILD_DIR/out/scummvm" ]; then
    echo "  Native:  build/out/scummvm ($NATIVE_TARGET)"
fi
if [ -f "$BUILD_DIR/out/scummvm.exe" ]; then
    echo "  Windows: build/out/scummvm.exe"
fi
echo ""
echo "Usage:"
echo "  ./build/out/scummvm --path=/path/to/COMI/game"
echo ""
