# COMI-HD Repository Audit Summary

**Date:** 2026-07-01  
**Scope:** Full repository audit — docs, scripts, patches, config, and project structure.  
**Repo:** `harrytyp/comiupscale` — Curse of Monkey Island HD Upscale (ScummVM fork)

---

## 1. Overview — Repo Size and Composition

### 1.1 Size
The repository contains the complete ScummVM fork source tree plus project-specific pipeline code, documentation, and configuration. The tracked content (excluding `.git/`) comprises:

- **~600+ source/object files** (ScummVM fork C++ build artifacts + source)
- **59 Markdown documents** (14 project docs + 45 inherited from upstream ScummVM)
- **39+ Python scripts** in `scripts/` (project pipeline)
- **~100+ Python files** in `scummvm/fork/` (upstream devtools/test infrastructure)
- **14 patch files** (5 HD project patches, 9 upstream/third-party patches)
- **5 YAML config files** across `config/`, `setup_wizard/`, and upstream
- **2 JSON config files** (`hd_manifest.json`, `object_map.json`)
- **5 shell scripts** (pipeline/build/launcher)

### 1.2 Top-Level Layout
```
comiupscale/
├── scummvm/
│   ├── fork/              ← Full ScummVM source tree with HD modifications
│   └── patches/           ← HD patch files (reference) + config.h/config.mk
├── docs/                  ← 14 project documentation files
├── scripts/               ← 39 pipeline Python scripts
├── config/                ← paths.yaml, hd_manifest.json, object_map.json, upscale/
├── setup_wizard/          ← MI3-themed setup wizard (Python package, 5 files)
├── tests/                 ← Test files
├── tools/                 ← Third-party tool wrappers (nutcracker, realesrgan)
├── assets/                ← User-generated (untracked, gitignored)
├── game/                  ← Game runtime data (untracked, gitignored)
├── dumps/                 ← Raw resource dumps (untracked)
├── setup.py, setup.sh     ← Entry points
└── README.md              ← Project overview
```

### 1.3 What's Tracked vs Untracked
| Tracked | Untracked (user-generated) |
|---------|---------------------------|
| Full ScummVM fork source + HD engine changes | `assets/extracted/` — original PNGs |
| HD patches for reference | `assets/upscaled/` — 4K upscaled PNGs |
| `config/` — manifest + object map + upscale configs | `game/` — game data + HD deploy |
| `scripts/` — pipeline scripts | `dumps/` — raw resource dumps |
| `docs/` — all project documentation | |
| `setup_wizard/` + `setup.py` | |
| `tests/` | |

---

## 2. Key Audit Findings

### 2.1 Documentation Audit (14 files in `docs/`)

| File | Status | Verdict |
|------|--------|---------|
| `AGENTS.md` | **Legacy/stale** | Windows-only handoff doc (Git Bash, `Z:\` paths, Windows Python). Replace or rewrite for Linux. |
| `BUILD.md` | **Active** | Accurate build instructions for LLVM MinGW cross-compile and Linux native build. Keep. |
| `FORK_PLAN.md` | **Active** | Detailed ScummVM fork architecture plan. Keep. |
| `HD_COSTUME_PLAN.md` | **Stale** | Proposes outdated "intercept SD costume output" approach. The v0.0.3 release uses the HD costume manager instead. Archive. |
| `HD_MANIFEST_SPEC.md` | **Active** | Valid manifest format spec for `hd_manifest.json`. Keep. |
| `HD_QUALITY_ANALYSIS.md` | **Active** | Deep investigation of HD background rendering quality issues. Merge with `PLAN_QUALITY_FIX.md`. |
| `INDEX.md` | **Legacy** | Superseded by `STRUCTURE.md`. Contains old NAS project structure. Archive. |
| `PATH_A_ANALYSIS.md` | **Historical** | Documents abandoned "patch game binary" approach (Path A). Archive. |
| `PLAN.md` | **Stale/superseded** | Original project plan from Windows era. Current project uses `ROADMAP.md`-style tracking. Replace with `ROADMAP.md`. |
| `PLAN_QUALITY_FIX.md` | **Active** | Root cause analysis + solution plan for HD quality issues. Merge with `HD_QUALITY_ANALYSIS.md`. |
| `RESEARCH.md` | **Historical** | Research on HD solutions, MMUCS, NUTcracker. All decisions made. Archive. |
| `STATUS.md` | **Active** | Current status report (2026-05-26). Accurately reflects working/broken items. Keep. |
| `STRUCTURE.md` | **Active** | Repo structure documentation. Needs minor update for new layout. Keep. |
| `TECHNICAL_REPORT.md` | **Active** | Comprehensive technical overview of extraction, upscaling, build, and runtime overlay. Keep. |

**Summary:** 7 of 14 docs are active/current. 5 are stale/historical/legacy and should be archived. 2 should be merged.

### 2.2 Scripts Audit (39 files in `scripts/`)

**Version proliferation — `add_object_alpha.py`:**
- `add_object_alpha.py` (v1) — original
- `add_object_alpha_v2.py` — second iteration
- `add_object_alpha_v3.py` — third iteration
- `add_object_alpha_v4.py` — fourth iteration
- `add_object_alpha_v5.py` — fifth iteration
- `add_object_alpha_v6.py` — sixth iteration (latest)

**Verdict:** v3–v6 supersede v1–v2. The first two versions should be removed. Consider consolidating v4–v6 if the latest (v6) is stable.

**Stale/one-off scripts (hardcoded paths, not general-purpose):**
| Script | Issue |
|--------|-------|
| `upscale_room9.py` | Room-specific, hardcoded paths |
| `analyze_room9.py` | Room-specific, hardcoded paths |
| `verify_room9.py` | Room-specific, hardcoded paths |
| `demo_upscale.py` | One-off demo |
| `demo_upscale_stage.py` | One-off staging script |
| `debug_loop.sh` | Debug-only, hardcoded paths |
| `check_hd_dumps.py` | Debug/analysis utility |
| `test_hd.sh` | Test-only script |

**Active/maintained scripts:**
| Script | Purpose |
|--------|---------|
| `paths.py` | Central path resolver (all scripts should import this) |
| `hd_manifest_gen.py` | Manifest generator |
| `deploy_hd.py` | HD asset deployment |
| `build_object_map.py` | Object→HD mapping |
| `batch_upscale_costumes.py` | Batch costume upscaling |
| `upscale_esrgan.py` | General ESRGAN upscaler |
| `extract_all_raw.py` | Raw asset extraction |
| `extract_costumes_fixed.py` | Costume extraction (patched AKOS) |
| `apply_chaikin_alpha.py` | Alpha smoothing |
| `add_costume_alpha.py` | Costume alpha fixup |
| `add_object_alpha_v6.py` | Object alpha fixup (latest) |
| `sd_vs_hd_diff.py` | SD vs HD comparison tool |
| `vision_qa.py` | Vision quality assessment |
| `check_setup.py` | Setup verification |
| `full_pipeline.sh` | Full build + deploy pipeline |
| `export_all.sh` | Full asset export |
| `setup_build_env.sh` | Build environment setup |

### 2.3 Patch Audit (5 HD project patches in `scummvm/patches/`)

| Patch | Status | Notes |
|-------|--------|-------|
| `0002-HD-Objects-v2-culling-alpha-masks...patch` | **Applied in fork/** | Confirmed in source tree |
| `0003-HD-Costume-Font-managers-SMUSH-passthrough...patch` | **Applied in fork/** | Confirmed in source tree |
| `0004-HD-Costume-Manager-HD-Font-Manager-source-files.patch` | **Applied in fork/** | Confirmed in source tree |
| `scumm-hd-fork.patch` | **Applied in fork/** | Snapshot patch from earlier iteration |
| `scumm-hd-fork-v2.patch` | **Outdated** | Has `.rej` (reject) file — failed to apply cleanly |
| `config.h` / `config.mk` | **Reference only** | MinGW Windows config. Different from fork's Linux build configs |
| `hd_asset_manager.cpp/.h` | **Duplicate** | Standalone copies in `patches/` — fork has its own versions in `fork/engines/scumm/` |
| `hd_video_player.cpp/.h` | **Duplicate** | Same as above |
| `module.mk` | **Duplicate** | Same as above |

**Verdict:** Numbered patches (0002, 0003, 0004) are the canonical set and are already applied in `fork/`. The `scumm-hd-fork-v2.patch` is stale (failed rejects). The standalone `.cpp/.h` files in `patches/` are duplicates of what lives in the fork tree. `config.h`/`config.mk` are a MinGW reference that diverges from the tracked Linux build configs.

### 2.4 Config Audit

| File | Status | Notes |
|------|--------|-------|
| `config/paths.yaml` | **Orphaned/unused** | Contains path definitions but no script references it. `scripts/paths.py` is the active path resolver. |
| `config/hd_manifest.json` | **Active** | HD asset catalog, consumed by the fork at runtime. |
| `config/object_map.json` | **Active** | DOBJ object→filename mapping. |
| `config/upscale/batch_upscale.sh` | **Active** | Batch upscale script. |
| `config/upscale/upscale_objects.sh` | **Active** | Object upscaling. |
| `config/upscale/upscale_remaining.sh` | **Active** | Remaining assets. |
| `setup_wizard/config.yaml` | **Active** | Setup wizard configuration. |
| `setup_wizard/steps/__init__.py` | **Empty/unused** | Only contains a docstring `"""Pipeline steps package."""`. No step modules registered. |

---

## 3. Issues Found

### 3.1 Documentation Proliferation
- **14 docs** for a focused HD fork project — excessive. 7 are stale, historical, or superseded.
- `INDEX.md` (legacy file index) is fully superseded by `STRUCTURE.md`.
- `HD_QUALITY_ANALYSIS.md` and `PLAN_QUALITY_FIX.md` overlap significantly — should be merged.
- `AGENTS.md` is Windows-specific and references paths (`Z:\`, `Git Bash`, `NAS`) that don't apply to Linux deployments.

### 3.2 Script Version Proliferation
- **6 versions** of `add_object_alpha.py` (v1–v6) with no cleanup. Only v6 matters.
- **8 scripts** are one-off debug/demo/room-specific tools with hardcoded paths — contribute noise and cannot be reused.
- `__pycache__/` directories checked in (should be gitignored).

### 3.3 Orphaned Configuration
- `config/paths.yaml` defines path structure but nothing reads it — `scripts/paths.py` is the active resolver. The YAML file is dead code.
- `setup_wizard/steps/__init__.py` is an empty package stub with no actual step modules. The setup wizard (`pipeline.py`, `config.py`, `ui.py`) exists but the steps subpackage is never populated.

### 3.4 Patch Redundancy
- 5 patch files in `scummvm/patches/` when only 3 numbered patches (0002–0004) reflect the current state.
- Duplicate `.cpp/.h` files in `patches/` that already exist in `fork/engines/scumm/`.
- `scumm-hd-fork-v2.patch` has a `.rej` file — clearly failed to apply and should be removed.
- `config.h`/`config.mk` in `patches/` are MinGW-specific and differ from the Linux configs tracked in `fork/`.

### 3.5 Build Artifacts in Tree
- Compiled `.o` and `.d` files from the ScummVM fork build are present in the tree (e.g., `engines/scumm/*.o`, `backends/graphics/opengl/*.o`). These should be gitignored or cleaned up (roughly 400+ object files visible).

---

## 4. Risk Assessment

| Risk | Severity | Likelihood | Impact | Recommended Action |
|------|----------|------------|--------|-------------------|
| **Stale docs mislead contributors** | Medium | High | New contributors follow outdated Windows instructions | Archive 5 stale docs, rewrite AGENTS.md for Linux |
| **Script version confusion** | Low | Medium | Wrong `add_object_alpha` version used, producing incorrect output | Consolidate to v6, remove v1–v2 |
| **Orphaned config causes pipeline breakage** | Medium | Low | If someone edits `config/paths.yaml` expecting it to work | Either wire it into `paths.py` or delete it |
| **Build artifacts inflate repo** | Low | High | Bloated clone, merge conflicts on `.o` files | Add `*.o *.d *.pyc` to `.gitignore`, clean up |
| **Stale patches applied by mistake** | Medium | Low | `scumm-hd-fork-v2.patch` applied over clean fork | Remove the stale patch and reject file |
| **Patch/config duplicate confusion** | Low | Medium | Merge conflicts when both `patches/` and `fork/` versions diverge | Remove duplicates from `patches/` |
| **Empty/unused package signals incomplete feature** | Low | Medium | `setup_wizard/steps/` has no steps — user expects functionality that doesn't exist | Either implement steps or remove the subpackage |
| **Fork source drifts from patch set** | High | Medium | Future rebuilds can't reproduce current state if patches diverge from fork | Regenerate patches from fork after each significant change |

### 4.1 Overall Assessment

**Health:** The core project (ScummVM fork, HD pipeline, active docs) is in good shape. The v0.0.3 release is functional with HD backgrounds, objects, costumes, and fonts working.

**Housekeeping needed:** The repository has accumulated significant cruft — stale docs, script version proliferation, orphaned config files, redundant patches, and build artifacts in the tree. This doesn't affect runtime functionality but adds friction for new contributors and risks confusion during future work.

**Priority actions:**
1. Archive 5 stale docs (`AGENTS.md`, `INDEX.md`, `PATH_A_ANALYSIS.md`, `RESEARCH.md`, `HD_COSTUME_PLAN.md`).
2. Merge `HD_QUALITY_ANALYSIS.md` + `PLAN_QUALITY_FIX.md` into a single document.
3. Clean up `add_object_alpha.py` versions — keep only v6.
4. Remove `config/paths.yaml` or wire it into `scripts/paths.py`.
5. Remove stale patch `scumm-hd-fork-v2.patch` and its `.rej` file.
6. Remove duplicate `.cpp/.h` files from `scummvm/patches/`.
7. Add `*.o`, `*.d`, `*.pyc`, `__pycache__/` to `.gitignore` and clean up.
8. Either populate or remove `setup_wizard/steps/__init__.py`.
9. Replace `PLAN.md` with a current `ROADMAP.md`.
10. Update `STRUCTURE.md` to reflect the current layout.
