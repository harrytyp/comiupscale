# COMI-HD Repository Structure

> Last updated: 2026-07-01
>
> This document describes the current (as-is) directory layout and the
> proposed target layout after minimal, safe reorganization focused on
> the COMI-HD-specific parts of the repo. The `scummvm/fork/` subtree
> (a full ScummVM source tree) is **not** restructured — only its
> `patches/` companion may be organized.

---

## 1. Current Directory Tree

Only the root and first‑level subdirectories are shown. `scummvm/fork/`
is collapsed to one node — its internals are not enumerated. Untracked /
gitignored items are marked with `†`.

```
comi-hd-repo/
├── .gitignore
├── README.md
├── requirements.txt              # numpy, pillow, typer
├── setup.py                      # Wizard entry point
├── setup.sh                      # Quick-start script
│
├── config/                       # Runtime configuration
│   ├── hd_manifest.json          # HD asset catalog (tracked)
│   ├── object_map.json           # DOBJ → filename mapping (tracked)
│   ├── paths.yaml                # User path config (tracked)
│   └── upscale/                  # Batch upscale shell scripts
│       ├── batch_upscale.sh
│       ├── upscale_objects.sh
│       └── upscale_remaining.sh
│
├── docs/                         # All documentation (flat)
│   ├── AGENTS.md
│   ├── BUILD.md
│   ├── FORK_PLAN.md
│   ├── HD_COSTUME_PLAN.md
│   ├── HD_MANIFEST_SPEC.md
│   ├── HD_QUALITY_ANALYSIS.md
│   ├── INDEX.md
│   ├── PATH_A_ANALYSIS.md
│   ├── PLAN.md
│   ├── PLAN_QUALITY_FIX.md
│   ├── RESEARCH.md
│   ├── STATUS.md
│   ├── STRUCTURE.md
│   ├── TECHNICAL_REPORT.md
│   └── screenshots/              # Before/after images
│       ├── hd_background_room9.png
│       └── room9.png
│
├── dumps/                        † Extracted game data (untracked)
│
├── hd_costumes_fixed/            † Symlink → /opt/.../hd_costumes_fixed/
│
├── comi-hd-final                 † Symlink → /opt/.../comi-hd-final
│
├── release/                      † Build release artifacts (untracked)
│
├── scummvm/
│   ├── fork/                     *** FULL SCUMMVM SOURCE — DO NOT REORG ***
│   │   └── ... (engine, backends, devtools, build artifacts, etc.)
│   └── patches/                  (currently empty / not present in workspace)
│
├── scripts/                      # Pipeline scripts (flat, 37 files)
│   ├── add_costume_alpha.py
│   ├── add_object_alpha.py          ← pre-v6 original
│   ├── add_object_alpha_v2.py
│   ├── add_object_alpha_v3.py
│   ├── add_object_alpha_v4.py
│   ├── add_object_alpha_v5.py
│   ├── add_object_alpha_v6.py       ← current version
│   ├── analyze_dump.py
│   ├── analyze_framebuffer.py
│   ├── analyze_room9.py             ← one-off analysis
│   ├── apply_chaikin_alpha.py
│   ├── batch_upscale_costumes.py
│   ├── build_object_map.py
│   ├── check_hd_dumps.py
│   ├── check_setup.py
│   ├── debug_loop.sh
│   ├── demo_upscale.py              ← experimental
│   ├── demo_upscale_stage.py        ← experimental
│   ├── deploy_hd.py
│   ├── diagnose.py
│   ├── export_all.sh
│   ├── extract_all_raw.py
│   ├── extract_costumes_fixed.py
│   ├── full_pipeline.sh
│   ├── generate_test_pattern.py
│   ├── hd_diagnose.py
│   ├── hd_manifest_gen.py
│   ├── paths.py
│   ├── sd_vs_hd_diff.py
│   ├── setup_build_env.sh
│   ├── test_hd.sh
│   ├── upscale_costumes.py
│   ├── upscale_esrgan.py            ← current upscaler
│   ├── upscale_room9.py             ← superseded by upscale_esrgan
│   ├── verify_room9.py              ← one-off verification
│   └── vision_qa.py
│
├── setup_wizard/                 # Python package for user setup
│   ├── __init__.py
│   ├── config.py
│   ├── config.yaml
│   ├── pipeline.py
│   ├── ui.py
│   └── steps/
│       └── __init__.py
│
└── tests/                        # Test files
    ├── analyze_dump.py            # (duplicate of scripts/analyze_dump.py)
    ├── test_hd_composite.cpp
    ├── test_pattern_2560x1920.png
    ├── test_room.cpp
    ├── test_room_debug.cpp
    └── test_room_sdl.cpp
```

> **Legend:** `†` = untracked / gitignored (user‑generated or symlink).

---

## 2. Target Directory Tree (Proposed)

Changes are **minimal and safe**: no files are deleted, no `scummvm/fork/`
paths are touched. The only structural additions are two `/archive/`
directories under `docs/` and `scripts/`.

```
comi-hd-repo/
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py
├── setup.sh
│
├── config/                       ◄── NO CHANGE
│   ├── hd_manifest.json
│   ├── object_map.json
│   ├── paths.yaml
│   └── upscale/
│       ├── batch_upscale.sh
│       ├── upscale_objects.sh
│       └── upscale_remaining.sh
│
├── docs/                         ◄── ACTIVE docs only at root
│   ├── BUILD.md                  │   active — still relevant
│   ├── STRUCTURE.md              │   active — this document
│   ├── TECHNICAL_REPORT.md       │   active — technical overview
│   ├── REPO_STRUCTURE.md         │   NEW — this file
│   ├── screenshots/              │   active — before/after images
│   │   ├── hd_background_room9.png
│   │   └── room9.png
│   └── archive/                  ── historical reference docs
│       ├── AGENTS.md
│       ├── FORK_PLAN.md
│       ├── HD_COSTUME_PLAN.md
│       ├── HD_MANIFEST_SPEC.md
│       ├── HD_QUALITY_ANALYSIS.md
│       ├── INDEX.md
│       ├── PATH_A_ANALYSIS.md
│       ├── PLAN.md
│       ├── PLAN_QUALITY_FIX.md
│       ├── RESEARCH.md
│       └── STATUS.md
│
├── dumps/                        ◄── NO CHANGE (untracked)
├── hd_costumes_fixed/            ◄── NO CHANGE (symlink)
├── comi-hd-final                 ◄── NO CHANGE (symlink)
├── release/                      ◄── NO CHANGE (untracked)
│
├── scummvm/                      ◄── NO CHANGE (fork kept intact)
│   ├── fork/                     *** FULL SCUMMVM SOURCE — INTACT ***
│   └── patches/                  (if present, no change)
│
├── scripts/                      ◄── ACTIVE scripts only at root
│   ├── add_costume_alpha.py
│   ├── add_object_alpha_v6.py        ← the current version
│   ├── analyze_dump.py               ← keep; referenced by workflows
│   ├── analyze_framebuffer.py
│   ├── apply_chaikin_alpha.py
│   ├── batch_upscale_costumes.py
│   ├── build_object_map.py
│   ├── check_hd_dumps.py
│   ├── check_setup.py
│   ├── debug_loop.sh
│   ├── deploy_hd.py
│   ├── diagnose.py
│   ├── export_all.sh
│   ├── extract_all_raw.py
│   ├── extract_costumes_fixed.py
│   ├── full_pipeline.sh
│   ├── generate_test_pattern.py
│   ├── hd_diagnose.py
│   ├── hd_manifest_gen.py
│   ├── paths.py
│   ├── sd_vs_hd_diff.py
│   ├── setup_build_env.sh
│   ├── test_hd.sh
│   ├── upscale_costumes.py
│   ├── upscale_esrgan.py             ← the current upscaler
│   └── vision_qa.py
│   └── archive/                  ── stale / superseded / experimental
│       ├── add_object_alpha.py        superseded by v6
│       ├── add_object_alpha_v2.py     alpha iteration
│       ├── add_object_alpha_v3.py     alpha iteration
│       ├── add_object_alpha_v4.py     alpha iteration
│       ├── add_object_alpha_v5.py     alpha iteration
│       ├── analyze_room9.py           one-off early analysis
│       ├── demo_upscale.py            experimental, not used
│       ├── demo_upscale_stage.py      experimental, not used
│       ├── upscale_room9.py           superseded by upscale_esrgan.py
│       └── verify_room9.py            one-off verification
│
├── setup_wizard/                 ◄── NO CHANGE
│   ├── __init__.py
│   ├── config.py
│   ├── config.yaml
│   ├── pipeline.py
│   ├── ui.py
│   └── steps/
│       └── __init__.py
│
└── tests/                        ◄── NO CHANGE (keep as-is)
    ├── analyze_dump.py            (duplicate — consider dedup later)
    ├── test_hd_composite.cpp
    ├── test_pattern_2560x1920.png
    ├── test_room.cpp
    ├── test_room_debug.cpp
    └── test_room_sdl.cpp
```

---

## 3. Rationale for Each Change

### 3.1 `docs/ → docs/archive/` — Separate historical from active docs

| Change | Rationale |
|--------|-----------|
| **Move 11 historical .md files → `docs/archive/`** | The `docs/` folder had 14 markdown files in a flat list, mixing one‑off planning docs (PLAN.md, STATUS.md, RESEARCH.md) with evergreen reference (BUILD.md, STRUCTURE.md, TECHNICAL_REPORT.md). Keeping only the 3 active docs at root makes navigation much faster. The archived docs are still perfectly accessible at `docs/archive/` — nothing is deleted. |
| **No change to `docs/screenshots/`** | Screenshots are still active reference images; they stay at `docs/screenshots/`. |

**Which docs go to `docs/archive/` (and why):**

| File | Why it's historical |
|------|-------------------|
| `AGENTS.md` | Handoff doc for AI agent context; session‑specific, not user‑facing |
| `FORK_PLAN.md` | Early planning for the ScummVM fork approach; superseded by actual implementation |
| `HD_COSTUME_PLAN.md` | Planning doc for costume pipeline; pipeline is already built |
| `HD_MANIFEST_SPEC.md` | Format spec — useful reference but doesn't need to be in the active root |
| `HD_QUALITY_ANALYSIS.md` | One‑time quality assessment of upscale results |
| `INDEX.md` | Legacy file index; superseded by STRUCTURE.md / REPO_STRUCTURE.md |
| `PATH_A_ANALYSIS.md` | Binary format analysis done during research phase |
| `PLAN.md` | Old master plan; project has moved beyond the planning phase |
| `PLAN_QUALITY_FIX.md` | Specific quality‑fix plan; already actioned or superseded |
| `RESEARCH.md` | Research notes from early exploration; reference only |
| `STATUS.md` | Status snapshot at a point in time; no longer updated |

### 3.2 `scripts/ → scripts/archive/` — Consolidate script versions

| Change | Rationale |
|--------|-----------|
| **Move 10 stale/superseded scripts → `scripts/archive/`** | The `scripts/` folder grew organically with multiple alpha versions of the same functionality (add_object_alpha.py through v6, three upscale variants, two demo scripts). Keeping only the **current** version of each pipeline step in the active root reduces cognitive load and prevents accidentally running an outdated script. |
| **No change to shell pipeline scripts** | `full_pipeline.sh`, `export_all.sh`, `debug_loop.sh`, `test_hd.sh`, `setup_build_env.sh` remain active. |

**Which scripts go to `scripts/archive/` (and why):**

| Script | Why it's archived |
|--------|------------------|
| `add_object_alpha.py` | Pre‑v6 original; superseded by `add_object_alpha_v6.py` |
| `add_object_alpha_v2.py` | Iteration; superseded by v6 |
| `add_object_alpha_v3.py` | Iteration; superseded by v6 |
| `add_object_alpha_v4.py` | Iteration; superseded by v6 |
| `add_object_alpha_v5.py` | Iteration; superseded by v6 |
| `analyze_room9.py` | One‑off early analysis of Room 9 only |
| `demo_upscale.py` | Experimental demo, not part of pipeline |
| `demo_upscale_stage.py` | Experimental demo, not part of pipeline |
| `upscale_room9.py` | Early room‑specific upscaler; superseded by `upscale_esrgan.py` |
| `verify_room9.py` | One‑off verification, not part of pipeline |

### 3.3 Things we do **NOT** change

| Area | Why left untouched |
|------|-------------------|
| **`scummvm/fork/`** | This is a full ScummVM source tree with pre‑configured build files. Moving or restructuring it would break build paths, git history, and the release workflow. |
| **`scummvm/patches/`** | If this directory exists it holds reference patches; it's already in the right place next to `fork/`. |
| **`config/`** | Already well‑organized with runtime configs at root and upscale scripts in a subdirectory. No changes needed. |
| **`setup_wizard/`** | Clean Python package structure. No changes needed. |
| **`tests/`** | Small (5 files), well‑named. The duplicate `analyze_dump.py` between `scripts/` and `tests/` is noted but is too minor to propose a change for in this round. |
| **`dumps/` `release/` `hd_costumes_fixed/` `comi-hd-final`** | Untracked / symlink artifacts; not committed to git. No changes needed. |
| **Root files** (`.gitignore`, `README.md`, `requirements.txt`, `setup.py`, `setup.sh`) | Standard project root. No changes needed. |

---

## 4. Summary of Proposed Operations

| # | Operation | From | To | Type |
|---|-----------|------|----|------|
| 1 | Move | `docs/AGENTS.md` | `docs/archive/AGENTS.md` | `git mv` |
| 2 | Move | `docs/FORK_PLAN.md` | `docs/archive/FORK_PLAN.md` | `git mv` |
| 3 | Move | `docs/HD_COSTUME_PLAN.md` | `docs/archive/HD_COSTUME_PLAN.md` | `git mv` |
| 4 | Move | `docs/HD_MANIFEST_SPEC.md` | `docs/archive/HD_MANIFEST_SPEC.md` | `git mv` |
| 5 | Move | `docs/HD_QUALITY_ANALYSIS.md` | `docs/archive/HD_QUALITY_ANALYSIS.md` | `git mv` |
| 6 | Move | `docs/INDEX.md` | `docs/archive/INDEX.md` | `git mv` |
| 7 | Move | `docs/PATH_A_ANALYSIS.md` | `docs/archive/PATH_A_ANALYSIS.md` | `git mv` |
| 8 | Move | `docs/PLAN.md` | `docs/archive/PLAN.md` | `git mv` |
| 9 | Move | `docs/PLAN_QUALITY_FIX.md` | `docs/archive/PLAN_QUALITY_FIX.md` | `git mv` |
| 10 | Move | `docs/RESEARCH.md` | `docs/archive/RESEARCH.md` | `git mv` |
| 11 | Move | `docs/STATUS.md` | `docs/archive/STATUS.md` | `git mv` |
| 12 | Move | `scripts/add_object_alpha.py` | `scripts/archive/add_object_alpha.py` | `git mv` |
| 13 | Move | `scripts/add_object_alpha_v2.py` | `scripts/archive/add_object_alpha_v2.py` | `git mv` |
| 14 | Move | `scripts/add_object_alpha_v3.py` | `scripts/archive/add_object_alpha_v3.py` | `git mv` |
| 15 | Move | `scripts/add_object_alpha_v4.py` | `scripts/archive/add_object_alpha_v4.py` | `git mv` |
| 16 | Move | `scripts/add_object_alpha_v5.py` | `scripts/archive/add_object_alpha_v5.py` | `git mv` |
| 17 | Move | `scripts/analyze_room9.py` | `scripts/archive/analyze_room9.py` | `git mv` |
| 18 | Move | `scripts/demo_upscale.py` | `scripts/archive/demo_upscale.py` | `git mv` |
| 19 | Move | `scripts/demo_upscale_stage.py` | `scripts/archive/demo_upscale_stage.py` | `git mv` |
| 20 | Move | `scripts/upscale_room9.py` | `scripts/archive/upscale_room9.py` | `git mv` |
| 21 | Move | `scripts/verify_room9.py` | `scripts/archive/verify_room9.py` | `git mv` |

> All operations are `git mv` (preserve history). No files are deleted.
> `scummvm/fork/` is never touched.

---

## 5. Files That Stay in Place

These files are **not** moved because they are either (a) active pipeline
code, (b) current reference docs, or (c) infrastructure that should not be
touched:

### Active `docs/` (kept at root)
- `BUILD.md` — build instructions, still needed
- `STRUCTURE.md` — existing structure overview (keep for reference)
- `TECHNICAL_REPORT.md` — current technical report
- `screenshots/` — active before/after images

### Active `scripts/` (kept at root)
- `add_costume_alpha.py`, `add_object_alpha_v6.py` — current alpha pipeline
- `analyze_dump.py`, `analyze_framebuffer.py` — diagnostic tools
- `apply_chaikin_alpha.py` — active pipeline step
- `batch_upscale_costumes.py` — active pipeline step
- `build_object_map.py` — active pipeline step
- `check_hd_dumps.py`, `check_setup.py` — validation tools
- `debug_loop.sh`, `export_all.sh`, `full_pipeline.sh`, `test_hd.sh` — shell pipelines
- `deploy_hd.py` — deploy step
- `diagnose.py`, `hd_diagnose.py` — diagnostics
- `extract_all_raw.py`, `extract_costumes_fixed.py` — extraction steps
- `generate_test_pattern.py` — test utility
- `hd_manifest_gen.py` — manifest generation
- `paths.py` — path utilities (imported by others)
- `sd_vs_hd_diff.py` — comparison tool
- `setup_build_env.sh` — environment setup
- `upscale_costumes.py`, `upscale_esrgan.py` — current upscalers
- `vision_qa.py` — QA tool
