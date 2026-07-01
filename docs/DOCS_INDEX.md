# COMI-HD Documentation Index

> **Single source of truth** for navigating all documentation in this repository.
> Last updated: 2026-07-01

---

## How to Use This Index

Each entry includes:
- **File** — relative path from repo root
- **Purpose** — what the document covers
- **Cross-links** — related docs you should read alongside it
- **Status** — `Active` (current/kept), `Stale` (outdated content), `Archived` (historical only), `Merge` (should be combined with another doc)

---

## Category: Architecture & Design

Documents describing system architecture, engine modifications, and design decisions.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 1 | `README.md` | **Project overview** — features, prerequisites, installation (Windows/Linux), HD comparison, changelog, acknowledgments, legal/disclaimer. Entry point for end users. | → `docs/STRUCTURE.md` → `docs/BUILD.md` | **Active** |
| 2 | `docs/STRUCTURE.md` | **Repo structure & architecture** — one-repo layout, tracked vs untracked content, per-workstation build steps, patch regeneration. Describes the full `scummvm/fork/` tree with HD managers. | → `docs/REPO_STRUCTURE.md` → `README.md` | **Active** |
| 3 | `docs/FORK_PLAN.md` | **ScummVM HD fork technical plan** — detailed architecture of `HDAssetManager`, coordinate scaling strategy (×4 via `_hdScale`), files to modify in `engines/scumm/`, `hd_manifest.json` format, build setup (MSYS2/MinGW), testing workflow, milestones, Happy-Ferret reference. | → `docs/HD_MANIFEST_SPEC.md` → `docs/BUILD.md` → `docs/TECHNICAL_REPORT.md` | **Active** |
| 4 | `docs/TECHNICAL_REPORT.md` | **Technical overview** — how extraction (NUTcracker → PNGs), upscaling (RealESRGAN ×4), build (MinGW cross-compile), and runtime overlay (`renderHDComposite()` 4-step compositing) work. Gives the big picture of the full pipeline. | → `docs/FORK_PLAN.md` → `docs/BUILD.md` → `docs/STATUS.md` | **Active** |
| 5 | `docs/HD_MANIFEST_SPEC.md` | **`hd_manifest.json` format specification** — manifest structure, directory convention (no-manifest mode), background asset mapping table (all 40 rooms with HD dimensions), manifest generator script reference. | → `docs/FORK_PLAN.md` → `scripts/hd_manifest_gen.py` | **Active** |
| 6 | `docs/PLAN.md` | **Original project plan** — strategy, why-not-reimport analysis, phases (1–5), asset inventory (38,689 PNGs), key decisions (4× scale, anime model, external HD assets). **Superseded by FORK_PLAN.md and actual implementation.** | → `docs/FORK_PLAN.md` → `docs/PATH_A_ANALYSIS.md` | **Stale** |
| 7 | `config/paths.yaml` | **Path configuration YAML** — defines project directory layout paths. **Orphaned:** no script reads this file; `scripts/paths.py` is the active path resolver. | → `scripts/paths.py` | **Stale** |

---

## Category: Build & Deployment

Documents covering compilation, toolchain setup, and release workflows.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 8 | `docs/BUILD.md` | **Build instructions** — LLVM MinGW cross-compile (Windows binary from Linux), Linux native build, MSYS2 native build, critical `scumm-7-8` vs `scumm_7_8` trap. Asset extraction (NUTcracker), RealESRGAN upscaling, post-processing (alpha fixup), release assembly (ZIPs, GitHub release), and known issues. | → `docs/FORK_PLAN.md` → `docs/TECHNICAL_REPORT.md` → `docs/STATUS.md` | **Active** |
| 9 | `docs/REPO_STRUCTURE.md` | **Repo reorganization proposal** — current vs target directory layout, rationale for archiving 11 stale docs and 10 stale scripts, `archive/` directories under `docs/` and `scripts/`, files that stay in place. | → `docs/STRUCTURE.md` → `docs/AUDIT_SUMMARY.md` | **Active** |
| 10 | `scripts/export_all.sh` | **Full shell-driven asset export** — backgrounds, objects, cutscenes, fonts, costumes via NUTcracker. | → `docs/BUILD.md` → `docs/SCRIPT_INVENTORY.md` | **Active** |
| 11 | `scripts/deploy_hd.py` | **HD asset deployment** — copies upscaled assets to the `hd/` directory. | → `docs/BUILD.md` → `docs/STATUS.md` | **Active** |
| 12 | `setup.sh` | **Quick-start bash script** — download pre-built assets + binary for end users. | → `README.md` | **Active** |

---

## Category: Quality Analysis & Fixes

Documents investigating visual quality issues and their solutions.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 13 | `docs/HD_QUALITY_ANALYSIS.md` | **HD background quality investigation** — deep analysis of why RealESRGAN-upscaled backgrounds look worse in ScummVM than in Windows Photo Viewer. Verifies pixel-perfect decoding, correct OpenGL pipeline, GL_NEAREST filtering. Identifies gamma correction and window-size mismatch as likely root causes. Includes test infrastructure and next steps. | → `docs/PLAN_QUALITY_FIX.md` | **Merge** (with PLAN_QUALITY_FIX.md) |
| 14 | `docs/PLAN_QUALITY_FIX.md` | **Quality root cause & solution plan** — concludes real issue is inadequate texture resampling (nearest-neighbor aliasing + bilinear blur at non-1:1 ratios). Proposes Lanczos/Bicubic GLSL downsampling shader + subpixel AA. References existing xBRZ shaders in ScummVM tree. | → `docs/HD_QUALITY_ANALYSIS.md` → `docs/STATUS.md` | **Merge** (with HD_QUALITY_ANALYSIS.md) |

---

## Category: Pipeline & Scripting

Documents covering scripts, tools, and automation infrastructure.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 15 | `docs/SCRIPT_INVENTORY.md` | **Complete script inventory** — all 53 files in `scripts/`, `tests/`, `config/upscale/`, `setup_wizard/`, and root. Master inventory table with purpose, size, dependencies, status, and recommendation (keep/delete/archive). Includes consolidation opportunities and cleanup plan. | → `docs/AUDIT_SUMMARY.md` → `docs/REPO_STRUCTURE.md` | **Active** |
| 16 | `scripts/paths.py` | **Central path resolver** — imported by all pipeline scripts for project paths. | → `config/paths.yaml` | **Active** |
| 17 | `scripts/hd_manifest_gen.py` | **Manifest generator** — scans extracted backgrounds → produces `hd_manifest.json`. | → `docs/HD_MANIFEST_SPEC.md` | **Active** |
| 18 | `scripts/build_object_map.py` | **Object map builder** — reads DOBJ resources → produces `object_map.json`. | → `config/object_map.json` | **Active** |
| 19 | `scripts/upscale_esrgan.py` | **Standalone RealESRGAN upscaler** — PyTorch, `x4plus_anime_6B` model. | → `docs/BUILD.md` | **Active** |

---

## Category: Status & Audits

Documents capturing project state, audit findings, and progress tracking.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 20 | `docs/STATUS.md` | **Project status report (2026-05-26)** — what works (HD backgrounds, objects, costumes, fonts, builds), what's broken (HD videos, sword cursor, object culling, flickering), build details, known issues with root causes and priorities. | → `docs/BUILD.md` → `docs/TECHNICAL_REPORT.md` → `docs/PLAN_QUALITY_FIX.md` | **Active** |
| 21 | `docs/AUDIT_SUMMARY.md` | **Full repository audit (2026-07-01)** — scope covers docs, scripts, patches, config. Finds: doc proliferation (7 of 14 active), script version proliferation (6 versions of `add_object_alpha`), orphaned config (`config/paths.yaml`), patch redundancy, build artifacts in tree. Priority actions listed. | → `docs/SCRIPT_INVENTORY.md` → `docs/REPO_STRUCTURE.md` → `docs/AGENTS.md` | **Active** |
| 22 | `docs/SCRIPT_INVENTORY.md` | _(also listed in Pipeline above)_ Script inventory generated from audit. | → `docs/AUDIT_SUMMARY.md` | **Active** |

---

## Category: Historical / Archived Research

Documents from the early exploration and research phase. Informational only — all decisions have been made.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 23 | `docs/RESEARCH.md` | **Research findings** — survey of existing SCUMM V8 HD solutions. Covers MMUCS (haywirephoenix, Godot-based viewer, actively developed), NUTcracker AKOS support, confirmation that no public ScummVM HD fork exists, and implications for the project path. Concludes MMUCS is the most promising alternative. | → `docs/PATH_A_ANALYSIS.md` → `docs/PLAN.md` | **Archived** |
| 24 | `docs/PATH_A_ANALYSIS.md` | **Binary format analysis (Path A)** — detailed analysis of every coordinate-bearing data structure in SCUMM V8: RMHD, BOXD, BOXM, SCAL, IMHD, OBCD, SCRP, MAXS. Concludes script bytecode patching is infeasible (weeks–months), recommends runtime coordinate scaling approach. This analysis led to the ScummVM fork approach. | → `docs/FORK_PLAN.md` → `docs/PLAN.md` | **Archived** |
| 25 | `docs/INDEX.md` | **Legacy file index** — old NAS-based project structure (`Z:\Projekte\COMI-Upscaled\`). Superseded by `docs/STRUCTURE.md`. | → `docs/STRUCTURE.md` | **Archived** |
| 26 | `docs/AGENTS.md` | **AI agent handoff document** — Windows-specific session context (Git Bash, `Z:\\` paths, Windows Python). Contains useful asset inventory and critical gotchas but is stale for Linux/repo-based workflows. | → `docs/STATUS.md` | **Stale** |

---

## Category: Planning (Outdated)

One-off planning documents that have been superseded by implementation.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 27 | `docs/HD_COSTUME_PLAN.md` | **HD costume animation fix plan** — proposed two-phase approach: Phase 1 intercept SD rendered output (quick win but no RealESRGAN crispness), Phase 2 add RealESRGAN frames back. **Outdated:** v0.0.3 release uses the HD costume manager instead of SD interception. | → `docs/STATUS.md` → `docs/TECHNICAL_REPORT.md` | **Stale** |
| 28 | `docs/PLAN.md` | _(also in Architecture above)_ Original project plan — historical reference only. | → `docs/FORK_PLAN.md` | **Stale** |

---

## Category: Engine Patches & Configuration

Inline documentation in patch headers and config files.

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 29 | `scummvm/patches/0002-HD-Objects-v2-culling-alpha-masks...patch` | **HD Objects patch (applied)** — culling, alpha masks, pixel-precise transparency for HD object overlay. | → `docs/FORK_PLAN.md` → `scummvm/fork/engines/scumm/` | **Active** |
| 30 | `scummvm/patches/0003-HD-Costume-Font-managers-SMUSH-passthrough...patch` | **HD Costume/Font/SMUSH patch (applied)** — costume/font managers and SMUSH video passthrough with OOB protection. | → `docs/FORK_PLAN.md` → `scummvm/fork/engines/scumm/` | **Active** |
| 31 | `scummvm/patches/0004-HD-Costume-Manager-HD-Font-Manager-source-files.patch` | **HD manager source files patch (applied)** — adds source files for HD Costume and Font managers. | → `docs/FORK_PLAN.md` → `scummvm/fork/engines/scumm/` | **Active** |
| 32 | `scummvm/patches/scumm-hd-fork.patch` | **Snapshot patch** — earlier iteration of the HD fork changes. Partially superseded by numbered patches. | → `scummvm/patches/0002-*` → `scummvm/patches/0003-*` → `scummvm/patches/0004-*` | **Stale** |
| 33 | `scummvm/patches/scumm-hd-fork-v2.patch` | **Stale patch** — has `.rej` (reject) file, failed to apply cleanly. Should be removed. | → `scummvm/patches/scumm-hd-fork.patch` | **Stale** |
| 34 | `scummvm/patches/config.h` | **MinGW build config (reference)** — pre-configured `config.h` for Windows cross-compile. Differs from the Linux config tracked in `scummvm/fork/`. | → `scummvm/patches/config.mk` → `docs/BUILD.md` | **Reference** |
| 35 | `scummvm/patches/config.mk` | **MinGW build config.mk (reference)** — pre-configured build makefile for Windows cross-compile. | → `scummvm/patches/config.h` → `docs/BUILD.md` | **Reference** |
| 36 | `scummvm/patches/hd_asset_manager.h` | **Standalone HD asset manager header** — duplicate of the file in `scummvm/fork/engines/scumm/`. | → `scummvm/fork/engines/scumm/hd_asset_manager.h` | **Duplicate** |
| 37 | `scummvm/patches/hd_asset_manager.cpp` | **Standalone HD asset manager implementation** — duplicate of the file in `scummvm/fork/engines/scumm/`. | → `scummvm/fork/engines/scumm/hd_asset_manager.cpp` | **Duplicate** |
| 38 | `scummvm/patches/hd_video_player.h` | **Standalone HD video player header** — duplicate of the file in `scummvm/fork/engines/scumm/`. | → `scummvm/fork/engines/scumm/hd_video_player.h` | **Duplicate** |
| 39 | `scummvm/patches/hd_video_player.cpp` | **Standalone HD video player implementation** — duplicate of the file in `scummvm/fork/engines/scumm/`. | → `scummvm/fork/engines/scumm/hd_video_player.cpp` | **Duplicate** |
| 40 | `scummvm/patches/module.mk` | **Standalone module.mk** — duplicate of the build entries in `scummvm/fork/engines/scumm/module.mk`. | → `scummvm/fork/engines/scumm/module.mk` | **Duplicate** |
| 41 | `config/hd_manifest.json` | **HD asset catalog** — JSON manifest consumed by the ScummVM fork at runtime. Lists all HD backgrounds with dimensions. | → `docs/HD_MANIFEST_SPEC.md` | **Active** |
| 42 | `config/object_map.json` | **DOBJ→filename mapping** — maps object IDs to their HD texture filenames. | → `scripts/build_object_map.py` | **Active** |

---

## Category: Screenshots & Visual Assets

| # | File | Purpose | Cross-links | Status |
|---|------|---------|-------------|--------|
| 43 | `docs/screenshots/room9.png` | **Before screenshot** — Room 9 (Cannon Gallery) at original SD resolution. | → `docs/screenshots/hd_background_room9.png` | **Active** |
| 44 | `docs/screenshots/hd_background_room9.png` | **After screenshot** — Room 9 with 4× HD textures (2560×1920). | → `docs/screenshots/room9.png` → `README.md` | **Active** |

---

## Documents Not Included in This Index

The following `.md` files exist in the repository under the `scummvm/fork/` subtree but are **inherited from upstream ScummVM** (not project-specific documentation):

- `scummvm/fork/README.md` — Upstream ScummVM README
- `scummvm/fork/NEWS.md` — Upstream release notes
- `scummvm/fork/CONTRIBUTING.md` — Upstream contribution guidelines
- `scummvm/fork/AI-GUIDELINES.md` — Upstream AI contribution guidelines
- `scummvm/fork/RELEASE_README.md` — Fork-specific release instructions
- Various platform READMEs (`dists/`, `backends/platform/`, `devtools/`) — Upstream documentation for target platforms

These are not project-owned and are not included in this index. Refer to the upstream ScummVM documentation for those.

---

## Quick-Start Guide for New Contributors

**Read these three documents first:**

1. **`README.md`** → Start here for the project overview, what COMI-HD does, how to install and play, and the legal context.
2. **`docs/STRUCTURE.md`** → Understand the repository layout, what's tracked vs untracked, and how to build the fork.
3. **`docs/TECHNICAL_REPORT.md`** → Get the full technical picture: how assets are extracted, upscaled, and composited at runtime via the HD overlay pipeline.

After those three, dive deeper into `docs/BUILD.md` (to build the fork yourself), `docs/FORK_PLAN.md` (for the engine architecture), or `docs/STATUS.md` (for what currently works and what's still broken).
