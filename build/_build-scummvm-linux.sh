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
# Unter MSYS2 heisst das Ergebnis scummvm.exe. Ohne diese Unterscheidung liegt das Binary
# als "scummvm" im out-Verzeichnis, obwohl es eine Windows-exe ist.
if [ -n "${MSYSTEM:-}" ]; then
    SCUMMVM_LINUX="$BUILD_DIR/out/scummvm.exe"
else
    SCUMMVM_LINUX="$BUILD_DIR/out/scummvm"
fi
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
# zlib und libpng: liegen die Quellen nicht vor (Linux laedt sie nicht herunter), werden die
# Systembibliotheken benutzt. Vorher brach der Build hier mit "No such file or directory" ab,
# obwohl zlib1g-dev und libpng-dev installiert waren.
if [ ! -d "$DEPS_DIR/zlib-1.3.1" ] || [ ! -d "$DEPS_DIR/libpng-1.6.44" ]; then
    info "zlib/libpng sources not present, using system libraries"
    export PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
elif [ ! -f "$NATIVE_PREFIX/lib/libpng16.a" ] || [ ! -f "$NATIVE_PREFIX/lib/libz.a" ]; then
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
# Das selbst gebaute SDL2 liegt in einem eigenen Prefix. Ohne diese beiden Pfade scheitert der
# Test-Link von configure auf macOS an fehlenden Symbolen und meldet "Checking for SDL... no"
# (Linux faellt zurueck auf die Systembibliothek und merkt es nicht).
export CPPFLAGS="-I$SDL2_NATIVE_DIR/include -I$SDL2_NATIVE_DIR/include/SDL2 -I$NATIVE_PREFIX/include"
export LDFLAGS="-L$SDL2_NATIVE_DIR/lib -L$NATIVE_PREFIX/lib"
export PKG_CONFIG_PATH="$NATIVE_PREFIX/lib/pkgconfig"

# macOS: Homebrew-SDL2 benutzen. Der lokale SDL2-Bau laesst sich dort nicht durch den
# Configure-Test von ScummVM bringen ("Checking for SDL... no"), die Brew-Fassung schon.
if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    SDL2_NATIVE_DIR="$(brew --prefix sdl2)"
    export CPPFLAGS="-I$SDL2_NATIVE_DIR/include -I$SDL2_NATIVE_DIR/include/SDL2"
    export LDFLAGS="-L$SDL2_NATIVE_DIR/lib"
    export SDL_CONFIG="$SDL2_NATIVE_DIR/bin/sdl2-config"
    export PKG_CONFIG_PATH="$SDL2_NATIVE_DIR/lib/pkgconfig:$PKG_CONFIG_PATH"
    info "Using Homebrew SDL2: $SDL2_NATIVE_DIR"
fi

# Create build directory in fork
# MSYS2: im Quellbaum bauen. Out-of-tree schreibt configure einen Makefile, der auf
# /d/a/.../scummvm/fork/Makefile zeigt, und Windows-make findet diesen Pfad nicht.
if [ -n "${MSYSTEM:-}" ]; then
    BUILD_DIR_LINUX="$FORK_DIR"
else
    BUILD_DIR_LINUX="$FORK_DIR/build-linux"
fi
mkdir -p "$BUILD_DIR_LINUX"

cd "$BUILD_DIR_LINUX"

# Only configure if not already configured
if [ ! -f "config.mk" ]; then
    info "Configuring ScummVM for Linux..."
# --with-sdl-prefix: ohne diese Angabe findet configure das selbst gebaute SDL2 nicht und
#   faellt auf "Checking for SDL... no" zurueck. --enable-engine braucht den Bindestrich:
#   "scumm_7_8" wird stillschweigend ignoriert, dann fehlt genau der Engine-Teil fuer COMI.
    # --disable-jpeg: COMI braucht kein JPEG (HD-Texturen sind PNG). Ohne den Schalter haengt das
    # Binary an libjpeg.so.8 aus dem Build-System, eine SONAME, die Debian so nicht hat -
    # das Spiel startet dort dann nicht.
    # Achtung: keine Kommentarzeilen zwischen die mit \ fortgesetzten Argumente schreiben,
    # das beendet den Befehl und endet in "command not found" (Exit 127).
    # --enable-static: ScummVM holt SDL dann ueber "sdl2-config --static-libs", also aus der
    # selbst gebauten libSDL2.a. Ohne das haengt das Linux-Binary an libSDL2-2.0.so.0 und
    # startet nur, wo das Paket installiert ist. Auf macOS ist es umgekehrt (Brew-SDL2, dynamic).
    STATIC_OPT=""
    if [ "$(uname -s)" = "Linux" ]; then STATIC_OPT="--enable-static"; fi
    "$FORK_DIR/configure" \
        $STATIC_OPT \
        --opengl-mode=gl \
        --enable-verbose-build \
        --disable-nasm \
        --disable-all-engines \
        --enable-engine=scumm,scumm-7-8 \
        --with-sdl-prefix="$SDL2_NATIVE_DIR" \
        --disable-jpeg \
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
    # Verify PNG support (anchored: the commented '# USE_PNG = 1' line
    # must NOT count as enabled — that silent failure broke Linux builds)
    if ! grep -qE "^USE_PNG = 1" config.mk 2>/dev/null; then
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
# Vollstaendiges Log mitschreiben: "| tail -5" verschluckt bei einem Link-Fehler genau die
# Zeile mit der Ursache (auf MSYS2 war im CI nichts mehr zu sehen ausser "exit code 2").
if ! make -j$(ncores) > "$BUILD_DIR_LINUX/make.log" 2>&1; then
    err "make failed — last lines of $BUILD_DIR_LINUX/make.log:"
    tail -40 "$BUILD_DIR_LINUX/make.log"
    exit 1
fi
tail -5 "$BUILD_DIR_LINUX/make.log"

# Check result
if [ ! -f "scummvm" ]; then
    err "Build failed — scummvm binary not found"
    exit 1
fi

# Verify static SDL2: the released Linux binary must be self-contained
# (sdl2-config --libs returns -Bstatic flags). Dynamic SDL2 means desktop
# users need a matching system SDL2 — we ship static instead.
# NOTE: grep -c, not grep -q (pipefail + SIGPIPE issue, see windows script).
# Dynamisches SDL2 ist kein Fehler, solange die Bibliothek im Build-Baum liegt und per rpath
# gefunden wird: dann laeuft das Binary ohne systemweite Installation. Vorher brach der Build
# hier ab, obwohl er erfolgreich kompiliert hatte.
if [ "$(ldd scummvm 2>/dev/null | grep -c libSDL2)" -ne 0 ]; then
    if ldd scummvm 2>/dev/null | grep libSDL2 | grep -q "$SDL2_NATIVE_DIR"; then
        warn "Binary links SDL2 from $SDL2_NATIVE_DIR (rpath), that is fine for local use"
    else
        warn "Binary links system SDL2, users need the same package installed"
    fi
fi
ok "Linux binary built: $(ls -lh scummvm | awk '{print $5}')"

# Copy to output. Unter MSYS2 heisst das Ergebnis scummvm.exe, das Skript hat aber bisher
# immer "scummvm" kopiert — deshalb fand der Strip die Datei nicht.
BIN_SRC=scummvm
[ -f scummvm.exe ] && BIN_SRC=scummvm.exe
cp "$BIN_SRC" "$SCUMMVM_LINUX"

# Strip
info "Stripping binary..."
strip "$SCUMMVM_LINUX" || warn "strip fehlgeschlagen, Binary bleibt ungestrippt"

ok "Linux binary: $SCUMMVM_LINUX ($(du -h "$SCUMMVM_LINUX" | cut -f1))"
