# COMI Upscaled — Project Documentation

## Overview

This project extracts all visual assets from **"The Curse of Monkey Island"**
(LucasArts, 2000, SCUMM V8), upscales them 4x using AI (RealESRGAN-NCNN-Vulkan),
and delivers them via a **modified ScummVM fork** with HD overlay support.

**Strategy:** Instead of patching original game data (the reimport approach which
breaks coordinate-based structures), we fork ScummVM's SCUMM engine to load 4x
replacement textures from an external `hd/` directory at runtime. See [PLAN.md](PLAN.md).

**Project root:** `Z:\Projekte\COMI-Upscaled\` (NAS)

---

## Documentation Index

| File | Description |
|------|-------------|
| `PLAN.md` | **Main plan** — ScummVM HD fork strategy, phases, milestones |
| `README.md` | This file — project overview and structure |
| `AGENTS.md` | AI agent handoff document (session context) |
| `PATH_A_ANALYSIS.md` | Technical analysis of HD reimport requirements |
| `RESEARCH.md` | Research on existing solutions, forums, techniques |
| `scripts/export_all.sh` | Automated full-export script |
| `requirements.txt` | Python dependencies for AKOS decoding |
| `docs/FORK_PLAN.md` | Detailed technical plan for ScummVM fork |
| `docs/HD_MANIFEST_SPEC.md` | hd_manifest.json format specification |
| `docs/BUILD.md` | Build instructions for the ScummVM fork |

---

## Extracted Asset Summary

| Category | PNGs | Location |
|----------|------|----------|
| Backgrounds | 40 | `CMI UPSCALED/extracted/COMI/IMAGES/backgrounds/` |
| Objects | 600 | `CMI UPSCALED/extracted/COMI/IMAGES/objects/` |
| Object layers | 234 | `CMI UPSCALED/extracted/COMI/IMAGES/objects_layers/` |
| Cutscene frames | 12,506 | `CMI UPSCALED/extracted/COMI/cutscenes/*/` (15 dirs) |
| Fonts | 5 | `CMI UPSCALED/extracted/COMI/fonts/*/chars.png` |
| Costumes/sprites | 25,304 | `CMI UPSCALED/extracted/COMI/costumes/` |
| **TOTAL** | **38,689** | |

---

## Project Structure

```
Z:\Projekte\COMI-Upscaled\
├── PLAN.md                       # ScummVM HD fork plan (READ FIRST)
├── README.md                     # This file
├── AGENTS.md                     # AI handoff doc
├── INDEX.md                      # Legacy file index
├── PATH_A_ANALYSIS.md            # HD reimport technical analysis
├── RESEARCH.md                   # Research findings
├── requirements.txt              # Python deps (numpy, pillow, typer)
│
├── docs/
│   ├── FORK_PLAN.md              # Detailed ScummVM fork tech plan
│   ├── HD_MANIFEST_SPEC.md       # hd_manifest.json format
│   └── BUILD.md                  # ScummVM fork build instructions
│
├── scripts/
│   ├── export_all.sh             # Automated export (chmod +x)
│   ├── demo_upscale.py           # Lanczos upscale demo
│   ├── demo_upscale_stage.py     # Stage room demo
│   └── hd_manifest_gen.py        # hd_manifest.json generator
│
├── hd_config/
│   └── batch_upscale.sh          # Batch RealESRGAN upscale script
│
├── nutcracker/
│   ├── src/nutcracker/           # Python source (for AKOS decoding)
│   └── pyproject.toml            # Python package definition
│
├── nutcracker-Windows_X64/
│   └── nutcracker.exe            # Prebuilt Windows binary
│
├── scummvm-fork/ -> /c/Users/go75bel/scummvm-fork  # ScummVM source (localhost clone)
│
├── ScummVM/
│   ├── scummvm.exe               # Stock ScummVM binary
│   ├── monkey3/
│   │   ├── COMI.LA0, .LA1, .LA2 # Game resource archives
│   │   └── RESOURCE/             # SAN cutscenes, NUT fonts, BUN audio
│   │   └── hd/                   # HD manifest + upscaled assets (future)
│   └── ...
│
├── scummvm-tools/                # ScummVM utilities (compress, etc.)
├── scummeditor/                   # ScummEditor C# source
│
├── COMI/                          # Raw resource dump
│   ├── LECF_0001/                # Rooms 1-38
│   ├── LECF_0002/                # Rooms 39-93
│   └── rpdump.xml
│
├── CMI UPSCALED/
│   ├── extracted/COMI/
│   │   ├── IMAGES/
│   │   │   ├── backgrounds/      # 40 PNGs (original)
│   │   │   ├── objects/          # 600 PNGs (original)
│   │   │   └── objects_layers/   # 234 PNGs (original)
│   │   ├── cutscenes/            # 15 dirs, ~12,506 frames
│   │   ├── fonts/                # 5 dirs
│   │   └── costumes/             # 25,304 frames
│   ├── upscaled/                 # HD output dir (4x AI-upscaled)
│   │   ├── backgrounds/
│   │   ├── objects/
│   │   ├── cutscenes/
│   │   ├── costumes/
│   │   └── objects_layers/
│   ├── hd/                       # HD manifest + assets for ScummVM fork
│   ├── demo/                     # Lanczos demo (room 0015)
│   ├── demo_stage/               # RealESRGAN demo (room 0019)
│   └── repackaged/               # Legacy reimport output (unused)
│
├── MMUCS/                        # Godot SCUMM V8 viewer
└── tools/
    └── realesrgan-ncnn-vulkan-v0.2.0-windows/
```

---

## Key Tools

### NUTcracker Binary
- **Path:** `nutcracker-Windows_X64/nutcracker.exe`
- **Usage:** Backgrounds, objects, cutscenes, fonts
- **Commands:** `sputm room decode`, `smush decode`, `sputm room encode`, `sputm build`

### NUTcracker Python Source
- **Path:** `nutcracker/src/nutcracker/`
- **Usage:** AKOS costume decoding
- **Run:** `PYTHONPATH=nutccker/src python -m nutcracker.sputm.costume.akos <LA0>`
- **Deps:** numpy, pillow, typer

### RealESRGAN-NCNN-Vulkan
- **Path:** `tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe`
- **Model:** `realesrgan-x4plus-anime` (best for COMI's hand-drawn cartoon style)
- **Usage:** `realesrgan-ncnn-vulkan.exe -i input.png -o output.png -m models/ -n realesrgan-x4plus-anime`

### Python Setup
- System Python: `C:\Users\go75bel\AppData\Local\Programs\Python\Python313\python.exe`
- Hermes venv: no pip — use system Python instead

---

## Quick-Start (HD Pipeline)

```bash
cd /z/Projekte/COMI-Upscaled

# 1. Batch upscale all 40 backgrounds
bash hd_config/batch_upscale.sh

# 2. Generate manifest
python scripts/hd_manifest_gen.py

# 3. Build ScummVM fork (see docs/BUILD.md)
cd scummvm-fork
./configure --backend=sdl
make -j$(nproc)

# 4. Run with HD assets
./scummvm.exe --path=/z/Projekte/COMI-Upscaled/ScummVM/monkey3
```

---

## Critical Gotchas

1. **sputm room decode has NO --target flag** — output always relative to CWD
2. **AKOS costumes** are NOT extracted by sputm — use Python decoder
3. **NAS (Z:) is slow** — bulk operations on 25K+ files may time out
4. **Shell is Git Bash** — POSIX syntax, NOT PowerShell
5. **ScummVM fork approach** replaces the old reimport plan — coordinate patching
   is handled at runtime in C++, not in the asset files
