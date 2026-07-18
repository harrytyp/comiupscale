#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# COMI-HD — Quick Setup Script
# ============================================================
# Downloads the pre-built ScummVM HD binary and HD texture packs
# from GitHub Releases, plus optional 4K cutscenes from archive.org.
#
# Usage:
#   ./setup.sh --game /path/to/COMI
#
# Flags:
#   --game PATH     Path to your COMI game directory (COMI.LA0/1/2)
#   --binary VER    Binary release tag to use (default: v0.0.64)
#   --assets VER    HD assets release tag (default: hd_assets_v1.0.3)
#   --no-videos     Skip 4K cutscene download from archive.org
#   --help          Show this message
# ============================================================

GH_REPO="harrytyp/comiupscale"
GAME_DIR=""
BINARY_TAG="v0.0.64"
ASSETS_TAG="hd_assets_v1.0.3"
NO_VIDEOS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --game)     GAME_DIR="$2"; shift 2 ;;
        --binary)   BINARY_TAG="$2"; shift 2 ;;
        --assets)   ASSETS_TAG="$2"; shift 2 ;;
        --no-videos) NO_VIDEOS=true; shift ;;
        --help)     grep "^#" "$0" | head -30 | cut -c3-; exit 0 ;;
        *)          echo "Unknown: $1"; exit 1 ;;
    esac
done

if [ -z "$GAME_DIR" ]; then
    echo "ERROR: --game is required. Usage: ./setup.sh --game /path/to/COMI"
    exit 1
fi

GAME_DIR="$(realpath "$GAME_DIR")"
OUTPUT_DIR="$(pwd)/game"

echo "=== COMI-HD Setup ==="
echo "Game files:  $GAME_DIR"
echo "Output dir:  $OUTPUT_DIR"
echo "Binary:      $BINARY_TAG"
echo "HD Assets:   $ASSETS_TAG"
echo ""

# --- Step 1: Verify game files ---
echo "[1/6] Verifying game files..."
LA0=$(find "$GAME_DIR" -maxdepth 1 -iname "COMI.LA0" -print -quit)
LA1=$(find "$GAME_DIR" -maxdepth 1 -iname "COMI.LA1" -print -quit)
LA2=$(find "$GAME_DIR" -maxdepth 1 -iname "COMI.LA2" -print -quit)
if [ -z "$LA0" ] || [ -z "$LA1" ] || [ -z "$LA2" ]; then
    echo "ERROR: COMI.LA0, COMI.LA1, COMI.LA2 not found in $GAME_DIR"
    exit 1
fi
echo "  ✅ COMI.LA0/1/2 found"

# --- Step 2: Create output directory ---
echo "[2/6] Creating output directory..."
mkdir -p "$OUTPUT_DIR/game" "$OUTPUT_DIR/hd"

# --- Step 3: Download ScummVM HD binary ---
echo "[3/6] Downloading ScummVM HD binary..."
OS="$(uname -s)"
if [ "$OS" = "Linux" ]; then
    BINARY_NAME="scummvm"
else
    BINARY_NAME="scummvm.exe"
fi

API_URL="https://api.github.com/repos/$GH_REPO/releases/tags/$BINARY_TAG"
ASSET_URL=$(curl -sL "$API_URL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if asset['name'] == '$BINARY_NAME':
        print(asset['browser_download_url'])
        break
")

if [ -z "$ASSET_URL" ]; then
    echo "  ⚠️  Binary not found for $BINARY_TAG/$BINARY_NAME"
    echo "  You'll need to build from source (see build/BUILD.md)"
else
    echo "  Downloading $BINARY_NAME..."
    curl -L -o "$OUTPUT_DIR/$BINARY_NAME" "$ASSET_URL"
    chmod +x "$OUTPUT_DIR/$BINARY_NAME"
    echo "  ✅ $BINARY_NAME ($(du -h "$OUTPUT_DIR/$BINARY_NAME" | cut -f1))"
fi

# Windows: also download the bundle (SDL2.dll, config, launchers)
if [ "$OS" != "Linux" ]; then
    BUNDLE_URL=$(curl -sL "$API_URL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if asset['name'] == 'scummvm-win-bundle.zip':
        print(asset['browser_download_url'])
        break
    ")
    if [ -n "$BUNDLE_URL" ]; then
        echo "  Downloading scummvm-win-bundle.zip (SDL2.dll, config)..."
        curl -L -o /tmp/win-bundle.zip "$BUNDLE_URL"
        unzip -o -q /tmp/win-bundle.zip -d "$OUTPUT_DIR/"
        rm -f /tmp/win-bundle.zip
        echo "  ✅ Windows bundle extracted (SDL2.dll, config, launchers)"
    fi
fi

# --- Step 4: Download HD assets ---
echo "[4/6] Downloading HD texture packs..."
ASSETS_API="https://api.github.com/repos/$GH_REPO/releases/tags/$ASSETS_TAG"
PARTS=$(curl -sL "$ASSETS_API" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if asset['name'].startswith('hd_assets_part'):
        print(asset['browser_download_url'])
")

if [ -z "$PARTS" ]; then
    echo "  ⚠️  HD asset release not found ($ASSETS_TAG)"
else
    echo "$PARTS" | while read -r url; do
        fname=$(basename "$url")
        echo "  Downloading $fname..."
        curl -L -o "/tmp/$fname" "$url"
        echo "  Extracting $fname into hd/..."
        unzip -o -q "/tmp/$fname" -d "$OUTPUT_DIR/"
        rm -f "/tmp/$fname"
    done
    COUNT=$(find "$OUTPUT_DIR/hd" -type f 2>/dev/null | wc -l)
    echo "  ✅ $COUNT HD texture files extracted"
fi

# --- Step 5: Copy game files ---
echo "[5/6] Copying game files..."
cp "$LA0" "$OUTPUT_DIR/game/COMI.LA0"
cp "$LA1" "$OUTPUT_DIR/game/COMI.LA1"
cp "$LA2" "$OUTPUT_DIR/game/COMI.LA2"
echo "  ✅ Game files copied"

# --- Step 6: Download 4K cutscenes (optional) ---
if [ "$NO_VIDEOS" = false ]; then
    echo "[6/6] Downloading 4K cutscenes from archive.org..."
    echo "  Source: https://archive.org/details/COMI_4k"
    echo "  Run with --no-videos to skip this step."
    echo "  (Download manually if this fails: https://archive.org/details/COMI_4k)"
    mkdir -p "$OUTPUT_DIR/hd/videos"
    # Attempt to download from archive.org
    IA_BASE="https://archive.org/download/COMI_4k"
    IA_FILES=$(curl -sL "$IA_BASE/" | python3 -c "
import sys, re, html
content = sys.stdin.read()
for m in re.finditer(r'href=\"([^\"]+\.(mp4|avi|mkv))\">', content):
    print(html.unescape(m.group(1)))
" 2>/dev/null || echo "")
    if [ -n "$IA_FILES" ]; then
        echo "$IA_FILES" | while read -r fname; do
            echo "  Downloading $fname..."
            curl -L -o "$OUTPUT_DIR/hd/videos/$fname" "$IA_BASE/$fname"
        done
        echo "  ✅ 4K videos downloaded"
    else
        echo "  ⚠️  Could not fetch video list from archive.org"
    fi
else
    echo "[6/6] Skipping videos (--no-videos)"
fi

# --- Create launcher ---
if [ "$OS" = "Linux" ]; then
    cat > "$OUTPUT_DIR/start_comi_hd.sh" << 'SCRIPT'
#!/usr/bin/env bash
cd "$(dirname "$0")"
./scummvm --config=scummvm.ini --path=game --renderer=opengl comi
SCRIPT
    chmod +x "$OUTPUT_DIR/start_comi_hd.sh"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To play:"
if [ "$OS" = "Linux" ]; then
    echo "  cd $OUTPUT_DIR"
    echo "  ./start_comi_hd.sh"
    echo ""
    echo "Or manually:"
    echo "  cd $OUTPUT_DIR"
    echo "  ./scummvm --config=scummvm.ini --path=game --renderer=opengl comi"
else
    echo "  Open $OUTPUT_DIR in Explorer"
    echo "  Double-click start_comi_hd.bat"
fi
