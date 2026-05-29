# COMI Upscaled — Project Plan

## Goal
A playable 4x HD version of Curse of Monkey Island (SCUMM V8) via a
modified ScummVM fork that loads upscaled assets externally, without
patching original game files.

## Strategy
**Approach** (validated by Happy-Ferret's Open Remonkeyed fork):
Modify ScummVM's SCUMM engine to read HD replacement textures from
an external `hd/` directory via a manifest file, instead of reimporting
into the game's binary format. The engine renders at 4x native resolution,
scaling coordinates at runtime. Original game data stays untouched.

### Why not reimport?
- SCRP bytecodes push coordinates on a stack — binary patching 93 rooms
  of V8 bytecode requires a full disassembler/rewriter
- RMHD/BOXD/IMHD coordinate patching is possible but pointless if scripts
  don't match
- The reimport pipeline exists (NUTcracker room encode + build) but doesn't
  scale anything — it encodes whatever you give it at original dimensions

### Why not MMUCS?
- MMUCS is a viewer, not a game engine (no SCUMM Runner yet)
- This produces a real ScummVM fork — works with the full game

## Asset Inventory (extracted, 38,689 PNGs)
- Backgrounds: 40 (35 standard 640x480, 5 panoramic up to 2096x480)
- Objects: 600
- Object layers: 234
- Costumes (AKOS): 25,304 frames across 457 files
- Cutscenes (SAN/SMUSH): 12,506 frames across 15 scenes
- Fonts: 5

## Phases

### Phase 1: Development Environment
- Clone ScummVM source
- Set up MSYS2/MinGW build toolchain on Windows
- Build stock ScummVM to verify
- [docs/BUILD.md](docs/BUILD.md)

### Phase 2: HD Manifest System
- Define `hd_manifest.json` format
- Create generator script from extracted assets
- See [docs/HD_MANIFEST_SPEC.md](docs/HD_MANIFEST_SPEC.md)

### Phase 3: ScummVM Engine Modifications
Core changes in `engines/scumm/`:
- `HDAssetManager` — loads HD textures, falls back to originals
- `room.cpp` — intercept room background load, swap with 4x HD PNG
- Internal resolution: 640x480 → 2560x1920 (4x)
- Coordinate scaling: actor positions, walkboxes, object coords all *4
- Render scaling: costume drawing, screen shake, effects
- See [docs/FORK_PLAN.md](docs/FORK_PLAN.md)

### Phase 4: Asset Pipeline
- Batch upscale 40 backgrounds with RealESRGAN-x4plus-anime
- Generate manifest
- Test: load COMI in the fork, verify HD backgrounds render
- Validate scaling: actor placement, walkboxes, click detection

### Phase 5: Polish
- Object HD sprites (600 objects)
- Costume scaling (bottomless work — Happy-Ferret calls it "MASSIVE undertaking")
- UI/element scaling
- Cutscene rendering at HD (SMUSH video)

## Project Structure
```
/z/Projekte/COMI-Upscaled/
├── PLAN.md                          # This file
├── README.md                        # Project overview
├── INDEX.md                         # File index
├── AGENTS.md                        # Hermes handoff
├── RESEARCH.md                      # Research findings
├── PATH_A_ANALYSIS.md               # Binary format analysis
├── requirements.txt                 # Python deps
├── patches/                       # ScummVM HD fork patches (reproducible build)
│   ├── scumm-hd-fork.patch        # Git patch for 5 modified engine files
│   ├── hd_asset_manager.h         # New HD asset manager header
│   └── hd_asset_manager.cpp       # New HD asset manager implementation
│
├── scripts/                         # Utility scripts
│   ├── export_all.sh                # Full asset export
│   ├── demo_upscale.py              # Lanczos demo
│   └── hd_manifest_gen.py           # Manifest generator
├── docs/                            # Documentation
│   ├── FORK_PLAN.md                 # Detailed fork plan
│   ├── HD_MANIFEST_SPEC.md          # Manifest format spec
│   └── BUILD.md                     # Build instructions
├── hd_config/                       # HD asset configs
│   └── batch_upscale.sh             # Batch upscale script
├── ScummVM/                         # Game install (target binary)
│   ├── scummvm.exe
│   └── monkey3/
├── scummvm-fork/ -> /c/Users/go75bel/scummvm-fork  # ScummVM source (localhost)
├── CMI UPSCALED/                    # Extracted + upscaled assets
│   ├── extracted/                   # Original PNGs (38,689 files)
│   ├── upscaled/                    # AI-upscaled 4x PNGs
│   ├── hd/                          # HD manifest + assets for ScummVM fork
│   └── demo/                        # Demo files
├── nutcracker/                      # NUTcracker source
├── tools/                           # External tools
│   └── realesrgan-ncnn-vulkan-v0.2.0-windows/
├── MMUCS/                           # Godot SCUMM V8 viewer
└── scummvm-tools/                   # ScummVM utilities
```

## Key Decisions
- **4x scale** (2560x1920) — clean integer multiple of 640x480
- **Anime model** (realesrgan-x4plus-anime) — best for COMI's hand-drawn art
- **External HD assets** — no game file patching, `hd/` directory next to game data
- **C++ ScummVM fork** — the only practical path for native HD gameplay

## Reference People
- **Happy-Ferret** (Mark Bauermeister) — has working ScummVM fork with HD
  backgrounds for SCUMM v6. Patreon: patreon.com/HappyFerret
- **Laserschwert** — did early ESRGAN upscales of COMI assets (2020)
- **haywirephoenix** — MMUCS creator, SCUMM V8 modding
