#!/usr/bin/env bash
# ============================================================
# zlib-ng 2.3.3 fuer den Windows-Cross-Build (ersetzt zlib 1.3.1)
# Output: build/install/zlib-ng-2.3.3-mingw/{include,lib/libz.a}
#
# Warum: zlib-ng dekodiert 1,5-mal schneller (gemessen 2026-11-23, Linux
# 4,59 -> 3,04 ms je MB dekodiertes Bild, Pixel bytegleich). Eine neue
# Abhaengigkeit nur auf einer Plattform ist ein Release-Fallstrick, deshalb
# wird dieselbe Bibliothek auch fuer Windows gebaut, mit ZLIB_COMPAT=ON,
# damit libpng (gegen zlib 1.3.1 gebaut) unveraendert dagegen linken kann.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

ZNG_VERSION="2.3.3"
ZNG_SRC="$BUILD_DIR/deps/zlib-ng-$ZNG_VERSION"
ZNG_BUILD="$INSTALL_DIR/../out/zlibng-mingw-build"
ZNG_PREFIX="$INSTALL_DIR/zlib-ng-$ZNG_VERSION-mingw"

if [ ! -d "$ZNG_SRC" ]; then
    err "Quelle fehlt: $ZNG_SRC (zlib-ng $ZNG_VERSION entpacken)"
    exit 1
fi

export PATH="$LLVM_MINGW_DIR/bin:$PATH"

# CMAKE_SYSTEM_PROCESSOR ist Pflicht: ohne ihn bricht zlib-ngs CMake in der
# SIMD-Erkennung mit "Unknown arguments specified" ab (STREQUAL auf leerem Wert).
cmake -S "$ZNG_SRC" -B "$ZNG_BUILD" \
    -DCMAKE_SYSTEM_NAME=Windows \
    -DCMAKE_SYSTEM_PROCESSOR=x86_64 \
    -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
    -DZLIB_COMPAT=ON \
    -DBUILD_SHARED_LIBS=OFF \
    -DBUILD_TESTING=OFF \
    -DCMAKE_INSTALL_PREFIX="$ZNG_PREFIX" > /dev/null
cmake --build "$ZNG_BUILD" -j"$(ncores)" > /dev/null
cmake --install "$ZNG_BUILD" > /dev/null

if [ ! -f "$ZNG_PREFIX/lib/libz.a" ]; then
    err "libz.a fehlt in $ZNG_PREFIX/lib"
    exit 1
fi
# Nachweis im Archiv: inflate/uncompress unter den Standardnamen (ZLIB_COMPAT)
if [ "$(nm "$ZNG_PREFIX/lib/libz.a" | grep -cE ' T (zng_)?inflate$')" -eq 0 ]; then
    err "libz.a exportiert kein inflate — ZLIB_COMPAT nicht aktiv?"
    exit 1
fi

ok "zlib-ng $ZNG_VERSION (MinGW): $ZNG_PREFIX/lib/libz.a"
