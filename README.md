# COMI-HD — Curse of Monkey Island HD Upscale

![COMI-HD Screenshot](docs/screenshots/room9.png)
*Room 9 (Cannon Gallery) with HD textures — 4x upscale*

---

## Overview

COMI-HD is a **ScummVM fork** that renders Curse of Monkey Island (COMI / SCUMM v8) in **4x HD**. It loads external HD textures (backgrounds, costumes, objects, fonts) from an `hd/` directory and scales coordinates at runtime — no original game file patching required.

### Features
- ⚡ **4x HD** (2560×1920) — AI-upscaled textures via RealESRGAN
- 🎭 **25,303 costume frames** — HD characters in full detail
- 🖼️ **81 HD backgrounds** — every room upscaled
- 🎬 **15 HD videos** — AI-upscaled cutscenes
- 🔧 **No patching** — original game files remain untouched

---

## Downloads

The release is split into **3 parts**:

| Part | Content | Size | Source |
|------|---------|:----:|:------:|
| 1. Game | COMI.LA0, LA1, LA2 | 82 MB | [GitHub Release](https://github.com/harrytyp/comiupscale/releases/tag/v1.0.2) |
| 2. HD Assets | Backgrounds, Videos, Costumes, Objects, Fonts | 8.8 GB | [MEGA](/comi_hd_v1.0.2/hd/) |
| 3. ScummVM Build | scummvm.exe, SDL2.dll, zlib1.dll, Scripts | 26 MB | [GitHub Release](https://github.com/harrytyp/comiupscale/releases/tag/v1.0.2) |

### 1. Game Files (`comi_hd_game.zip`)
Original Curse of Monkey Island data:
- `COMI.LA0`
- `COMI.LA1`
- `COMI.LA2`

→ Extract into your `COMI/` directory.

### 2. HD Assets (MEGA)
```
/comi_hd_v1.0.2/hd/
├── backgrounds/   (81 HD backgrounds, 2560×1920)
├── costumes/      (25,303 costume frames)
├── videos/        (15 upscaled cutscenes)
├── objects/       (600 HD objects)
├── fonts/         (5 HD fonts)
└── object_map.json
```
→ Extract into the game directory (next to `game/hd/`).

### 3. ScummVM Build (`comi_hd_build.zip`)
| File | Description |
|------|-------------|
| `scummvm.exe` | ScummVM v1.0.2 with HD support (scumm_7_8 engine) |
| `SDL2.dll` | SDL2 runtime |
| `zlib1.dll` | Zlib runtime |
| `start_comi_hd.bat` | Windows launcher script |
| `start_comi_hd.sh` | Linux launcher script |
| `scummvm.ini` | Preconfigured ScummVM config |

---

## Installation

### Windows
1. Extract `comi_hd_game.zip` → `COMI/`
2. Extract `comi_hd_build.zip` → `comi_hd_v1.0.2/`
3. Extract HD Assets from MEGA → `comi_hd_v1.0.2/hd/`
4. Run `start_comi_hd.bat`

### Linux
1. Extract `comi_hd_game.zip` → `COMI/`
2. Extract `comi_hd_build.zip` → `comi_hd_v1.0.2/`
3. Extract HD Assets from MEGA → `comi_hd_v1.0.2/hd/`
4. `chmod +x scummvm start_comi_hd.sh`
5. Run `./start_comi_hd.sh`

---

## HD Comparison

![HD Background Room 9](docs/screenshots/hd_background_room9.png)
*HD Background for Room 9 (2560×1920) — 4x upscale*

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
- **Videos:** HNM → MP4 → 4x upscale (Topaz) → MP4

---

## Changelog

### v1.0.2 (Current)
- ✅ scumm_7_8 engine enabled
- ✅ Room-warp debug feature removed
- ✅ Relative game path in `start_comi_hd.bat`
- ✅ SDL2.dll + zlib1.dll included

### v1.0.1
- HD asset pipeline stabilized
- Costume rendering optimized

### v1.0.0
- Initial release with HD backgrounds
- Basic costume support

---

## Acknowledgments

This project builds on the work of many people in the SCUMM modding community:

### Tools & Libraries
- **ScummVM Team** — The amazing engine that makes all this possible. [scummvm.org](https://www.scummvm.org/)
- **NUTcracker** ([BLooperZ](https://github.com/BLooperZ/nutcracker) / pycd02) — Asset extraction toolkit for SCUMM games. The AKOS costume decoder was added specifically for COMI upscaling.
- **RealESRGAN** ([xinntao](https://github.com/xinntao/Real-ESRGAN)) — AI upscaling model (`x4plus_anime_6B`) used for all backgrounds, objects, and costumes.
- **MMUCS** ([haywirephoenix](https://github.com/haywirephoenix/MMUCS)) — Godot-powered SCUMM V8 content explorer. Groundbreaking work on COMI modding and AKOS rendering.

### Research & Predecessors
- **Happy-Ferret (Mark Bauermeister)** — Pioneering work on a ScummVM v6 HD fork with external texture loading. [patreon.com/HappyFerret](https://patreon.com/HappyFerret)
- **Laserschwert** — Early ESRGAN upscales of COMI assets (2020). MixnMojo veteran.
- **haywirephoenix** — Requested and tested AKOS support in NUTcracker, created ScummRev (AKOS viewer predecessor), built MMUCS.
- **ubertrout** — 4K Topaz Video upscale of all COMI cutscenes. [archive.org/details/COMI_4k](https://archive.org/details/COMI_4k)

### HD Assets
- **Original Game:** © LucasArts / Disney (1998). Game data not included.
- **HD Textures:** AI-upscaled using RealESRGAN. Licensed under CC BY-NC-SA 4.0.
- **4K Videos:** Upscaled by ubertrout using Topaz Video AI. Available at the link above.

---

*COMI-HD is a fan project. Not affiliated with LucasArts, Disney, or ScummVM.*
