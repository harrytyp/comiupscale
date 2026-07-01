# SCRIPT INVENTORY — COMI HD Upscale Pipeline

**Generated:** 2026-07-01  
**Scope:** All executable scripts, shell pipelines, test files, and supporting infrastructure under `scripts/`, `tests/`, `config/upscale/`, `setup_wizard/`, and the project root.

---

## 1. Master Inventory Table

### 1.1 Active Pipeline Scripts (`scripts/`)

| # | Script | Purpose | Size (B) | Lines | Dependencies | Status | Rec. |
|---|--------|---------|----------|-------|--------------|--------|------|
| 1 | `paths.py` | Central path resolver — all scripts import this for project paths | 2,729 | 72 | `os` | ✅ Active | **Keep** |
| 2 | `hd_manifest_gen.py` | Scan extracted backgrounds → produce `hd_manifest.json` mapping room→HD dims | 3,044 | 91 | `PIL`, `paths` | ✅ Active | **Keep** |
| 3 | `build_object_map.py` | Read DOBJ resource via NUTcracker → map `obj_nr`↔filename → `object_map.json` | 6,534 | 185 | `nutcracker.sputm`, `paths` | ✅ Active | **Keep** |
| 4 | `check_setup.py` | Setup validation & path debugging for the project | 6,404 | 192 | `paths` | ✅ Active | **Keep** |
| 5 | `check_hd_dumps.py` | Read debug dump raw files from ScummVM fork → HD rendering health report | 4,717 | 145 | `struct` | ✅ Active | **Keep** |
| 6 | `deploy_hd.py` | Deploy upscaled assets to HD directory (robocopy on Win, shutil on Linux) | 3,088 | 95 | `shutil`, `subprocess`, `paths` | ✅ Active | **Keep** |
| 7 | `extract_all_raw.py` | Extract ALL raw assets (backgrounds, objects, layers, fonts, costumes) | 6,013 | 169 | `nutcracker.*`, `numpy` | ✅ Active | **Keep** |
| 8 | `extract_costumes_fixed.py` | AKOS costume extractor with correct palette/alpha mapping (2026-06-28 fixes) | 10,108 | 261 | `numpy`, `PIL`, `nutcracker` | ✅ Active | **Keep** |
| 9 | `export_all.sh` | Full shell-driven asset export (backgrounds, objects, cutscenes, fonts, costumes) | 8,209 | 233 | `bash`, `nutcracker.exe` (Win) | ✅ Active | **Keep** |
| 10 | `generate_test_pattern.py` | Generate 2560×1920 test pattern PNG for resolution verification | 3,502 | 113 | `PIL`, `struct` | ✅ Active | **Keep** |
| 11 | `debug_loop.sh` | Full automated debug & test loop — setup, Xvfb, ScummVM launch, screenshot, QA | 34,581 | 958 | `bash`, ScummVM bin, `vision_qa.py` | ✅ Active | **Keep** |
| 12 | `test_hd.sh` | Automated HD rendering test suite — builds, launches, captures dumps | 3,012 | 108 | `bash`, `check_setup.py` | ✅ Active | **Keep** |
| 13 | `add_costume_alpha.py` | GPU-batched alpha mask compositing for costumes (v4 engine) | 8,474 | 242 | `PIL`, `numpy`, `tqdm`, `torch` (opt) | ✅ Active | **Keep** |
| 14 | `add_object_alpha_v4.py` | Pixel-precise alpha mask v4 (called by `upscale_remaining.sh`) | 2,185 | 71 | `PIL`, `numpy` | ✅ Active | **Keep**⎱ |
| 15 | `add_object_alpha_v5.py` | Optimized alpha mask v5 w/ `os.scandir`, NEAREST mask resize (called by `pipeline.py`) | 2,500 | 83 | `PIL`, `numpy`, `tqdm` | ✅ Active | **Keep**⎱ |
| 16 | `add_object_alpha_v6.py` | **Latest** alpha mask v6 — multiprocess + green-background cleanup | 7,330 | 204 | `PIL`, `numpy`, `concurrent.futures` | ✅ Active | **Keep** |
| 17 | `apply_chaikin_alpha.py` | Vector-contour alpha smoothing (Chaikin corner-cutting) for HD assets | 12,326 | 271 | `cv2`, `numpy`, `PIL`, `tqdm` | ✅ Active | **Keep** |
| 18 | `diagnose.py` | Parse ScummVM HD debug logs → structured report of what works | 7,295 | 215 | `re`, `collections` | ✅ Active | **Keep** |
| 19 | `hd_diagnose.py` | Automated HD texture diagnose (alternative parser, JSON output) | 8,281 | 235 | `re`, `json`, `collections` | ✅ Active | **Keep**★ |
| 20 | `sd_vs_hd_diff.py` | Read SD-composite & diff raw files → per-region diff analysis + PNG viz | 7,663 | 206 | `struct`, `math` | ✅ Active | **Keep** |
| 21 | `vision_qa.py` | Send screenshot to MiMo vision API → structured quality ratings | 9,802 | 279 | `urllib`, `json`, `base64` | ✅ Active | **Keep** |
| 22 | `upscale_costumes.py` | Bulk costume upscale via RealESRGAN with tqdm progress | 3,899 | 115 | `subprocess`, `tqdm` | ✅ Active | **Keep** |
| 23 | `upscale_esrgan.py` | Standalone RealESRGAN x4plus_anime_6B (PyTorch, no basicsr) | 6,395 | 155 | `torch`, `numpy`, `cv2` | ✅ Active | **Keep** |

⎱ v4 & v5 are still referenced by shell scripts — consolidate imports to v6 when those scripts are updated.  
★ Overlaps with `diagnose.py` — consider merging.

### 1.2 Stale / Legacy Scripts (`scripts/`)

| # | Script | Purpose | Size (B) | Lines | Why Stale | Rec. |
|---|--------|---------|----------|-------|-----------|------|
| 24 | `add_object_alpha.py` (v1) | Original alpha mask — used palette index 0 only | 4,246 | 139 | Superseded by v6 | **Delete** |
| 25 | `add_object_alpha_v2.py` | Improved — border-pixel detection instead of palette idx 0 | 3,333 | 105 | Superseded by v6 | **Delete** |
| 26 | `add_object_alpha_v3.py` | Distance-based chroma-key with edge falloff | 2,600 | 79 | Superseded by v6 | **Delete** |
| 27 | `analyze_dump.py` | HD surface dump analysis — hardcoded Windows paths (`C:\Users\…`, `Z:\…`) | 4,348 | 114 | Hardcoded paths; use `tests/analyze_dump.py` instead | **Delete** |
| 28 | `analyze_room9.py` | Analyze Room 9 objects via NUTcracker | 2,919 | 81 | Room-specific, hardcoded paths | **Delete** |
| 29 | `analyze_framebuffer.py` | Find actual framebuffer dimensions from raw dump | 3,788 | 105 | Hardcoded Windows paths | **Delete** |
| 30 | `batch_upscale_costumes.py` | Batch upscale costumes via RealESRGAN + Chaikin alpha | 2,630 | 76 | Hardcoded paths; workflow subsumed by `upscale_remaining.sh` | **Archive** |
| 31 | `demo_upscale.py` | Trivial LANCZOS demo of room 15 town background | 765 | 26 | One-off demo, no real use | **Delete** |
| 32 | `demo_upscale_stage.py` | Trivial LANCZOS demo of room 19 stage background | 772 | 26 | One-off demo, no real use | **Delete** |
| 33 | `full_pipeline.sh` | End-to-end: Extract → Upscale → Build → Play | 7,453 | 205 | Superseded by `setup.py` w/ `setup_wizard/` | **Archive** |
| 34 | `setup_build_env.sh` | MSYS2 MinGW64 environment setup (pacman) | 1,178 | 49 | MSYS2-only, not applicable to Linux build | **Archive** |
| 35 | `upscale_room9.py` | Upscale Room 9 costumes only | 1,376 | 35 | Room-specific, hardcoded paths | **Delete** |
| 36 | `verify_room9.py` | Proof-of-concept: overlay Guybrush on cannon bg | 2,389 | 57 | Room-specific, hardcoded paths | **Delete** |

### 1.3 Configuration Shell Scripts (`config/upscale/`)

| # | Script | Purpose | Size (B) | Lines | Status | Rec. |
|---|--------|---------|----------|-------|--------|------|
| 37 | `batch_upscale.sh` | Upscale all 40 extracted backgrounds with RealESRGAN | 1,122 | 43 | ✅ Active | **Keep** |
| 38 | `upscale_objects.sh` | Upscale 600+ objects and 234 object layers | 1,545 | 55 | ✅ Active | **Keep** |
| 39 | `upscale_remaining.sh` | Upscale costumes (25K+) + fonts + alpha fixup + deploy | 8,589 | 256 | ✅ Active | **Keep** |

### 1.4 Test Files (`tests/`)

| # | File | Purpose | Size (B) | Lines | Lang | Status | Rec. |
|---|------|--------|----------|-------|------|--------|------|
| 40 | `analyze_dump.py` | General HD debug dump analyzer (raw RGBA, palette, cursor checks) | 9,087 | 230 | Python | ✅ Active | **Keep** |
| 41 | `test_room.cpp` | Standalone HD compositing pipeline test — auto-verify, no window | 35,958 | 924 | C++ | ✅ Active | **Keep** |
| 42 | `test_room_sdl.cpp` | Same as test_room + SDL2 window for visual inspection | 17,559 | 427 | C++ | ✅ Active | **Keep** |
| 43 | `test_hd_composite.cpp` | Minimal HD compositing unit test (no ScummVM dependency) | 26,666 | 696 | C++ | ✅ Active | **Keep** |
| 44 | `test_room_debug.cpp` | Quick debug dump tool — pixel readout for analysis | 3,203 | 71 | C++ | Subset of `test_room.cpp` | **Delete** |
| 45 | `test_pattern_2560x1920.png` | 4K test pattern with checkerboard scales | — | — | PNG | ✅ Active | **Keep** |

### 1.5 Setup & Wizard

| # | File | Purpose | Size (B) | Lines | Dependencies | Status | Rec. |
|---|------|--------|----------|-------|--------------|--------|------|
| 46 | `setup.py` | Main entry point — interactive wizard or CLI pipeline | 5,707 | 162 | `setup_wizard.*` | ✅ Active | **Keep** |
| 47 | `setup.sh` | Quick-setup bash script — download pre-built assets + binary | 5,954 | 175 | `bash`, `curl`/`wget` | ✅ Active | **Keep** |
| 48 | `setup_wizard/__init__.py` | Package init, exports version | 81 | 3 | — | ✅ Active | **Keep** |
| 49 | `setup_wizard/ui.py` | MI3-themed terminal UI via Rich library | 9,557 | 272 | `rich` | ✅ Active | **Keep** |
| 50 | `setup_wizard/config.py` | Config YAML load/save with schema validation | 4,479 | 138 | `yaml` | ✅ Active | **Keep** |
| 51 | `setup_wizard/pipeline.py` | Master orchestrator — detect, extract, upscale, alpha, deploy, build | 13,472 | 373 | `setup_wizard.ui` | ✅ Active | **Keep** |
| 52 | `setup_wizard/steps/__init__.py` | Empty package stub (only docstring, no modules) | 31 | 1 | — | ❌ Empty | **Delete** or implement |

### 1.6 Orphaned / Unused

| # | File | Purpose | Size (B) | Status | Rec. |
|---|------|---------|----------|--------|------|
| 53 | `config/paths.yaml` | YAML path definitions — **no script reads this** | 903 | ❌ Orphaned | **Delete** or wire into `paths.py` |

---

## 2. Recommendations Summary

### 2.1 Keep (35 files)
All scripts marked ✅ **Active** above should be retained. They form the working pipeline:
- Core pipeline: `paths.py`, `hd_manifest_gen.py`, `build_object_map.py`, `deploy_hd.py`, `extract_all_raw.py`, `extract_costumes_fixed.py`
- Alpha handling: `add_object_alpha_v6.py`, `add_costume_alpha.py`, `apply_chaikin_alpha.py`
- Upscale: `upscale_costumes.py`, `upscale_esrgan.py`, and 3 `config/upscale/` shell scripts
- Diagnostics: `check_setup.py`, `check_hd_dumps.py`, `diagnose.py`, `hd_diagnose.py`, `sd_vs_hd_diff.py`, `vision_qa.py`
- Test infrastructure: `debug_loop.sh`, `test_hd.sh`, `generate_test_pattern.py`, `export_all.sh`
- Tests: `tests/analyze_dump.py`, `tests/test_room.cpp`, `tests/test_room_sdl.cpp`, `tests/test_hd_composite.cpp`, `tests/test_pattern_2560x1920.png`
- Setup wizard: `setup.py`, `setup.sh`, `setup_wizard/*` (except `steps/__init__.py`)

### 2.2 Delete (12 files)
| File | Reason |
|------|--------|
| `add_object_alpha.py` | Superseded by v6 |
| `add_object_alpha_v2.py` | Superseded by v6 |
| `add_object_alpha_v3.py` | Superseded by v6 |
| `analyze_dump.py` (scripts/) | Hardcoded Windows paths; `tests/analyze_dump.py` is the general version |
| `analyze_room9.py` | Room-specific, hardcoded paths |
| `analyze_framebuffer.py` | Hardcoded Windows paths |
| `demo_upscale.py` | Trivial one-off demo |
| `demo_upscale_stage.py` | Trivial one-off demo |
| `upscale_room9.py` | Room-specific, hardcoded paths |
| `verify_room9.py` | Room-specific, hardcoded paths |
| `tests/test_room_debug.cpp` | Subset of `test_room.cpp` |
| `setup_wizard/steps/__init__.py` | Empty stub — no implementation |

### 2.3 Archive (4 files)
| File | Reason |
|------|--------|
| `batch_upscale_costumes.py` | Contains unique upscale+Chaikin-alpha workflow reference; subsumed by `upscale_remaining.sh` |
| `full_pipeline.sh` | Historical reference for original extract→upscale→build→play flow; superseded by `setup.py` |
| `setup_build_env.sh` | Reference for MSYS2 build env setup; not applicable to Linux builds |
| `config/paths.yaml` | Path definitions — useful as documentation if removed from live use |

---

## 3. Consolidation Opportunities

### 3.1 Alpha Generator Consolidation (Highest Priority)
Six versions of `add_object_alpha.py` exist. The call graph is:

```
upscale_remaining.sh ──► add_object_alpha_v4.py
pipeline.py ──────────► add_object_alpha_v5.py
(standalone) ─────────► add_object_alpha_v6.py  (latest)
```

**Action:** Update `upscale_remaining.sh` and `pipeline.py` (or `setup_wizard/pipeline.py`) to call `add_object_alpha_v6.py` instead of v4/v5, then delete v1–v3 immediately and v4–v5 after the swap.

### 3.2 Log Parser Merge (Low Priority)
`diagnose.py` and `hd_diagnose.py` do nearly the same thing — parse ScummVM HD debug logs. They have slightly different output formats (table vs JSON). 

**Action:** Unify into a single `diagnose.py` with `--json` / `--table` flags. Archive or delete `hd_diagnose.py`.

### 3.3 C++ Test File Cleanup (Low Priority)
`tests/test_room_debug.cpp` (71 lines) is a quick hack subset of the functionality already in `tests/test_room.cpp` (924 lines). 

**Action:** Delete `test_room_debug.cpp`. The full `test_room.cpp` and its SDL variant (`test_room_sdl.cpp`) cover all test scenarios.

### 3.4 Duplicate Path Management
`config/paths.yaml` defines paths that duplicate `scripts/paths.py`. No script loads the YAML file — the Python module `paths.py` is the canonical resolver.

**Action:** Either:
- Delete `config/paths.yaml` if unused (simplest), or
- Have `paths.py` read `config/paths.yaml` at import time to make it the single source of truth.

### 3.5 Setup Wizard Steps Package
`setup_wizard/steps/__init__.py` is an empty stub (1 line, 31 bytes) with no actual step modules. The `setup_wizard/pipeline.py` orchestrator defines all steps inline.

**Action:** Either implement step modules in `steps/` and refactor `pipeline.py` to use them, or delete the empty `steps/__init__.py` and remove the `steps/` directory.

### 3.6 Shell Script Portability
The three `config/upscale/*.sh` scripts and `export_all.sh` reference `realesrgan-ncnn-vulkan.exe` (Windows). These work on Linux via Wine or if the tool path is updated. 

**Action:** Consider making the tool path configurable (env var or argument) so the scripts work on both platforms without editing.

---

## 4. Size Overview

| Category | Files | Total Size | Lines |
|----------|-------|-----------|-------|
| Active scripts (`scripts/` active) | 23 | ~174 KB | ~4,800 |
| Stale/legacy scripts (`scripts/` stale) | 13 | ~38 KB | ~1,250 |
| Config upscale (`config/upscale/`) | 3 | ~11 KB | ~350 |
| Test files (`tests/`) | 6 | ~93 KB | ~2,350 |
| Setup wizard (`setup_wizard/`) | 5 | ~28 KB | ~790 |
| Root setup | 2 | ~12 KB | ~340 |
| Orphaned | 1 | ~1 KB | ~35 |
| **Total** | **53** | **~355 KB** | **~9,900** |

---

## 5. Quick Cleanup Plan

1. **Immediate (safe):** Delete `add_object_alpha.py`, `_v2.py`, `_v3.py`, `demo_upscale.py`, `demo_upscale_stage.py`, `test_room_debug.cpp`, `setup_wizard/steps/__init__.py` — no active caller depends on these.
2. **After caller update:** Delete `add_object_alpha_v4.py`, `add_object_alpha_v5.py`, `batch_upscale_costumes.py` — once callers are migrated to v6.
3. **After verification:** Delete `analyze_dump.py` (scripts/), `analyze_room9.py`, `analyze_framebuffer.py`, `upscale_room9.py`, `verify_room9.py`.
4. **Archive:** Move `full_pipeline.sh`, `setup_build_env.sh` to an `archive/` subdirectory or a git tag.
5. **Optional:** Unify `diagnose.py` / `hd_diagnose.py`, wire or delete `config/paths.yaml`, implement or remove `setup_wizard/steps/`.
