# COMI-Upscaled v0.0.3 — 4x AI Upscaled HD Remaster

> **The Curse of Monkey Island** (LucasArts, 2000) — A modified **ScummVM** fork that renders COMI in 4x HD with AI-upscaled textures.

## 📦 What's Included

| Component | Size | Details |
|-----------|------|---------|
| **scummvm** (Linux Binary) | 25 MB | Modified ScummVM with HD overlay engine |
| **scummvm.exe** (Windows Binary) | 85 MB | Same build for Windows (MinGW/Clang) |
| **hd/** | ~9 GB | 4x upscaled HD textures (costumes, objects, fonts, backgrounds, videos) |
| **scummvm.ini** | — | Preconfigured for COMI |

**Total: ~9 GB** (without game data)

## ❌ What You Need To Provide

### The Game "Curse of Monkey Island" (COMI)

The original game files (`COMI.LA0`, `COMI.LA1`, `COMI.LA2`, `RESOURCE/`) are **not included**. You need a legal copy:

| Source | Link | Price |
|--------|------|:-----:|
| **Steam** | https://store.steampowered.com/app/730820/ | ~€5 |
| **GOG** | https://www.gog.com/en/game/the_curse_of_monkey_island | ~€5, DRM-free |

### 2. 4K Cutscenes (optional)

For 4K cutscenes (additional ~6 GB):
📥 https://archive.org/details/COMI_4k

Extract into `hd/videos/`. Without these, cutscenes play in original SD.

## 🚀 Installation

### Linux
```bash
# 1. Extract build ZIP
unzip comi_hd_build_0.0.3.zip -d comi_hd_v0.0.3/
# 2. Extract all 6 HD asset parts into the same directory
for f in hd_assets_0.0.3_part*.zip; do unzip "$f" -d comi_hd_v0.0.3/; done
cd comi_hd_v0.0.3

# 3. Copy your COMI game data into game/ subdirectory

# 4. Make binaries executable
chmod +x scummvm
./start_comi_hd.sh
```

### Windows
```bat
:: 1. Extract comi_hd_build_0.0.3.zip → comi_hd_v0.0.3/
:: 2. Extract all 6 hd_assets_0.0.3_part*.zip → comi_hd_v0.0.3/ (same directory)
:: 3. Copy COMI game data into game/ subdirectory
:: 4. Run start_comi_hd.bat
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| `F5` | Menu (Save/Load) |
| `Ctrl` + `F5` | ScummVM Menu |
| `Ctrl` + `d` | Debug Console |
| `Alt` + `Enter` | Toggle Fullscreen |
| `Esc` | Skip/Back |
| Mouse | Classic Point-and-Click |

## ⚙️ Configuration

Key options in `scummvm.ini` under `[comi]`:

| Option | Default | Description |
|--------|---------|-------------|
| `hd_path` | `./hd` | Path to HD textures |
| `hd_enabled` | `true` | HD overlay on/off |
| `hd_trace` | `false` | Debug output (only for troubleshooting) |

## 🔧 Technical Details

- **Engine:** Modified ScummVM (git 2026-02-01 + HD patches)
- **Upscaling:** RealESRGAN x4plus-anime (AMD RX 5700 XT)
- **Extraction:** NUTcracker (AKOS/costume decoding with Room Palette)
- **HD Costumes:** 25,302 frames across 473 costumes
- **HD Objects:** 1,365 (foreground) + 633 (layers) across all rooms
- **HD Fonts:** 5 fonts
- **HD Backgrounds:** All rooms (CPU pre-rendered with same model)

## 📋 System Requirements

| | Minimum | Recommended |
|---|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 2 GB | 4 GB |
| **GPU** | OpenGL 3.3+ | OpenGL 4.0+ (software rendering via llvmpipe possible) |
| **Storage** | 5 GB free | 12 GB (with 4K videos) |
| **OS** | Linux (x86_64) / Windows 10+ | |

## 📜 License

- **ScummVM:** GPLv2 — https://www.scummvm.org/
- **Game Data:** © LucasArts / Disney — not included

## 🙏 Acknowledgments

| Person/Project | For | Link |
|----------------|-----|:----:|
| **ScummVM Team** | The engine that makes this possible | [scummvm.org](https://www.scummvm.org/) |
| **NUTcracker (BLooperZ / pycd02)** | Asset extraction toolkit (AKOS decoder) | [GitHub](https://github.com/BLooperZ/nutcracker) |
| **RealESRGAN (xinntao)** | AI upscaling model (x4plus_anime_6B) | [GitHub](https://github.com/xinntao/Real-ESRGAN) |
| **MMUCS (haywirephoenix)** | Godot-powered SCUMM V8 content explorer | [GitHub](https://github.com/haywirephoenix/MMUCS) |
| **Happy-Ferret (Mark Bauermeister)** | Pioneering ScummVM v6 HD fork with external textures | [Patreon](https://patreon.com/HappyFerret) |
| **Laserschwert** | Early ESRGAN upscales (2020) | MixnMojo |
| **ubertrout** | 4K Topaz Video upscale of all COMI cutscenes | [Archive](https://archive.org/details/COMI_4k) |

### Additional Contributors
- **haywirephoenix** — Requested and tested AKOS support in NUTcracker, created ScummRev (AKOS viewer)
- Various SCUMM modding community members whose tools and research made this possible

## ⚖️ Legal

This project is provided for **educational and archival purposes only**.

### What this IS:
- ✅ A modified ScummVM (GPL v2) that loads external HD textures
- ✅ AI-upscaled textures — a transformative process producing new high-resolution image data
- ✅ Configuration files and launcher scripts

### What this does NOT distribute:
- ❌ No original game code from "The Curse of Monkey Island" (© LucasArts / Disney)
- ❌ No original game assets (COMI.LA0, LA1, LA2, or original room data)
- ❌ No ROMs, ISOs, or disk images

### License
- **ScummVM fork:** GPL v2 — https://www.scummvm.org/
- **Documentation:** MIT License

---

*COMI-Upscaled — A fan project. Not affiliated with LucasArts, Disney, or ScummVM.*
