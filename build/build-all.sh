#!/usr/bin/env bash
# ============================================================
# COMI-HD — Build Everything
# ============================================================
# Usage:
#   bash build/build-all.sh          # Build both Linux + Windows
#   bash build/build-all.sh linux    # Linux only
#   bash build/build-all.sh windows  # Windows only
#
# Build artifacts will be in:
#   build/out/scummvm     (Linux binary)
#   build/out/scummvm.exe (Windows binary)
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
        linux|windows|all) TARGET="$arg" ;;
        -h|--help) sed -n "2,12p" "$0"; exit 0 ;;
        *) err "Usage: bash build/build-all.sh [linux|windows|all] [--no-deps]"; exit 1 ;;
    esac
done
TARGET="${TARGET:-all}"
case "$TARGET" in
    all|linux|windows) ;;
    *) err "Usage: bash build/build-all.sh [linux|windows|all] [--no-deps]"; exit 1 ;;
esac
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
if [ "$TARGET" = "all" ] || [ "$TARGET" = "windows" ]; then
    ensure_downloaded "$DEP_LLVM_MINGW_URL" "$DEP_LLVM_MINGW_DIR"
    # Symlink to a predictable path
    mkdir -p "$INSTALL_DIR"
    ln -sfn "$DEPS_DIR/$DEP_LLVM_MINGW_DIR" "$LLVM_MINGW_DIR" 2>/dev/null || true
fi

# SDL2 source (needed for both)
ensure_downloaded "$DEP_SDL2_URL" "$DEP_SDL2_DIR"

# zlib + libpng (needed for Windows cross-compile)
if [ "$TARGET" = "all" ] || [ "$TARGET" = "windows" ]; then
    ensure_downloaded "$DEP_ZLIB_URL" "$DEP_ZLIB_DIR"
    ensure_downloaded "$DEP_LIBPNG_URL" "$DEP_LIBPNG_DIR"
fi

ok "All dependencies downloaded"

# ── Step 2: Build SDL2 for Linux native ────────────────
if [ "$TARGET" = "all" ] || [ "$TARGET" = "linux" ]; then
    echo ""
    info "=== Step 2/5: Building SDL2 (Linux native) ==="
    bash "$SCRIPT_DIR/_build-sdl2-native.sh"
fi

# ── Step 3: Build SDL2 + libs for MinGW cross-compile ─
if [ "$TARGET" = "all" ] || [ "$TARGET" = "windows" ]; then
    echo ""
    info "=== Step 3/5: Building SDL2 (MinGW cross-compile) ==="
    bash "$SCRIPT_DIR/_build-sdl2-mingw.sh"

    echo ""
    info "=== Step 4/5: Building zlib + libpng (MinGW cross-compile) ==="
    bash "$SCRIPT_DIR/_build-mingw-libs.sh"
fi

# ── Step 5: Build ScummVM ──────────────────────────────
mkdir -p "$BUILD_DIR/out"

if [ "$TARGET" = "all" ] || [ "$TARGET" = "linux" ]; then
    echo ""
    info "=== Step 5/5: Building COMI-HD (Linux) ==="
    bash "$SCRIPT_DIR/_build-scummvm-linux.sh"

    if [ -f "$BUILD_DIR/out/scummvm" ]; then
        ok "Linux binary: $BUILD_DIR/out/scummvm"
        ls -lh "$BUILD_DIR/out/scummvm"
    fi
fi

if [ "$TARGET" = "all" ] || [ "$TARGET" = "windows" ]; then
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
    echo "  Linux:   build/out/scummvm"
fi
if [ -f "$BUILD_DIR/out/scummvm.exe" ]; then
    echo "  Windows: build/out/scummvm.exe"
fi
echo ""
echo "Usage:"
echo "  ./build/out/scummvm --path=/path/to/COMI/game"
echo ""
