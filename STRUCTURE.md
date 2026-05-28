# Project Structure & Architecture

## One Repo — Full Fork Source

**`harrytyp/comiupscale`** on GitHub contains the full ScummVM fork source
(in `scummvm/`) with pre-configured build config. Clone, build, run — no
patch step needed.

```
comiupscale/
├── scummvm/                    ← FULL fork source (incl. pre-configured config)
│   ├── engines/scumm/
│   │   ├── hd_*.cpp/.h        ← HD managers (assets, objects, costumes, fonts, video)
│   │   ├── gfx.cpp             ← HD composite rendering
│   │   ├── scumm.cpp/scumm.h   ← Manager init/cleanup, state
│   │   ├── charset.cpp         ← Font recording hook
│   │   └── module.mk           ← Build system entries
│   ├── config.h                ← PRE-CONFIGURED — tracked in git
│   ├── config.mk               ← PRE-CONFIGURED — tracked in git
│   └── ...                     ← Full ScummVM source tree
├── patches/                    ← HD patches (for reference, can regenerate)
├── scripts/                    ← Pipeline (upscale, alpha, deploy, manifest)
├── hd_config/                  ← Batch upscale configs
├── hd_manifest.json            ← Object/costume/font manifest
├── docs/                       ← FORK_PLAN, BUILD, HD_MANIFEST_SPEC
├── setup.py + comi_upscaled/   ← Setup wizard
├── monkey3/                    ← Game data + HD deploy target (on NAS: Z:\...\ScummVM\monkey3)
├── PLAN.md, STATUS.md, README.md, AGENTS.md, STRUCTURE.md
```

### What's Tracked in Git

| What | Why |
|------|-----|
| `scummvm/` | Full fork source — clone, build, run |
| `scummvm/config.h` + `scummvm/config.mk` | Pre-configured so no workstation re-runs `./configure` |
| `patches/` | HD patches (kept for reference, can extract at any time) |
| `scripts/`, `docs/`, `hd_config/` | Pipeline, docs, configs |
| `hd_manifest.json` | All HD assets declaration |
| `setup.py` + `comi_upscaled/` | Setup wizard |
| `PLAN.md`, `STATUS.md`, `README.md`, `AGENTS.md` | Project docs |

### Per-Workstation Build

```bash
# 1. Install MSYS2 (one per machine)
#    https://www.msys2.org/
#    pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-make ...

# 2. Clone the repo
git clone git@github.com:harrytyp/comiupscale.git
cd comiupscale/scummvm

# 3. Build (no ./configure needed — config is tracked)
mingw32-make -j12

# 4. Run
./scummvm.exe --path=../monkey3
```

### Regenerating Patches (if needed)

```bash
cd scummvm
# Compare against upstream ScummVM tag
git diff v2.9.0 -- engines/scumm/hd_*.cpp engines/scumm/hd_*.h \
  engines/scumm/gfx.cpp engines/scumm/scumm.cpp engines/scumm/scumm.h \
  engines/scumm/charset.cpp engines/scumm/module.mk > ../patches/scumm-hd.patch
```
