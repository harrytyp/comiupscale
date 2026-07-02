#!/usr/bin/env bash
# ============================================================
# COMI Upscaled — ScummVM HD Fork Build Script
# ============================================================
# Cross-platform build for Windows (MSYS2) and Linux.
#
# This is a convenience wrapper. For the full automated build
# (downloads deps, builds SDL2 from source, cross-compile for
# Windows), use:
#
#   bash build/build-all.sh
#
# from the repository root.
#
# Usage:
#   cd <repo>/scummvm/fork
#   bash build.sh
#
# Detects platform automatically:
#   - Windows (MSYS2/MinGW64) → mingw32-make
#   - Linux/macOS → make
# ============================================================

set -e

# ── Platform detection ─────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    MINGW*|MSYS*|CYGWIN*)
        PLATFORM="windows"
        MAKE_CMD="mingw32-make"
        MAKE_TARGET="scummvm.exe"
        ;;
    Linux*)
        PLATFORM="linux"
        MAKE_CMD="make"
        MAKE_TARGET="scummvm"
        ;;
    Darwin*)
        PLATFORM="macos"
        MAKE_CMD="make"
        MAKE_TARGET="scummvm"
        ;;
    *)
        echo "ERROR: Unsupported platform: $OS"
        exit 1
        ;;
esac

echo "=== COMI Upscaled Build ==="
echo "Platform: $PLATFORM ($OS)"

echo ""
echo "NOTE: For the fully automated build (downloads toolchains,"
echo "builds SDL2 from source, cross-compiles for Windows), run:"
echo ""
echo "  bash build/build-all.sh"
echo ""
echo "from the repository root instead."

# ── Windows-specific setup ─────────────────────────────
if [ "$PLATFORM" = "windows" ]; then
    # Ensure MinGW64 tools are in PATH
    export PATH="/mingw64/bin:/usr/bin:$PATH"

    # MSYS2 temp directory fix
    export TMP="/tmp"
    export TEMP="/tmp"
    mkdir -p /tmp

    echo ""
    echo "Applying MSYS2 sed 4.9 workaround..."

    # Workaround for MSYS2 sed 4.9 bug (crashes on Makefile.common sed patterns)
    mkdir -p dists dists/.deps
    $MAKE_CMD -j$(nproc) \
      dists/scummvm_rc_engine_data_core.rh \
      dists/scummvm_rc_engine_data.rh \
      dists/scummvm_rc_engine_data_big.rh \
      2>/dev/null || true

    # Compile the resource file manually (avoids the broken sed dependency rule)
    if command -v windres &>/dev/null; then
        windres -DHAVE_CONFIG_H -DRELEASE_BUILD -DWIN32 -DSDL_BACKEND -DUSE_SDL2 \
          -I. -I./engines -I./base \
          dists/scummvm.rc -o dists/scummvm.o 2>/dev/null || true
    fi
fi

# ── Linux-specific checks ──────────────────────────────
if [ "$PLATFORM" = "linux" ] || [ "$PLATFORM" = "macos" ]; then
    echo ""
    echo "Checking dependencies..."

    MISSING=""
    for cmd in gcc g++ make pkg-config; do
        if ! command -v "$cmd" &>/dev/null; then
            MISSING="$MISSING $cmd"
        fi
    done
    if [ -n "$MISSING" ]; then
        echo "ERROR: Missing required tools:$MISSING"
        echo ""
        echo "Install with:"
        echo "  Ubuntu/Debian: sudo apt install build-essential pkg-config"
        echo "  Fedora/RHEL:   sudo dnf groupinstall 'Development Tools'"
        echo "  Arch:          sudo pacman -S base-devel pkgconf"
        exit 1
    fi

    # Check for SDL2
    if ! pkg-config --exists sdl2 2>/dev/null && ! command -v sdl2-config &>/dev/null; then
        echo "WARNING: SDL2 not found. Build SDL2 first:"
        echo "  bash build/build-all.sh linux"
        echo "  (or install system SDL2: sudo apt install libsdl2-dev)"
    fi

    # Check OpenGL support (needed for HD rendering)
    if ! pkg-config --exists gl 2>/dev/null; then
        echo "WARNING: OpenGL development files not found"
        echo "  Install: sudo apt install libgl-dev libglu1-mesa-dev"
        echo "  For headless/software rendering: sudo apt install mesa-utils libgl1-mesa-dri"
    fi

    echo "Dependencies OK"
fi

# ── Build ───────────────────────────────────────────────
echo ""
echo "Building with $MAKE_CMD ($(nproc) jobs)..."

# Parallel jobs: detect CPU count
if command -v nproc &>/dev/null; then
    JOBS=$(nproc)
elif [ "$PLATFORM" = "macos" ]; then
    JOBS=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
else
    JOBS=4
fi

$MAKE_CMD -j"$JOBS"

# ── Done ────────────────────────────────────────────────
echo ""
echo "=== Build complete ==="

if [ -f "$MAKE_TARGET" ]; then
    ls -lh "$MAKE_TARGET"
    echo ""
    echo "Binary: $(pwd)/$MAKE_TARGET"
    echo ""
    echo "Usage:"
    echo "  ./$MAKE_TARGET --path=/path/to/COMI/game"
    echo ""
    echo "With HD assets:"
    echo "  Place hd/ directory next to your game data (COMI.LA0/1/2)"
    echo "  See docs/BUILD.md for details"
else
    echo "ERROR: Build target $MAKE_TARGET not found"
    exit 1
fi
