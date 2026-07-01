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

## Prerequisites

You need a **legal copy of "The Curse of Monkey Island"** to play. The original game files (`COMI.LA0`, `COMI.LA1`, `COMI.LA2`, `RESOURCE/`) are **not included** in this release.

| Source | Link | Price |
|--------|------|:-----:|
| **Steam** | https://store.steampowered.com/app/730820/ | ~€5 |
| **GOG** | https://www.gog.com/en/game/the_curse_of_monkey_island | ~€5, DRM-free |

## Downloads

This release contains the **ScummVM fork** and **HD texture packs** — no game data.

| Part | File | Size | Download |
|------|------|:----:|:--------:|
| 1. ScummVM Build | `comi_hd_build.zip` | 26 MB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/comi_hd_build.zip) |
| 2. HD Assets (Part 1) | `hd_assets_part1.zip` | 1.9 GB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/hd_assets_part1.zip) |
| 2. HD Assets (Part 2) | `hd_assets_part2.zip` | 1.9 GB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/hd_assets_part2.zip) |
| 2. HD Assets (Part 3) | `hd_assets_part3.zip` | 1.7 GB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/hd_assets_part3.zip) |
| 2. HD Assets (Part 4) | `hd_assets_part4.zip` | 0.9 GB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/hd_assets_part4.zip) |
| 2. HD Assets (Part 5) | `hd_assets_part5.zip` | 1.7 GB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/hd_assets_part5.zip) |
| 2. HD Assets (Part 6) | `hd_assets_part6.zip` | 0.8 GB | [⬇ Download](https://github.com/harrytyp/comiupscale/releases/download/v1.0.2/hd_assets_part6.zip) |

### ScummVM Build (`comi_hd_build.zip`)

| File | Description |
|------|-------------|
| `scummvm.exe` | ScummVM v1.0.2 with HD support (scumm_7_8 engine) |
| `SDL2.dll` | SDL2 runtime |
| `zlib1.dll` | Zlib runtime |
| `start_comi_hd.bat` | Windows launcher script |
| `start_comi_hd.sh` | Linux launcher script |
| `scummvm.ini` | Preconfigured ScummVM config |

### HD Assets (`hd_assets_part1.zip` – `hd_assets_part6.zip`)

```
hd/
├── backgrounds/   (81 HD backgrounds, 2560×1920)
├── costumes/      (25,303 costume frames)
├── videos/        (15 upscaled cutscenes)
├── objects/       (600 HD objects)
├── fonts/         (5 HD fonts)
└── object_map.json
```

→ Download all 6 parts, then extract all into the same directory (next to `game/hd/`).

---

## Installation

### Windows
1. Buy & install COMI from [Steam](https://store.steampowered.com/app/730820/) or [GOG](https://www.gog.com/en/game/the_curse_of_monkey_island)
2. Extract `comi_hd_build.zip` → `comi_hd_v1.0.2/`
3. Download & extract all 6 `hd_assets_part*.zip` → `comi_hd_v1.0.2/hd/`
4. Copy your COMI game data into the `game/` subdirectory
5. Run `start_comi_hd.bat`

### Linux
1. Buy & install COMI from [Steam](https://store.steampowered.com/app/730820/) or [GOG](https://www.gog.com/en/game/the_curse_of_monkey_island)
2. Extract `comi_hd_build.zip` → `comi_hd_v1.0.2/`
3. Download & extract all 6 `hd_assets_part*.zip` → `comi_hd_v1.0.2/hd/`
4. Copy your COMI game data into the `game/` subdirectory
5. `chmod +x scummvm start_comi_hd.sh`
6. Run `./start_comi_hd.sh`

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
- **4K Videos:** Upscaled by ubertrout using Topaz Video AI. Available at the link above.

---

*COMI-HD is a fan project. Not affiliated with LucasArts, Disney, or ScummVM.*

---

## Legal

### Disclaimer & Legal Analysis

This project is provided for **educational and archival purposes only**. We believe it falls within the boundaries of fair use / fair dealing, but we are not lawyers — this is not legal advice.

#### What this project IS:
- ✅ A **modified version of ScummVM** (GPL v2 licensed) that loads external HD textures
- ✅ **AI-upscaled textures** created by running artwork through RealESRGAN — a transformative process that produces new, higher-resolution image data
- ✅ **Configuration files** and **launcher scripts** to make everything work together

#### What this project does NOT distribute:
- ❌ **No original game code** from "The Curse of Monkey Island" (© LucasArts / Disney)
- ❌ **No original game assets** — no .LA0, .LA1, .LA2 files, no original room data
- ❌ **No ROMs, ISOs, or disk images**
- ❌ **No decryption keys or copy protection circumvention**

#### The User Must Provide:
The user must own a legitimate copy of "The Curse of Monkey Island" and extract the game data files themselves. This can be purchased from:
- [Steam](https://store.steampowered.com/app/730820/)
- [GOG.com](https://www.gog.com/en/game/the_curse_of_monkey_island)
- The original CD release

#### Trademarks

"Curse of Monkey Island", "Monkey Island", "LucasArts", and "Disney" are registered trademarks of their respective owners. This project is not endorsed by or affiliated with Disney, LucasArts, or any of their subsidiaries. All trademarks and copyrights are property of their respective holders.

#### License

- **ScummVM fork:** GPL v2 — [https://www.scummvm.org/](https://www.scummvm.org/)
- **Documentation:** MIT License

---

*This project is a labor of love by fans, for fans. We respect the rights of copyright holders and will comply with legitimate requests.*
