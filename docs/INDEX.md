# COMI Upscaled — Project Documentation

## Overview

This project extracts all visual assets from **"The Curse of Monkey Island"**
(LucasArts, 2000, SCUMM V8), upscales them 4x using AI (RealESRGAN-NCNN-Vulkan),
and reimports them into the game for play in ScummVM.

**Project root:** `Z:\Projekte\COMI-Upscaled\` (NAS)

---

## Documentation Index

| File | Description |
|------|-------------|
| `README.md` | Complete export process with exact commands |
| `AGENTS.md` | AI agent handoff document (session context) |
| `PATH_A_ANALYSIS.md` | Technical analysis of HD reimport requirements |
| `scripts/export_all.sh` | Automated full-export script |
| `requirements.txt` | Python dependencies for AKOS decoding |

---

## Extracted Asset Summary

| Category | PNGs | Location |
|----------|------|----------|
| Backgrounds | 40 | `extracted/COMI/IMAGES/backgrounds/` |
| Objects | 600 | `extracted/COMI/IMAGES/objects/` |
| Object layers | 234 | `extracted/COMI/IMAGES/objects_layers/` |
| Cutscene frames | 12,506 | `extracted/COMI/cutscenes/*/` (15 dirs) |
| Fonts | 5 | `extracted/COMI/fonts/*/chars.png` |
| Costumes/sprites | 25,304 | `extracted/COMI/costumes/` |
| **TOTAL** | **38,689** | |

---

## Project Structure

```
Z:\Projekte\COMI-Upscaled\
├── AGENTS.md                    # AI handoff doc (read first)
├── README.md                    # Export documentation
├── PATH_A_ANALYSIS.md           # HD reimport technical analysis
├── requirements.txt             # Python deps (numpy, pillow, typer)
├── initial_prompt.txt           # Original project brief
├── next_steps.md                # Legacy step plan
├── session 2.txt                # Tool discovery history
│
├── scripts/
│   └── export_all.sh            # Automated export (chmod +x)
│
├── nutcracker/
│   ├── src/nutcracker/          # Python source (for AKOS decoding)
│   └── pyproject.toml           # Python package definition
│
├── nutcracker-Windows_X64/
│   └── nutcracker.exe           # Prebuilt Windows binary
│
├── scummvm-tools/               # ScummVM tool source (unused)
├── scummeditor/                  # ScummEditor C# source (unused)
│
├── ScummVM/monkey3/
│   ├── COMI.LA0, .LA1, .LA2    # Game resource archives
│   ├── COMI.LA1, COMI.LA2
│   └── RESOURCE/                # SAN cutscenes, NUT fonts, BUN audio
│
├── COMI/                         # Raw resource dump (sputm extract)
│   ├── LECF_0001/               # Rooms 1-38
│   ├── LECF_0002/               # Rooms 39-93
│   └── rpdump.xml
│
└── CMI UPSCALED/
    ├── extracted/COMI/
    │   ├── IMAGES/
    │   │   ├── backgrounds/     # 40 PNGs
    │   │   ├── objects/         # 600 PNGs
    │   │   └── objects_layers/  # 234 PNGs
    │   ├── cutscenes/            # 15 dirs, ~12,506 PNGs
    │   ├── fonts/                # 5 dirs, chars.png each
    │   └── costumes/             # 25,304 PNGs
    ├── upscaled/                 # Output dir (empty, for upscaled assets)
    │   ├── backgrounds/
    │   ├── objects/
    │   ├── cutscenes/
    │   ├── costumes/
    │   └── objects_layers/
    └── repackaged/               # Output dir (empty, for rebuilt game files)
```

---

## Key Tools

### NUTcracker Binary
- **Path:** `nutcracker-Windows_X64/nutcracker.exe`
- **Usage:** Backgrounds, objects, cutscenes, fonts
- **Commands:** `sputm room decode`, `smush decode`, `sputm room encode`, `sputm build`

### NUTcracker Python Source
- **Path:** `nutcracker/src/nutcracker/`
- **Usage:** AKOS costume decoding (not exposed via CLI)
- **Run:** `PYTHONPATH=nutcracker/src python -m nutcracker.sputm.costume.akos <LA0>`
- **Deps:** numpy, pillow, typer

### Python Setup
- System Python: `C:\Users\go75bel\AppData\Local\Programs\Python\Python313\python.exe`
- Hermes venv Python at `/c/Users/go75bel/AppData/Local/hermes/hermes-agent/venv/Scripts/python` (no pip — use system Python instead)

---

## Quick-Start (Full Export)

```bash
cd /z/Projekte/COMI-Upscaled
pip install -r requirements.txt
bash scripts/export_all.sh
```

---

## Critical Gotchas

1. **sputm room decode has NO --target flag** — output is always relative to CWD
2. **AKOS costumes NOT extracted by sputm room decode** — must use Python decoder
3. **NAS (Z:) is slow** — bulk file operations on 25K+ files may time out
4. **Shell is Git Bash** — POSIX syntax, NOT PowerShell
5. **4x upscale breaks walkbox/hotspot/script coords** — see PATH_A_ANALYSIS.md
