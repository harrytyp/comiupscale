# Windows-Binary bauen

Das ausgelieferte `release/windows/scummvm.exe` ist aelter als die Engine-Aenderungen. In dieser
Umgebung gibt es keinen Cross-Compiler (kein mingw), deshalb muss es auf Windows oder in einer CI
gebaut werden. Der Linux-Weg ist davon unabhaengig.

## Auf Windows (MSYS2, empfohlen)

    pacman -S mingw-w64-x86_64-toolchain mingw-w64-x86_64-SDL2 mingw-w64-x86_64-libpng \
              mingw-w64-x86_64-zlib mingw-w64-x86_64-freetype mingw-w64-x86_64-make git
    git clone <repo> comi-hd && cd comi-hd/scummvm/fork
    ./configure --host=mingw32 --enable-release
    make -j"$(nproc)"

Ergebnis: `scummvm/fork/scummvm.exe`. Danach

    cp scummvm.exe ../../release/windows/

und in `release/windows` pruefen, dass es startet.

## In einer CI

Ein Windows-Runner mit MSYS2 erledigt dasselbe in einem Schritt; die Befehle oben sind die
vollstaendige Kette. Wichtig: danach `scripts/verify_release.sh` laufen lassen, damit das
Binary nicht wieder altert.

## Was das Tor prueft

`scripts/verify_release.sh` vergleicht das Datum von `release/windows/scummvm.exe` mit dem
juengsten Commit der Engine-Quellen. Ist das Binary aelter, meldet das Tor einen offenen Punkt.
