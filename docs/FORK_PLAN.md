# ScummVM HD Fork — Technical Plan

## Overview

Modify ScummVM's SCUMM engine (`engines/scumm/`) to load 4x HD replacement
textures from an external directory. The engine renders at 2560x1920
(4x 640x480) and scales all coordinates at runtime.

## Architecture

### HD Asset Loading

A new `HDAssetManager` class sits between the SCUMM engine and the
renderer. When the engine loads a room:

1. `HDAssetManager::hasHD(roomId)` checks if `hd/room_XXXX.png` exists
   per the manifest or directory scan
2. If yes: load the HD PNG (RGBA8888) at full resolution
3. If no: fall back to the original palette-rendered background at 640x480,
   scaled up to 2560x1920 via the renderer

The HD PNGs are pre-scaled to 4x original. Panoramic rooms (1496x480,
2096x480, etc.) also get 4x scaling automatically.

### Coordinate Scaling

Every coordinate-bearing path in the SCUMM engine gets multiplied by 4:

| Component | File | What to scale |
|-----------|------|---------------|
| Actor position | `actor.cpp` | `_pos.x`, `_pos.y`, `_walkdata` |
| Walkboxes | `boxes.cpp` | All box corner coordinates |
| Object positions | `object.cpp` | `_x`, `_y`, `_width`, `_height` |
| Mouse/talk coordinates | `scummvm.cpp` | Input coordinates |
| Camera/scroll | `camera.cpp` | `_cur.x`, `_cur.y`, scroll limits |
| Screen shake | `scummvm.cpp` | Shake offset |
| Costume drawing | `costume.cpp` | Draw positions |
| Verb/sentence line | `verb.cpp` | UI positions |
| Room dimensions | `room.cpp` | `_roomWidth`, `_roomHeight` |

**Strategy:** Add a global `_hdScale` factor (4) to the SCUMM engine class.
All coordinate reads/writes through the engine go through `_hdScale`.

### Internal Resolution

- Base: 640x480 → HD: 2560x1920
- Panoramic rooms scale proportionally
- The game sets `_screenWidth` / `_screenHeight` in the engine init
- The backend (SDL) window is created at HD resolution
- Scaler pass (ScummVM's built-in 2x/3x etc.) is bypassed or set to 1x

### Files to Modify in `engines/scumm/`

```
New files:
  engines/scumm/hd_asset_manager.h     — HD asset manager header
  engines/scumm/hd_asset_manager.cpp   — HD asset manager impl

Modified files:
  engines/scumm/scumm.h                — add _hdScale, HDAssetManager ptr
  engines/scumm/scumm.cpp              — init HD assets, set resolution
  engines/scumm/room.cpp               — HD background loading
  engines/scumm/room_scumm.cpp         — room scaling
  engines/scumm/actor.h / actor.cpp    — coordinate * _hdScale
  engines/scumm/boxes.cpp              — walkbox * _hdScale
  engines/scumm/object.cpp             — object coords * _hdScale
  engines/scumm/costume.cpp            — costume draw pos * _hdScale
  engines/scumm/verb.cpp               — verb UI * _hdScale
  engines/scumm/camera.cpp             — camera * _hdScale
  engines/scumm/smush/smush_player.cpp — video positioning
  engines/scumm/script_v8.cpp          — V8 opcode handlers for coords
  graphics/surface.h / surface.cpp     — optional: HD surface support
```

### hd_manifest.json Format

Place a `hd_manifest.json` in the game directory next to COMI.LA0.

```json
{
  "version": 1,
  "engine": "scumm",
  "game": "monkey3",
  "scale": 4,
  "assets": {
    "backgrounds": {
      "0001": { "file": "hd/bg_0001.png", "w": 2560, "h": 1920 },
      "0002": { "file": "hd/bg_0002.png", "w": 2560, "h": 1920 },
      "0015": { "file": "hd/bg_0015.png", "w": 8384, "h": 1920 }
    },
    "objects": {
      "0001": { "file": "hd/obj_0001.png", "w": 2560, "h": 1920 }
    }
  },
  "metadata": {
    "upscale_model": "realesrgan-x4plus-anime",
    "created": "2026-05-23"
  }
}
```

Alternatively, for simplicity: scan `hd/` directory for `bg_*.png` files
and match by numeric ID. No manifest needed for backgrounds — the manifest
becomes useful later for per-object and per-costume overrides.

### Smush Video (Cutscenes)

SMUSH video is rendered separately from the room engine. Two options:
1. Replace SMUSH videos with pre-upscaled versions (container format)
2. Scale the SMUSH render surface within the fork

Option 1 is simpler — replace `.SAN` files in the game data with 4x versions.
Ubertrout's upscaled cutscenes are at archive.org/details/COMI_4k.

## Build Setup (Windows)

### Toolchain: MSYS2 + MinGW

```bash
# Install MSYS2, then:
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake \
          mingw-w64-x86_64-sdl2 mingw-w64-x86_64-freetype \
          mingw-w64-x86_64-libpng mingw-w64-x86_64-zlib \
          mingw-w64-x86_64-flac mingw-w64-x86_64-mad \
          mingw-w64-x86_64-vorbis mingw-w64-x86_64-theora \
          make git

# Clone
cd /z/Projekte/COMI-Upscaled
git clone https://github.com/scummvm/scummvm.git scummvm-fork

# Configure
cd scummvm-fork
./configure --backend=sdl --enable-optimizations --enable-release

# Build
make -j$(nproc)
```

### Code::Blocks / MSVC alternative
ScummVM also ships `dists/msvc/scummvm.sln` for Visual Studio.

## Testing Workflow

1. Place HD backgrounds in `ScummVM/monkey3/hd/` as `bg_XXXX.png`
2. Generate manifest (or let engine scan directory)
3. Launch modified ScummVM, load COMI
4. Walk through rooms, verify:
   - Background renders at 2560x1920
   - Actors are positioned correctly
   - Walkboxes work (click-to-walk lands correctly)
   - Objects interact properly
   - Dialogue/verbs render at correct positions
   - Cutscenes play (may show at original res initially)

## Milestones

| Step | Status | Description |
|------|--------|-------------|
| 1. Build env | 🔲 | MSYS2/MSVC toolchain working |
| 2. HD backgrounds | 🔲 | 1 room renders at 2560x1920 |
| 3. Walkbox scaling | 🔲 | Click-to-walk works in HD |
| 4. Object scaling | 🔲 | Objects clickable at correct positions |
| 5. Actor scaling | 🔲 | Characters walk to correct locations |
| 6. UI scaling | 🔲 | Verbs, inventory, dialogue work |
| 7. All 40 rooms | 🔲 | All backgrounds upscaled + tested |
| 8. Cutscenes | 🔲 | SMUSH video at HD |
| 9. Objects/costumes | 🔲 | HD object sprites, costume scaling |

## Reference: Happy-Ferret's Implementation

Happy-Ferret's "Open Remonkeyed" fork for Sam & Max (SCUMM v6):

- **HD backgrounds**: load via `hd_manifest.json` with per-room lighting
- **Internal resolution**: 1920x1440 (3x for SCUMM v6's 640x480)
- **TTF fonts**: override game font slots with system TTF
- **True Color**: RGBA8888 surfaces instead of CLUT8
- **HD actors**: implemented but calls it "MASSIVE undertaking"
- **RotSprite**: used for cursor/icon upscaling
- **Open source**: promised but not yet released (behind Patreon)

The v6 → v8 gap:
- SCUMM v8 has more complex opcodes (script_v8.cpp)
- SMUSH video is V8-only (v6 uses different animation system)
- Object/costume format differs between v6 and v8
- Palette handling is different in v8

### Key insight from Happy-Ferret
The core architecture (HD manifest + load-time swap + coordinate scaling)
is sound and validated. The per-asset complexity (costumes, objects)
is independent of the architecture — each can be tackled separately.
