# Project Structure & Architecture

## One Repo — Full Fork Source

**`harrytyp/comiupscale`** on GitHub contains the full ScummVM fork source
with pre-configured build config. Clone, build, run — no patch step needed.

```
comiupscale/
├── scummvm/                       ← All fork-related
│   ├── fork/                      ← ScummVM source tree with HD changes
│   │   ├── engines/scumm/hd_*.cpp/.h  ← HD managers
│   │   ├── engines/scumm/gfx.cpp      ← HD composite rendering
│   │   ├── engines/scumm/scumm.cpp/h  ← Manager init, state
│   │   ├── engines/scumm/charset.cpp  ← Font recording hook
│   │   ├── engines/scumm/module.mk    ← Build entries
│   │   ├── config.h                  ← PRE-CONFIGURED (tracked)
│   │   ├── config.mk                 ← PRE-CONFIGURED (tracked)
│   │   └── ...full ScummVM tree...
│   └── patches/                  ← HD patch files for reference
├── config/                        ← Configuration (tracked)
│   ├── hd_manifest.json           ← HD asset catalog
│   ├── object_map.json            ← DOBJ object→filename mapping
│   └── upscale/                   ← Batch upscale scripts
├── docs/                          ← All documentation
├── scripts/                       ← Pipeline scripts
├── setup_wizard/                  ← MI3-themed setup wizard (Python package)
├── setup.py                       ← Wizard entry point
├── setup.sh                       ← Quick-start script
├── tests/                         ← Test files
├── tools/                         ← Third-party tools
│   ├── nutcracker/                ← Export tool (Python source)
│   ├── nutcracker-Windows_X64/    ← Export tool (Windows binary)
│   └── realesrgan-ncnn-vulkan-*  ← AI upscaler
├── assets/                        ← User-generated (untracked, gitignored)
│   ├── extracted/                 ← Original 640×480 PNGs
│   └── upscaled/                  ← 4K upscaled PNGs (backgrounds, objects,
│                                      costumes, fonts, cutscenes)
├── game/                          ← Game runtime data (untracked, gitignored)
│   ├── COMI.LA0/1/2              ← Game archives
│   ├── RESOURCE/                  ← Original SAN cutscenes, NUT fonts, BUN audio
│   └── hd/                       ← HD deploy target (generated)
├── dumps/                         ← Raw COMI resource dumps (untracked)
├── README.md
├── requirements.txt               ← Python deps (numpy, pillow, typer)
└── .gitignore
```

### What's Tracked in Git

| Path | Why |
|------|-----|
| `scummvm/fork/` | Full ScummVM source + our HD engine changes |
| `scummvm/fork/config.h` + `config.mk` | Pre-configured for zero-config build |
| `scummvm/patches/` | HD patches kept for reference |
| `config/` | HD manifest + object map + upscale configs |
| `scripts/` | Pipeline (upscale, alpha fixup, deploy, object map) |
| `docs/` | All project documentation |
| `setup_wizard/` + `setup.py` | MI3-themed setup wizard |
| `setup.sh` | Quick-start entry point |
| `requirements.txt` | Python dependencies (numpy, pillow, typer) |
| `tests/` | Test files |
| `tools/` | Third-party tool wrappers |
| `.gitignore` | Ignore user-generated content |

### What's Untracked (user generates from their own game copy)

| Path | Contents | How to generate |
|------|----------|-----------------|
| `assets/extracted/` | Original 640×480 PNGs | `nutcracker sputm room decode` |
| `assets/upscaled/` | 4K upscaled versions | `realesrgan-ncnn-vulkan` |
| `game/` | Game data + HD deploy | Copy from GOG/Steam/disc |
| `dumps/` | Raw resource dumps | `nutcracker rpdump` |

### Per-Workstation Build

```bash
# 1. Install MSYS2 (one per machine)
#    https://www.msys2.org/
#    pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-make ...

# 2. Clone the repo
git clone git@github.com:harrytyp/comiupscale.git
cd comiupscale/scummvm/fork

# 3. Build (no ./configure needed — config is tracked)
mingw32-make -j12

# 4. Run (point at game directory)
./scummvm.exe --path=../../game
```

### Regenerating Patches (if needed)

```bash
cd scummvm/fork
git diff v2.9.0 -- engines/scumm/hd_*.cpp engines/scumm/hd_*.h \
  engines/scumm/gfx.cpp engines/scumm/scumm.cpp engines/scumm/scumm.h \
  engines/scumm/charset.cpp engines/scumm/module.mk > ../patches/scumm-hd.patch
```
