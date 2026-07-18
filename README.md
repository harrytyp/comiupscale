# COMI-HD — Curse of Monkey Island HD Upscale

![COMI-HD Screenshot](docs/screenshots/room9.png)
*Room 9 (Cannon Gallery) with HD textures — 4x upscale*

---

## Overview

COMI-HD is a **ScummVM fork** that renders Curse of Monkey Island (COMI / SCUMM v8) in **4x HD**. It loads external HD textures (backgrounds, costumes, objects, fonts, videos) from an `hd/` directory and scales coordinates at runtime — no original game file patching required.

### Features
- ⚡ **4x HD** (2560×1920) — AI-upscaled textures via RealESRGAN
- 🎭 **25,303 costume frames** — HD characters in full detail
- 🖼️ **81 HD backgrounds** — every room upscaled
- 🎬 **15 HD videos** — AI-upscaled cutscenes (optional)
- 🔧 **No patching** — original game files remain untouched

---

## Choose Your Path

There are two ways to get COMI-HD running — pick the one that suits you:

### 🚀 Path A: Quick Start (Pre-built)
Download everything — game files from your legal copy, HD assets from GitHub, binaries from releases.

### 🛠️ Path B: Build Everything Yourself
Extract original assets, upscale with RealESRGAN, build the ScummVM fork from source — full control.

---

## Path A: Quick Start — Download & Play

### 1. Get the Game

You need a **legal copy of "The Curse of Monkey Island"**.

| Source | Link | Price |
|--------|------|:-----:|
| **Steam** | https://store.steampowered.com/app/730820/ | ~€5 |
| **GOG** | https://www.gog.com/en/game/the_curse_of_monkey_island | ~€5, DRM-free |

Copy these files into a `game/` folder:
- `COMI.LA0`, `COMI.LA1`, `COMI.LA2`, `RESOURCE/`

### 2. Download HD Assets

**Binary + HD textures from GitHub Releases:**

| Release | Link | Contents | Size |
|---------|------|----------|:----:|
| **Binary** | [v0.0.64](https://github.com/harrytyp/comiupscale/releases/tag/v0.0.64) | `scummvm.exe` (Windows) + `scummvm` (Linux) + `scummvm-win-bundle.zip` (SDL2.dll, config) | ~170 MB |
| **HD Assets** | [hd_assets_v1.0.3](https://github.com/harrytyp/comiupscale/releases/tag/hd_assets_v1.0.3) | Backgrounds, objects, costumes, fonts (3 ZIP parts) | ~4.8 GB |

**Installation:**
1. Download the binary for your OS from the latest release
2. Download all 3 parts from `hd_assets_v1.0.3`
3. Extract each ZIP into the same folder — they merge into `hd/`
4. Also grab config files from the repo: [`release/windows/`](release/windows/) — `scummvm.ini`, `start_comi_hd.bat`
5. **Windows only:** Build `SDL2.dll` with audio (see [Building SDL2](#building-sdl2-for-windows))

**Final folder structure:**
```
your-game-folder/
├── game/              ← your COMI game data (COMI.LA0, etc.)
├── hd/                ← HD textures (from release ZIPs)
├── scummvm.exe        ← from GitHub Releases
├── SDL2.dll           ← Windows: built with audio support
├── zlib1.dll          ← Windows: from MinGW
├── scummvm.ini        ← from release/windows/
├── start_comi_hd.bat  ← from release/windows/
└── playback_comi_hd.bat
```

### 3. 4K Cutscenes (Optional)
For 4K upscaled cutscenes by **ubertrout** (~6 GB):
📥 https://archive.org/details/COMI_4k
Extract into `hd/videos/`. Without these, cutscenes play in original SD.

### 4. Run
**Windows:** Double-click `start_comi_hd.bat`
**Linux:** `chmod +x scummvm && ./start_comi_hd.sh`

First launch shows the difficulty selection screen. Select a difficulty and the game starts with HD textures.

---

## Path B: Build Everything Yourself

### B1. Extract Original Assets

Requirements: Python 3 with `numpy` and `Pillow`, plus the custom NUTcracker fork (included in this repo at `tools/nutcracker/`).

```bash
# Install Python dependencies
pip install numpy Pillow

# Add the custom NUTcracker to your Python path
export PYTHONPATH=tools:$PYTHONPATH

# Extract all assets (backgrounds, objects, costumes, fonts)
python scripts/extract_all_raw.py --game /path/to/COMI --output extracted/
python scripts/extract_akos.py --game /path/to/COMI --output extracted/
```

> **Note:** This repo includes a **custom NUTcracker fork** at `tools/nutcracker/` with AKOS costume decoder support added specifically for COMI HD. The original NUTcracker does not support AKOS decoding. See [`docs/SCRIPT_INVENTORY.md`](docs/SCRIPT_INVENTORY.md) for details on all extraction scripts.

See `scripts/full_pipeline.sh` for the full automated extraction pipeline:
```bash
bash scripts/full_pipeline.sh --game /path/to/COMI --skip-upscale --skip-build
```

Extracted assets (~38,000 PNGs):
- 40 backgrounds (room images)
- 600 object textures
- 234 object layer textures
- 25,304 costume frames
- 5 fonts
- 12,506 cutscene frames

### B2. Upscale with RealESRGAN

Requirements: [RealESRGAN-NCNN-Vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan)

```bash
# Batch upscale all extracted assets
python scripts/batch_upscale_costumes.py --input extracted/ --output hd/ --model realesrgan-x4plus-anime

# Or use the full pipeline with upscaling:
bash scripts/full_pipeline.sh --game /path/to/COMI --skip-build
```

The build uses the `realesrgan-x4plus-anime` model (or `realesrgan-x4plus` for photorealism). Each asset is upscaled 4× independently.

### B3. Build the ScummVM Fork

See [`build/BUILD.md`](build/BUILD.md) for the complete build guide.

```bash
# Prerequisites (Ubuntu/Debian)
sudo apt install build-essential cmake pkg-config curl

# Build both Linux + Windows binaries
bash build/build-all.sh

# Build individually:
bash build/build-all.sh linux    # Linux only
bash build/build-all.sh windows  # Windows only (cross-compile from Linux)
```

**Artifacts appear in `build/out/`:**
- `build/out/scummvm` — Linux binary
- `build/out/scummvm.exe` — Windows binary

The build system is fully self-contained — it downloads LLVM MinGW, SDL2, zlib, and libpng from source. No system packages beyond build-essential are required.

#### Building SDL2 for Windows

The Windows binary needs `SDL2.dll` with audio support:

```bash
cd build/deps/SDL2-2.30.11
./configure --host=x86_64-w64-mingw32 \
    --enable-audio --enable-directsound --enable-wasapi --enable-winmm \
    --disable-joystick --disable-haptic
make -j4 && make install
```

Result: `build/install/sdl2-mingw/bin/SDL2.dll` (7.4 MB, with directsound/wasapi/winmm)

### B4. Assemble & Play

```
your-game-folder/
├── game/              ← your COMI game data
├── hd/                ← your upscaled HD textures (from step B2)
├── scummvm.exe        ← from build/out/ (step B3)
├── SDL2.dll           ← built with audio (step B3)
├── zlib1.dll          ← from MinGW (build/install/mingw-prefix/bin/)
├── scummvm.ini        ← from release/windows/scummvm.ini
├── start_comi_hd.bat  ← from release/windows/
└── playback_comi_hd.bat
```

---

## Controls

| Key | Action |
|-----|--------|
| `F5` | Menu (Save/Load) |
| `Ctrl` + `F5` | ScummVM Menu |
| `Ctrl` + `d` | Debug Console |
| `Alt` + `Enter` | Toggle Fullscreen |
| `Esc` | Skip/Back |
| Mouse | Classic Point-and-Click |

---

## Configuration

Key options in `scummvm.ini` under `[comi]`:

| Option | Default | Description |
|--------|---------|-------------|
| `hd_path` | `hd` | Path to HD textures (relative to game dir) |
| `path` | `game` | Path to COMI game data |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| No sound, no video | SDL2.dll built without audio | Rebuild SDL2 with `--enable-audio` |
| Black screen on startup | Missing game data | Check `game/` has `COMI.LA0` etc. |
| HD textures not loading | Missing `hd/` directory | Download or generate HD asset pack |
| Persistent dark overlay at top | Old build | Update to latest (includes inventory fix) |
| High GPU usage | No frame limiter in old builds | Update to latest (has ~30fps cap) |

---

## Technical Details

### ScummVM Fork
- **Base:** ScummVM (custom fork)
- **HD Asset Manager:** Loads external textures from `hd/` directory
- **Coordinate Scaling:** Automatic SD→HD coordinate mapping at runtime
- **Engine Support:** SCUMM v0-v6, v7 & v8 (COMI, Full Throttle, The Dig, etc.)
- **Build:** LLVM MinGW cross-compile (Windows) + GCC (Linux)

### HD Assets
- **Upscaling:** RealESRGAN `x4plus_anime_6B` model
- **Backgrounds:** Original ROOM/IMAG → PNG → 4x upscale → PNG
- **Costumes:** AKOS → PNG frames → 4x upscale → PNG
- **Objects:** 600 foreground + 234 layer textures
- **Videos:** HNM → MP4 → 4x upscale (Topaz) → MP4

### Known Issues
- **Inventory FLOBJ positioning:** Inventory HD textures all render at (0,0) because V8 uses a draw queue for positioning, not object coordinates. Items are visible but at the wrong position.
- **SMUSH video skip:** Fixed in latest build — `_hdDebugDumpCount` no longer affects the SMUSH player.

---

## Repository Structure

```
comiupscale/
├── README.md                  ← This file
├── build/                     ← Build system (self-contained)
│   ├── BUILD.md               ← Detailed build guide
│   └── build-all.sh           ← Main build script
├── release/windows/           ← Config files, launchers
├── scummvm/fork/              ← Modified ScummVM source
│   └── engines/scumm/         ← HD rendering engine
├── scripts/                   ← Extraction, upscaling, testing
│   ├── full_pipeline.sh       ← End-to-end: extract → upscale → build
│   ├── extract_akos.py        ← AKOS costume extraction
│   ├── upscale_esrgan.py      ← RealESRGAN batch upscale
│   └── ...
└── docs/                      ← Technical documentation
```

---

## Documentation Index

| File | Contents |
|------|----------|
| [`build/BUILD.md`](build/BUILD.md) | Detailed build guide (prerequisites, steps, troubleshooting) |
| [`scripts/full_pipeline.sh`](scripts/full_pipeline.sh) | End-to-end automation: extract → upscale → build → play |
| [`docs/v8-rendering-pipeline.md`](docs/v8-rendering-pipeline.md) | COMI V8 Rendering Pipeline — FLOBJs, AKOS, Verb-System, HD-Compositing |
| [`docs/HD_MANIFEST_SPEC.md`](docs/HD_MANIFEST_SPEC.md) | HD manifest format for custom asset mapping |
| [`setup.sh`](setup.sh) | Quick setup script (downloads binary + assets) |

---

## Acknowledgments

| Person/Project | For | Link |
|----------------|-----|:----:|
| **ScummVM Team** | The engine that makes this possible | [scummvm.org](https://www.scummvm.org/) |
| **NUTcracker (BLooperZ / pycd02)** | Asset extraction toolkit (AKOS decoder) | [GitHub](https://github.com/BLooperZ/nutcracker) |
| **RealESRGAN (xinntao)** | AI upscaling model (x4plus_anime_6B) | [GitHub](https://github.com/xinntao/Real-ESRGAN) |
| **MMUCS (haywirephoenix)** | Godot-powered SCUMM V8 content explorer | [GitHub](https://github.com/haywirephoenix/MMUCS) |
| **Happy-Ferret (Mark Bauermeister)** | Pioneering ScummVM v6 HD fork | [Patreon](https://patreon.com/HappyFerret) |
| **Laserschwert** | Early ESRGAN upscales (2020) | MixnMojo |
| **ubertrout** | 4K Topaz Video upscale of all COMI cutscenes | [Archive](https://archive.org/details/COMI_4k) |

---

## License

- **ScummVM fork:** GPL v2 — https://www.scummvm.org/
- **Documentation:** MIT License
- **Game Data:** © LucasArts / Disney — not included

*COMI-HD is a fan project. Not affiliated with LucasArts, Disney, or ScummVM.*
