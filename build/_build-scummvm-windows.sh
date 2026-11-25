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
# zlib-ng statt zlib 1.3.1 (gebaut von _build-zlibng-mingw.sh): ohne den
# Pfad gewinnt die alte zlib aus mingw-prefix, und Windows dekodiert wieder
# langsamer als Linux. Fehlt der Pfad, baut der Cross-Build wie bisher.
ZNG_PREFIX="$INSTALL_DIR/zlib-ng-2.3.3-mingw"
if [ -f "$ZNG_PREFIX/lib/libz.a" ]; then
    info "zlib-ng (MinGW) gefunden: $ZNG_PREFIX"
    export LDFLAGS="-L$SDL2_MINGW_DIR/lib -L$ZNG_PREFIX/lib -L$MINGW_PREFIX/lib"
else
    warn "zlib-ng (MinGW) fehlt, nehme zlib aus mingw-prefix (langsamerer Dekode)"
    export LDFLAGS="-L$SDL2_MINGW_DIR/lib -L$MINGW_PREFIX/lib"
fi
# SDL2 fuer MinGW liegt in einem eigenen Prefix, nicht im mingw-prefix. Ohne diesen
# Include-Pfad scheitert der Test-Compile von configure, und die Meldung lautet nur
# "Checking for SDL... no" (pkg-config findet sdl2 dabei problemlos).
export CPPFLAGS="-I$SDL2_MINGW_DIR/include -I$SDL2_MINGW_DIR/include/SDL2 -I$MINGW_PREFIX/include"
# SDL2 fuer MinGW liegt NICHT im mingw-prefix, sondern in sdl2-mingw. Ohne diesen Pfad
# findet configure per pkg-config kein sdl2 und meldet "Checking for SDL... no".
export PKG_CONFIG_PATH="$SDL2_MINGW_DIR/lib/pkgconfig:$MINGW_PREFIX/lib/pkgconfig"
# Cross-Sonderfall in configure (Zeile ~4457): fuer einen Host != Build-Host sucht es
# "$host-pkg-config", also x86_64-w64-mingw32-pkg-config, das es nicht gibt. Ergebnis:
# "Checking for pkg-config... no" und danach "Checking for SDL... no". Ist PKG_CONFIG_LIBDIR
# gesetzt, bleibt es bei pkg-config und durchsucht genau diese Verzeichnisse.
export PKG_CONFIG_LIBDIR="$SDL2_MINGW_DIR/lib/pkgconfig:$MINGW_PREFIX/lib/pkgconfig"

# Add toolchain to PATH
export PATH="$LLVM_TOOLCHAIN:$SDL2_MINGW_DIR/bin:$PATH"

# Auf macOS findet llvm-windres den Apple-clang in /usr/bin und preprocessed damit fuer
# Darwin statt fuer Windows; llvm-rc bricht dann mit "expected int or identifier, got -" ab.
# Der Preprocessor wird deshalb fest auf den MinGW-clang der Toolchain gelegt.
if [ "$(uname -s)" = "Darwin" ]; then
    export WINDRES="x86_64-w64-mingw32-windres --preprocessor=$LLVM_TOOLCHAIN/x86_64-w64-mingw32-gcc --preprocessor-arg=-E"
fi
export SDL_CONFIG="$SDL2_MINGW_DIR/bin/sdl2-config"

# Cross-Compiler explizit setzen. Ohne diese zwei Zeilen nahm configure den Host-g++
# (config.log: "g++: error: unrecognized command-line option '-mwindows'"), und der
# SDL-Test scheiterte, obwohl der MinGW-Compiler daneben liegt.
if [ -x "$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++" ]; then
    export CC="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-gcc"
    export CXX="$LLVM_TOOLCHAIN/x86_64-w64-mingw32-g++"
fi

# configure benennt das Werkzeug fuer Cross-Builds um: es sucht "$host-pkg-config", also
# x86_64-w64-mingw32-pkg-config (configure Zeile ~3973). Gibt es das nicht, faellt die
# pkg-config-Pruefung auf "no" und danach auch SDL. Ein duenner Wrapper loest das, ohne
# dass am Fremdcode etwas geaendert werden muss.
SHIM_DIR="$FORK_DIR/build-windows/shim"
mkdir -p "$SHIM_DIR"
printf "#!/bin/sh\nexec pkg-config \"\$@\"\n" > "$SHIM_DIR/x86_64-w64-mingw32-pkg-config"
chmod +x "$SHIM_DIR/x86_64-w64-mingw32-pkg-config"
export PATH="$SHIM_DIR:$PATH"

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
        # Ohne diese Zeile findet configure das eben gebaute SDL2 nicht und meldet
        # "Checking for SDL... no", obwohl sdl2-config daneben liegt.
        --with-sdl-prefix="$SDL2_MINGW_DIR"
        --opengl-mode=gl
        --enable-verbose-build
        --disable-nasm
        --disable-all-engines
        --enable-engine=scumm,scumm-7-8
    )

    # Vollstaendige Ausgabe mitschreiben. "| tail -5" hat bei der Fehlersuche genau die Zeile
# verschluckt, die den Grund nennt (warum pkg-config/SDL nicht gefunden wurde).
"$FORK_DIR/configure" "${CONFIG_ARGS[@]}" > "$BUILD_DIR_WIN/configure.log" 2>&1 || {
        err "configure failed, full output: $BUILD_DIR_WIN/configure.log"
        tail -20 "$BUILD_DIR_WIN/configure.log"
        exit 1
    }
    tail -5 "$BUILD_DIR_WIN/configure.log"

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
# WINDRES per Make-Variable setzen: config.mk schreibt "WINDRES := ..." und ueberschreibt
# eine reine Umgebungsvariable. Auf macOS muss der Preprocessor der Toolchain genannt werden,
# sonst nimmt llvm-windres den Apple-clang und llvm-rc kann dessen Ausgabe nicht lesen.
MAKE_WINDRES=()
if [ "$(uname -s)" = "Darwin" ]; then
    MAKE_WINDRES=("WINDRES=$LLVM_TOOLCHAIN/x86_64-w64-mingw32-windres --preprocessor=$LLVM_TOOLCHAIN/x86_64-w64-mingw32-gcc --preprocessor-arg=-E")
fi
if ! make -j$(ncores) "${MAKE_WINDRES[@]}" > "$FORK_DIR/build-windows/make.log" 2>&1; then
    err "make failed — last lines of build-windows/make.log:"
    tail -40 "$FORK_DIR/build-windows/make.log"
    exit 1
fi
tail -5 "$FORK_DIR/build-windows/make.log"

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

# ── Verify zlib-ng made it into the binary ──────────────
# Ohne diesen Nachweis merkt niemand, dass Windows wieder mit zlib 1.3.1
# dekodiert, waehrend Linux zlib-ng hat (gleiche Pixel, nur 1,5-mal langsamer).
if [ "$(strings "$SCUMMVM_WIN" 2>/dev/null | grep -c "zlib-ng")" -eq 0 ]; then
    warn "scummvm.exe enthaelt kein zlib-ng — Windows dekodiert langsamer als Linux."
    warn "  Behebung: bash build/_build-zlibng-mingw.sh, dann neu linken."
fi

# Die selbst gebaute SDL2.dll (1.5 MB) laeuft nicht: kein Ton, keine Cutscenes, Einfrieren beim
# Blick vom Schiff (siehe Issue #32). Die erprobte Fassung (7.3 MB) liegt mit ihrer Abhaengigkeit
# zlib1.dll in release/windows/. Deshalb wird sie hier ins Ausgabeverzeichnis gelegt, damit ein
# frischer Build dieselben Dateien erzeugt wie das Release.
RELEASE_WIN="$REPO_DIR/release/windows"
for dep in SDL2.dll zlib1.dll; do
    if [ -f "$RELEASE_WIN/$dep" ]; then
        cp -f "$RELEASE_WIN/$dep" "$BUILD_DIR/out/$dep"
        ok "shipped $dep from release/windows ($(du -h "$BUILD_DIR/out/$dep" | cut -f1))"
    else
        warn "release/windows/$dep fehlt — der Build ist ohne diese Datei nicht lauffaehig"
    fi
done
ok "Windows binary: $SCUMMVM_WIN ($(du -h "$SCUMMVM_WIN" | cut -f1))"
