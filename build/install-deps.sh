#!/usr/bin/env bash
# Installiert die Entwicklungspakete, die build/build-all.sh braucht.
# Erkennt die Distribution selbst und ruft den passenden Paketmanager.
#
#   bash build/install-deps.sh            # installiert (fragt nach sudo-Passwort)
#   bash build/install-deps.sh --dry-run  # zeigt nur, was installiert wuerde
#   bash build/install-deps.sh --check    # prueft nur, ob alles da ist
set -euo pipefail

DRY=0; CHECK=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --check)   CHECK=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unbekannte Option: $a"; exit 2 ;;
  esac
done

# Was gebraucht wird: C++-Werkzeuge, pkg-config, curl, X11 fuer SDL2, ALSA fuer Audio.
APT_PKGS="build-essential cmake pkg-config curl unzip python3 python3-venv \
libx11-dev libxext-dev libxcursor-dev libxi-dev libxfixes-dev libxrandr-dev libxinerama-dev libxss-dev \
libasound2-dev zlib1g-dev libpng-dev"
DNF_PKGS="gcc-c++ make cmake pkgconf-pkg-config curl unzip python3 \
libX11-devel libXext-devel libXcursor-devel libXi-devel libXfixes-devel libXrandr-devel libXinerama-devel libXScrnSaver-devel \
alsa-lib-devel zlib-devel libpng-devel"
PAC_PKGS="base-devel cmake pkgconf curl unzip python \
libx11 libxext libxcursor libxi libxfixes libxrandr libxinerama libxss \
alsa-lib zlib libpng"
ZYPP_PKGS="gcc-c++ make cmake pkg-config curl unzip python3 \
libX11-devel libXext-devel libXcursor-devel libXi-devel libXfixes-devel libXrandr-devel libXinerama-devel libXScrnSaver-devel \
alsa-devel zlib-devel libpng-devel"

# macOS und MSYS2 zuerst, sonst greift der Linux-Zweig auf einem Mac nie.
pm=""; pkgs=""
if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null; then
    pm="brew"
    pkgs="cmake pkg-config curl unzip sdl2 libpng"
elif [ -n "${MSYSTEM:-}" ] && command -v pacman >/dev/null; then
    pm="pacman"
    pkgs="mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-pkgconf \
mingw-w64-x86_64-SDL2 mingw-w64-x86_64-zlib mingw-w64-x86_64-libpng unzip"
elif command -v apt-get >/dev/null; then pm="apt"; pkgs="$APT_PKGS"
elif command -v dnf >/dev/null; then pm="dnf"; pkgs="$DNF_PKGS"
elif command -v pacman >/dev/null; then pm="pacman"; pkgs="$PAC_PKGS"
elif command -v zypper >/dev/null; then pm="zypper"; pkgs="$ZYPP_PKGS"
fi

if [ -z "$pm" ]; then
  cat <<'HINT'
Kein bekannter Paketmanager gefunden (apt, dnf, pacman, zypper).
Auf macOS:  xcode-select --install && brew install cmake pkg-config sdl2
Alles andere: build/build-all.sh --help zeigt, was gebraucht wird.
HINT
  exit 1
fi

missing=""
for p in ${pkgs}; do
  case "$pm" in
    brew) brew list --versions "$p" >/dev/null 2>&1 || missing="$missing $p" ;;
    apt) dpkg -s "$p" >/dev/null 2>&1 || missing="$missing $p" ;;
    dnf|zypper) rpm -q "$p" >/dev/null 2>&1 || missing="$missing $p" ;;
    pacman) pacman -Q "$p" >/dev/null 2>&1 || missing="$missing $p" ;;
  esac
done

if [ -z "$missing" ]; then
  echo "[OK]    Alle Pakete vorhanden ($pm)."
  exit 0
fi

echo "[INFO]  Paketmanager: $pm"
if [ "$CHECK" = 1 ]; then
  echo "[FEHLT] $missing"
  exit 1
fi

case "$pm" in
  brew)   cmd="brew install$missing" ;;
  apt)    cmd="apt-get install -y --no-install-recommends$missing" ;;
  dnf)    cmd="dnf install -y$missing" ;;
  pacman) cmd="pacman -S --needed --noconfirm$missing" ;;
  zypper) cmd="zypper install -y$missing" ;;
esac

if [ "$DRY" = 1 ]; then
  echo "[DRY]   sudo $cmd"
  exit 0
fi

if [ "$(id -u)" = "0" ]; then
  echo "[INFO]  $cmd"
  $cmd
else
  echo "[INFO]  sudo $cmd"
  sudo $cmd
fi
echo "[OK]    Abhaengigkeiten installiert. Jetzt: bash build/build-all.sh linux"
