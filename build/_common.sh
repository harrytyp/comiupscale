#!/usr/bin/env bash
# ============================================================
# COMI-HD Build — Shared Functions
# Source this from build scripts:  source "$(dirname "$0")/_common.sh"
# ============================================================

set -euo pipefail

# ── Colors ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── Paths ───────────────────────────────────────────────
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$BUILD_DIR/.." && pwd)"
FORK_DIR="$REPO_DIR/scummvm/fork"
DEPS_DIR="$BUILD_DIR/deps"
INSTALL_DIR="$BUILD_DIR/install"

# Sub-directories within install/
SDL2_NATIVE_DIR="$INSTALL_DIR/sdl2-native"
SDL2_MINGW_DIR="$INSTALL_DIR/sdl2-mingw"
MINGW_PREFIX="$INSTALL_DIR/mingw-prefix"
LLVM_MINGW_DIR="$INSTALL_DIR/llvm-mingw"

# ── Helpers ─────────────────────────────────────────────
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" >&2; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

require_cmd() {
    if ! command -v "$1" &>/dev/null; then
        err "Missing required command: $1"
        case "$1" in
            gcc|g++)    err "Install with: sudo apt install build-essential" ;;
            cmake)      err "Install with: sudo apt install cmake" ;;
            pkg-config) err "Install with: sudo apt install pkg-config" ;;
            make)       err "Install with: sudo apt install build-essential" ;;
            curl)       err "Install with: sudo apt install curl" ;;
            *)          err "Please install $1 via your package manager" ;;
        esac
        exit 1
    fi
}

# Load dependency URLs (auto-executed at bottom of this file)

# Download and extract a tarball if not already present
# Usage: ensure_downloaded <url> <dir_name> [<target_dir>]
ensure_downloaded() {
    local url="$1"
    local dir_name="$2"
    local target_dir="${3:-$DEPS_DIR}"
    local tarball="$target_dir/$(basename "$url")"
    local extract_dir="$target_dir/$dir_name"

    mkdir -p "$target_dir"

    if [ -d "$extract_dir" ]; then
        info "Already extracted: $dir_name"
        return 0
    fi

    if [ ! -f "$tarball" ]; then
        info "Downloading: $(basename "$url")"
        curl -fSL -o "$tarball" "$url" || {
            err "Download failed: $url"
            rm -f "$tarball"
            exit 1
        }
        ok "Downloaded: $(basename "$url")"
    else
        info "Already downloaded: $(basename "$url")"
    fi

    info "Extracting: $dir_name"
    case "$tarball" in
        *.tar.xz) tar xf "$tarball" -C "$target_dir" ;;
        *.tar.gz) tar xzf "$tarball" -C "$target_dir" ;;
        *.zip)    unzip -q "$tarball" -d "$target_dir" ;;
        *)        err "Unknown archive format: $tarball"; exit 1 ;;
    esac

    if [ ! -d "$extract_dir" ]; then
        err "Expected directory not found after extraction: $extract_dir"
        err "Contents of $target_dir:"
        ls -la "$target_dir"
        exit 1
    fi
    ok "Extracted: $dir_name"
}

# Check if a pkg-config package exists, optionally with a minimum version
has_pkg() {
    if [ -n "${2:-}" ]; then
        pkg-config --atleast-version="$2" "$1" 2>/dev/null
    else
        pkg-config --exists "$1" 2>/dev/null
    fi
}

# Number of CPU cores for parallel builds
ncores() {
    nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4
}

# ── Auto-load dependency versions ──────────────────────
source "$BUILD_DIR/deps.list"
