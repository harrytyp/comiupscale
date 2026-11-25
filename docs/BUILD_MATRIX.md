# Build-Matrix — was wo gebaut wird

Diese Tabelle ist der verbindliche Stand. Jede Zeile ist ein CI-Job in
`.github/workflows/build.yml`, der auf einem frisch installierten Runner startet und seine
Abhängigkeiten selbst installiert. Es gibt keine Zeile, die nur „sollte gehen" müsste.

| Host (wo du baust) | Befehl | Ergebnis | Nachweis |
|---|---|---|---|
| Linux (x86_64) | `bash build/build-all.sh` | Linux-Binary **und** Windows-exe | CI-Job `Linux -> Linux + Windows`: grün |
| macOS (Apple Silicon) | `bash build/build-all.sh` | macOS-Binary **und** Windows-exe | CI-Job `macOS -> macOS + Windows`: grün |
| Windows (MSYS2, MINGW64) | `bash build/build-all.sh native` | Windows-exe nativ | CI-Job `Windows (MSYS2) -> Windows`: grün |
| Windows (WSL) | `bash build/build-all.sh` | wie Linux | kein eigener Job, gleiche Skripte wie Linux |

Ergebnisse liegen in `build/out/`:

| Datei | Plattform | Format |
|---|---|---|
| `build/out/scummvm` | Linux | ELF x86_64 |
| `build/out/scummvm` | macOS | Mach-O arm64 |
| `build/out/scummvm.exe` | Windows | PE x86_64 |

## Einzelne Ziele

```bash
bash build/build-all.sh            # alles, was auf diesem Rechner geht (native + Windows-Cross)
bash build/build-all.sh native     # nur das eigene System
bash build/build-all.sh linux      # Linux-Binary, auch von macOS aus
bash build/build-all.sh macos      # macOS-Binary, nur auf macOS sinnvoll
bash build/build-all.sh windows    # Windows-exe per llvm-mingw, aus Linux ODER macOS
```

`native` ist der Befehl für Nutzer: er löst selbst auf, ob Linux, macOS oder Windows gemeint ist.
Unter MSYS2 ist das Ergebnis eine Windows-exe, unter macOS ein Mach-O-Binary, unter Linux ein ELF.
Auf einem Windows-Rechner ohne MSYS2 gibt es keinen Build-Pfad; nimm WSL oder MSYS2.

## Abhängigkeiten

`bash build/install-deps.sh` erkennt den Paketmanager und installiert, was fehlt:

| System | Paketmanager | Erkannt über |
|---|---|---|
| Debian/Ubuntu | apt | `apt-get` |
| Fedora/RHEL | dnf | `dnf` |
| Arch | pacman | `pacman` |
| openSUSE | zypper | `zypper` |
| macOS | brew | `uname -s` = Darwin |
| Windows/MSYS2 | pacman (mingw-w64) | `$MSYSTEM` |

`build-all.sh` ruft das automatisch auf. `--no-deps` schaltet es ab und zeigt nur die Liste.
`sudo` wird nur vorangestellt, wenn es existiert und wir nicht schon root sind; für brew nie.

## Windows-Cross im Detail

Beide Nicht-Windows-Hosts benutzen llvm-mingw, aber unterschiedliche Archive:
`build/deps.list` wählt anhand von `uname -s`/`uname -m`

- Linux x86_64 → `llvm-mingw-<v>-ucrt-ubuntu-22.04-x86_64.tar.xz`
- Linux aarch64 → `llvm-mingw-<v>-ucrt-ubuntu-22.04-aarch64.tar.xz`
- macOS (Intel und Apple Silicon) → `llvm-mingw-<v>-ucrt-macos-universal.tar.xz`

Was dabei schiefgehen kann und warum es behoben ist, steht in `docs/WINDOWS-CROSS-PITFALLS.md`.

## Was nicht geht, und warum

**Linux-Binary von Windows aus.** Es gibt keine fertige Toolchain, die aus einem MSYS2-Shell ein
Linux-ELF mit glibc erzeugt. Wer das braucht, nimmt WSL; dort laufen dieselben Skripte wie unter
Linux, und der Linux-Job der CI deckt genau diesen Pfad ab.

**Windows-Cross von Windows aus.** Nicht nötig: unter MSYS2 ist der native Build bereits eine
Windows-exe.

**macOS-Binary von Linux oder Windows aus.** Braucht das Apple-SDK, das nicht weitergegeben werden
darf. macOS-Binaries entstehen deshalb nur auf einem Mac.

**Intel-macOS-Binary.** Die CI baut auf `macos-latest`, das ist Apple Silicon; das Ergebnis ist
arm64. Wer einen Intel-Mac hat, baut lokal mit `bash build/build-all.sh macos`.
