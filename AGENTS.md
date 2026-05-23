# COMI Upscaled — Handoff Document

AI agent: read this at session start to get context.

## Project Status
All 38,689 visual assets extracted. Strategy shifted from "reimport into game
files" (blocked by coordinate patching) to **ScummVM HD fork**: modify the
SCUMM V8 engine to load 4x replacement textures externally via a manifest,
scaling coordinates at runtime. See `PLAN.md` for the full plan.

## System Constraints
- **OS:** Windows 10, Git Bash / MSYS shell (POSIX syntax)
- **GPU:** Intel UHD Graphics (laptop), Vulkan-capable
- **Working dir:** `Z:\Projekte\COMI-Upscaled\` (NAS, slow for bulk ops)
- **NUTcracker binary:** `nutcracker-Windows_X64/nutcracker.exe`
- **NUTcracker Python src:** `nutcracker/src/` (for AKOS decoding)
- **System Python:** `C:\Users\go75bel\AppData\Local\Programs\Python\Python313\python.exe`
- **Hermes venv:** no pip — use system Python with PYTHONPATH
- **RealESRGAN:** `tools/realesrgan-ncnn-vulkan-v0.2.0-windows/` (with models)
- **ScummVM binary:** `ScummVM/scummvm.exe` (stock, for comparison)

## Documentation Index

| File | What it contains |
|------|-----------------|
| `PLAN.md` | **Main plan** — HD fork strategy, phases, milestones |
| `README.md` | Project overview, structure, quick-start |
| `INDEX.md` | Legacy file index |
| `PATH_A_ANALYSIS.md` | Binary format analysis (for reference) |
| `RESEARCH.md` | Research on HD solutions, forums, people |
| `docs/FORK_PLAN.md` | Detailed ScummVM fork technical plan |
| `docs/HD_MANIFEST_SPEC.md` | hd_manifest.json format spec |
| `docs/BUILD.md` | Build instructions |
| `scripts/export_all.sh` | Automated export script |
| `scripts/hd_manifest_gen.py` | Manifest generator |
| `hd_config/batch_upscale.sh` | Batch RealESRGAN upscale |

## HD Pipeline
1. Batch upscale: `bash hd_config/batch_upscale.sh` (uses RealESRGAN anime model)
2. Generate manifest: `python scripts/hd_manifest_gen.py`
3. Build the fork: see `docs/BUILD.md`
4. Place HD assets in `ScummVM/monkey3/hd/`
5. Run fork: point at `ScummVM/monkey3/`

## Key References
- **Happy-Ferret** (Mark Bauermeister) — has working v6 ScummVM HD fork,
  patreon.com/HappyFerret, plans to open-source eventually
- **Laserschwert** — MixnMojo veteran, did early ESRGAN upscales (2020)
- **haywirephoenix** — MMUCS creator (Godot SCUMM V8 viewer)
- **Ubertrout** — Topaz Video upscale of cutscenes, archive.org/details/COMI_4k

## Extracted Assets (38,689 PNGs)
| Category | Count | Location |
|----------|-------|----------|
| Backgrounds | 40 | `CMI UPSCALED/extracted/COMI/IMAGES/backgrounds/` |
| Objects | 600 | `CMI UPSCALED/extracted/COMI/IMAGES/objects/` |
| Object layers | 234 | `CMI UPSCALED/extracted/COMI/IMAGES/objects_layers/` |
| Cutscene frames | 12,506 | `CMI UPSCALED/extracted/COMI/cutscenes/*/` |
| Fonts | 5 | `CMI UPSCALED/extracted/COMI/fonts/*/chars.png` |
| Costumes | 25,304 | `CMI UPSCALED/extracted/COMI/costumes/` |

## Critical Gotchas
1. **sputm room decode has NO --target flag** — CWD dependent
2. **AKOS costumes** use Python decoder, not binary
3. **NAS (Z:) is slow** — bulk ops on 25K+ files may time out
4. **Shell is Git Bash** — POSIX syntax, NOT PowerShell
5. **ScummVM fork approach** replaces old reimport plan — coordinate patching
   is done at runtime in C++, not in asset files
6. **Hermes venv has no pip** — use system Python instead
