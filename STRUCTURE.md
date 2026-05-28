# Project Structure & Architecture

## One Repo — Patches + Config

**`harrytyp/comiupscale`** on GitHub tracks our HD code as **patches** (small,
reviewable) plus **pre-configured build config** (so no workstation re-runs
`./configure`). The full fork source lives as a compressed tarball on NAS and
GitHub Releases.

```
comiupscale/
├── patches/                    ← All HD changes as patch files + new source files
│   ├── 0001-HD-Objects-....patch   ← HdObjectManager, compositing pipeline
│   ├── 0002-HD-Objects-v2-....patch   ← culling, alpha masks
│   ├── 0003-HD-Costume-....patch     ← Costume/Font managers, SMUSH fix
│   ├── 0004-HD-Costume-....patch     ← Source files for managers
│   ├── config.h                    ← PRE-CONFIGURED — tracked in git
│   ├── config.mk                   ← PRE-CONFIGURED — tracked in git
│   ├── hd_asset_manager.cpp/.h     ← New HD files (not in patch format)
│   ├── hd_video_player.cpp/.h      ← New HD files
│   ├── module.mk                   ← Modified build config
│   └── scumm-hd-fork.patch         ← Legacy patch (kept for reference)
├── scripts/                  ← Pipeline scripts
│   ├── add_costume_alpha.py
│   ├── add_object_alpha_v5.py/.v6.py
│   ├── deploy_hd.py
│   ├── setup_build_env.sh
│   ├── upscale_costumes.py
│   └── hd_manifest_gen.py
├── hd_config/                ← Batch upscale configs
│   └── upscale_remaining.sh
├── hd_manifest.json          ← Object/costume/font manifest
├── docs/
│   ├── FORK_PLAN.md
│   ├── BUILD.md
│   └── HD_MANIFEST_SPEC.md
├── setup.py                  ← Setup wizard entry point
├── comi_upscaled/            ← Setup wizard Python package
├── PLAN.md, STATUS.md, README.md, AGENTS.md, STRUCTURE.md
```

### What's Tracked in Git

| What | Why |
|------|-----|
| `patches/*.patch` | Our 4 HD commits as reviewable patches |
| `patches/config.h` + `patches/config.mk` | Pre-configured `./configure` output |
| `patches/hd_*.cpp/.h` | New source files (HD Asset/Video managers) |
| `patches/module.mk` | Build system changes |
| `scripts/`, `docs/`, `hd_config/` | Pipeline, docs, configs |
| `hd_manifest.json` | All HD assets declaration |
| `setup.py` + `comi_upscaled/` | Setup wizard |
| `PLAN.md`, `STATUS.md`, `README.md`, `AGENTS.md` | Project docs |

### What's on NAS Only (Z:\)

| Path | Contents |
|------|----------|
| `CMI UPSCALED/` | 38K+ extracted + upscaled PNGs |
| `ScummVM/monkey3/` | Game data + HD deploy target |
| `tools/` | RealESRGAN binaries |
| `nutcracker/`, `nutcracker-Windows_X64/` | Export tool |
| `scummvm-tools/`, `scummeditor/`, `MMUCS/` | Utilities |
| `COMI/` | Raw resource dumps |

### What's on NAS + GitHub Releases

| File | Purpose |
|------|---------|
| `scummvm-fork.tar.gz` | Full fork source with pre-configured config (builds on any machine) |

### Per-Workstation Build

```bash
# 1. Install MSYS2 (one per machine)
#    https://www.msys2.org/
#    pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-make ...

# 2. Clone the repo
git clone git@github.com:harrytyp/comiupscale.git
cd comiupscale

# 3. Download and extract the pre-configured fork source
#    (from GitHub Releases or NAS)
curl -L https://github.com/harrytyp/comiupscale/releases/download/v1.0/scummvm-fork.tar.gz
tar xzf scummvm-fork.tar.gz
cd scummvm

# 4. Build (no ./configure needed)
mingw32-make -j12

# 5. Run (mount Z:\ for assets)
./scummvm.exe --path=Z:/Projekte/COMI-Upscaled/ScummVM/monkey3
```

### Applying Patches to Fresh ScummVM Source

```bash
git clone --depth 1 https://github.com/scummvm/scummvm.git
cd scummvm
git am ../patches/0001-*.patch
git am ../patches/0002-*.patch
git am ../patches/0003-*.patch
git am ../patches/0004-*.patch
cp ../patches/hd_*.cpp ../patches/hd_*.h engines/scumm/
cp ../patches/config.h ../patches/config.mk .
```

### GitHub Releases

| Release Asset | Contents |
|---------------|----------|
| `scummvm-fork-v1.0.tar.gz` | Full source tarball with pre-configured config |
| `scummvm-hd-v1.0.exe` | Pre-built binary |
