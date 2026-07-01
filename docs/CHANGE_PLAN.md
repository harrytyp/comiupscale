# COMI-HD Repository Restructuring — Change Plan

> **Branch:** `repo-organization`  
> **Base:** `main`  
> **All changes are isolated to this branch. No changes are merged to `main` until approved.**  
> **Global rollback:** `git checkout main && git branch -D repo-organization`

---

## Overview

This plan restructures the COMI-HD repository to reduce clutter, eliminate
confusion from stale/duplicate files, and consolidate related documentation.
It is scoped strictly to the project's own files — **`scummvm/fork/` (the
ScummVM source tree) is never touched**.

The plan is ordered **lowest risk first**. Each change entry specifies:
- **What** — the actual file operation
- **Why** — the rationale from the audits
- **Risk level** — Very Low / Low / Medium / High
- **Rollback** — exact commands to undo the change
- **Git commands** — exact commands to execute the change

---

## Phase 0 — No-Brainer Cleanups (Risk: Very Low)

Files that are demonstrably unused, empty, or superseded with zero callers.
No functional impact. Each change is independently reversible.

---

### 0.1 Remove empty package stub: `setup_wizard/steps/__init__.py`

| Field | Value |
|-------|-------|
| **What** | Delete the empty `steps/` package stub (31 bytes, 1-line docstring) and its parent directory |
| **Why** | AUDIT_SUMMARY.md §2.4: "Empty/unused — only contains a docstring. No step modules registered." No code imports this subpackage; `pipeline.py` defines all steps inline |
| **Risk** | ⚪ Very Low — empty file, no references |
| **Rollback** | `git checkout HEAD~1 -- setup_wizard/steps/__init__.py && mkdir -p setup_wizard/steps` |

```bash
git rm setup_wizard/steps/__init__.py
rmdir setup_wizard/steps   # removes empty directory after git rm
git commit -m "phase0: remove empty setup_wizard/steps/__init__.py stub"
```

---

### 0.2 Remove debug subset: `tests/test_room_debug.cpp`

| Field | Value |
|-------|-------|
| **What** | Delete `tests/test_room_debug.cpp` (71 lines, quick hack debug tool) |
| **Why** | SCRIPT_INVENTORY.md §2.2: "Subset of `test_room.cpp` (924 lines)." All functionality is covered by `test_room.cpp` |
| **Risk** | ⚪ Very Low — standalone compile-only file, no build system integration |
| **Rollback** | `git checkout HEAD~1 -- tests/test_room_debug.cpp` |

```bash
git rm tests/test_room_debug.cpp
git commit -m "phase0: remove test_room_debug.cpp (subset of test_room.cpp)"
```

---

### 0.3 Delete stale alpha script versions v1–v3

| Field | Value |
|-------|-------|
| **What** | Delete `scripts/add_object_alpha.py` (v1), `scripts/add_object_alpha_v2.py`, `scripts/add_object_alpha_v3.py` |
| **Why** | AUDIT_SUMMARY.md §3.2: "6 versions of add_object_alpha.py with no cleanup. Only v6 matters." v1 uses palette idx 0 only, v2 uses border-pixel detection, v3 uses distance chroma-key — all superseded by v6's multiprocess + green-background cleanup |
| **Risk** | ⚪ Very Low — no active caller references v1–v3 (call graph: `upscale_remaining.sh` → v4, `pipeline.py` → v5, standalone → v6) |
| **Rollback** | `git checkout HEAD~1 -- scripts/add_object_alpha.py scripts/add_object_alpha_v2.py scripts/add_object_alpha_v3.py` |

```bash
git rm scripts/add_object_alpha.py scripts/add_object_alpha_v2.py scripts/add_object_alpha_v3.py
git commit -m "phase0: delete add_object_alpha v1-v3 (superseded by v6)"
```

---

### 0.4 Delete one-off demo scripts

| Field | Value |
|-------|-------|
| **What** | Delete `scripts/demo_upscale.py` (26 lines) and `scripts/demo_upscale_stage.py` (26 lines) |
| **Why** | SCRIPT_INVENTORY.md §1.2: "Trivial LANCZOS demo, no real use." Both are one-off experiments with hardcoded room numbers (room 15, room 19) |
| **Risk** | ⚪ Very Low — never called by any pipeline or script |
| **Rollback** | `git checkout HEAD~1 -- scripts/demo_upscale.py scripts/demo_upscale_stage.py` |

```bash
git rm scripts/demo_upscale.py scripts/demo_upscale_stage.py
git commit -m "phase0: delete one-off demo scripts (demo_upscale.py, demo_upscale_stage.py)"
```

---

### 0.5 Delete orphaned config: `config/paths.yaml`

| Field | Value |
|-------|-------|
| **What** | Delete `config/paths.yaml` (33 lines, 903 bytes) |
| **Why** | AUDIT_SUMMARY.md §3.3: "Defines path structure but nothing reads it — `scripts/paths.py` is the active path resolver. The YAML file is dead code." Also flagged in SCRIPT_INVENTORY.md §1.6 as orphaned/unused |
| **Risk** | ⚪ Very Low — no script imports, reads, or references this file |
| **Rollback** | `git checkout HEAD~1 -- config/paths.yaml` |

```bash
git rm config/paths.yaml
git commit -m "phase0: remove orphaned config/paths.yaml (no script reads it)"
```

---

## Phase 1 — Documentation Archival (Risk: Low)

Move stale, superseded, or purely historical documentation out of the active
`docs/` directory into `docs/archive/`. Uses `git mv` to preserve history.
No files are deleted — they remain accessible at `docs/archive/`.

---

### 1.1 Create archive directory

```bash
mkdir -p docs/archive
```

---

### 1.2 Archive stale research docs

| # | File | Why archived |
|---|------|-------------|
| 1 | `docs/INDEX.md` | Legacy NAS-based file index (`Z:\\` paths). Superseded by `docs/STRUCTURE.md` (AUDIT_SUMMARY.md §2.1) |
| 2 | `docs/PATH_A_ANALYSIS.md` | Documents abandoned "patch game binary" approach (Path A). All decisions made; led to the ScummVM fork approach now implemented (AUDIT_SUMMARY.md §2.1) |
| 3 | `docs/HD_COSTUME_PLAN.md` | Proposed outdated "intercept SD costume output" approach. v0.0.3 uses the HD costume manager instead (AUDIT_SUMMARY.md §2.1) |
| 4 | `docs/RESEARCH.md` | Survey of existing SCUMM V8 HD solutions. Informational only — all decisions made (DOCS_INDEX.md §Historical/Archived) |

| Field | Value |
|-------|-------|
| **What** | `git mv` 4 stale docs → `docs/archive/` |
| **Why** | Clear active-vs-historical separation; reduces docs/ from 14 files to 10 |
| **Risk** | 🟢 Low — `git mv` preserves history; files remain in repo at `docs/archive/` |
| **Rollback** | `git mv docs/archive/{INDEX.md,PATH_A_ANALYSIS.md,HD_COSTUME_PLAN.md,RESEARCH.md} docs/` |

```bash
git mv docs/INDEX.md docs/archive/INDEX.md
git mv docs/PATH_A_ANALYSIS.md docs/archive/PATH_A_ANALYSIS.md
git mv docs/HD_COSTUME_PLAN.md docs/archive/HD_COSTUME_PLAN.md
git mv docs/RESEARCH.md docs/archive/RESEARCH.md
git commit -m "phase1: archive 4 stale research docs"
```

---

## Phase 2 — Script Cleanup (Risk: Medium)

Clean up script version proliferation and delete room-specific/Windows-path
scripts. Some changes require updating callers before deleting referenced files.

---

### 2.1 Consolidate `add_object_alpha` v4–v6

**Current callers:**
- `config/upscale/upscale_remaining.sh` → calls `add_object_alpha_v4.py`
- `setup_wizard/pipeline.py` → calls `add_object_alpha_v5.py`

**Plan:**

| Step | Action |
|------|--------|
| 2.1a | Update `config/upscale/upscale_remaining.sh` to call `add_object_alpha_v6.py` instead of v4 |
| 2.1b | Update `setup_wizard/pipeline.py` to call `add_object_alpha_v6.py` instead of v5 |
| 2.1c | Delete v4 (`add_object_alpha_v4.py`) and v5 (`add_object_alpha_v5.py`) |
| 2.1d | Optionally rename `add_object_alpha_v6.py` → `add_object_alpha.py` (clean name) |

| Field | Value |
|-------|-------|
| **What** | Update callers → delete v4/v5 → keep only v6 (renamed or as-is) |
| **Why** | SCRIPT_INVENTORY.md §3.1: "Six versions of add_object_alpha.py exist. Update callers, then delete v4-v5 after the swap" |
| **Risk** | 🟡 Medium — callers must be updated first; if a caller is missed it will fail with "file not found" |
| **Rollback** | Undo caller edits: `git checkout HEAD~1 -- config/upscale/upscale_remaining.sh setup_wizard/pipeline.py`; Restore scripts: `git checkout HEAD~1 -- scripts/add_object_alpha_v4.py scripts/add_object_alpha_v5.py` |

```bash
# Step 2.1a: Update upscale_remaining.sh to call v6
# (edit config/upscale/upscale_remaining.sh: replace 'add_object_alpha_v4' with 'add_object_alpha_v6')

# Step 2.1b: Update pipeline.py to call v6
# (edit setup_wizard/pipeline.py: replace 'add_object_alpha_v5' with 'add_object_alpha_v6')

# Step 2.1c: Delete old versions
git rm scripts/add_object_alpha_v4.py scripts/add_object_alpha_v5.py

# Step 2.1d (optional): Rename v6 to clean name
# git mv scripts/add_object_alpha_v6.py scripts/add_object_alpha.py

git commit -m "phase2: consolidate add_object_alpha to v6, update callers, delete v4-v5"
```

---

### 2.2 Delete room-specific / one-off scripts

| # | File | Lines | Why |
|---|------|-------|-----|
| 1 | `scripts/analyze_room9.py` | 81 | Room-specific, hardcoded paths (SCRIPT_INVENTORY.md §1.2) |
| 2 | `scripts/upscale_room9.py` | 35 | Room-specific, superseded by `upscale_esrgan.py` |
| 3 | `scripts/verify_room9.py` | 57 | Room-specific, hardcoded paths |

| Field | Value |
|-------|-------|
| **What** | Delete 3 room-specific scripts |
| **Why** | All hardcode Room 9 paths; not general-purpose pipeline components |
| **Risk** | 🟢 Low — no active caller references these files |
| **Rollback** | `git checkout HEAD~1 -- scripts/analyze_room9.py scripts/upscale_room9.py scripts/verify_room9.py` |

```bash
git rm scripts/analyze_room9.py scripts/upscale_room9.py scripts/verify_room9.py
git commit -m "phase2: delete room-specific scripts (analyze/upscale/verify_room9)"
```

---

### 2.3 Delete Windows-path scripts from `scripts/`

| # | File | Lines | Why |
|---|------|-------|-----|
| 1 | `scripts/analyze_dump.py` | 114 | Hardcoded Windows paths (`C:\\Users\\…`); use `tests/analyze_dump.py` instead (SCRIPT_INVENTORY.md §1.2) |
| 2 | `scripts/analyze_framebuffer.py` | 105 | Hardcoded Windows paths (SCRIPT_INVENTORY.md §1.2) |

| Field | Value |
|-------|-------|
| **What** | Delete 2 Windows-path scripts from `scripts/` |
| **Why** | Hardcoded Windows paths make them non-portable; `tests/analyze_dump.py` is the maintained cross-platform version |
| **Risk** | 🟡 Medium — verify no pipeline script references these before deleting |
| **Rollback** | `git checkout HEAD~1 -- scripts/analyze_dump.py scripts/analyze_framebuffer.py` |

```bash
git rm scripts/analyze_dump.py scripts/analyze_framebuffer.py
git commit -m "phase2: delete Windows-path scripts (analyze_dump.py, analyze_framebuffer.py)"
```

---

## Phase 3 — Documentation Consolidation (Risk: Medium)

Merge overlapping documents and rewrite stale docs for current workflows.

---

### 3.1 Merge quality docs: `HD_QUALITY_ANALYSIS.md` + `PLAN_QUALITY_FIX.md`

| Field | Value |
|-------|-------|
| **What** | Create a consolidated `docs/HD_QUALITY_REPORT.md` combining both documents; archive originals to `docs/archive/` |
| **Why** | DOCS_INDEX.md shows both as "Merge" status. `HD_QUALITY_ANALYSIS.md` (158 lines) investigates the problem; `PLAN_QUALITY_FIX.md` (78 lines) proposes the solution. They overlap significantly (AUDIT_SUMMARY.md §3.1) |
| **Risk** | 🟡 Medium — if anyone links directly to either file, the link breaks. The archive preserves originals |
| **Rollback** | `git mv docs/archive/HD_QUALITY_ANALYSIS.md docs/ && git mv docs/archive/PLAN_QUALITY_FIX.md docs/ && git rm docs/HD_QUALITY_REPORT.md` |

```bash
# Create consolidated document
# (write new docs/HD_QUALITY_REPORT.md combining both analyses)

# Archive originals
git mv docs/HD_QUALITY_ANALYSIS.md docs/archive/HD_QUALITY_ANALYSIS.md
git mv docs/PLAN_QUALITY_FIX.md docs/archive/PLAN_QUALITY_FIX.md

git commit -m "phase3: merge HD_QUALITY_ANALYSIS.md + PLAN_QUALITY_FIX.md into HD_QUALITY_REPORT.md"
```

---

### 3.2 Rewrite `AGENTS.md` → `HANDSOFF.md`

| Field | Value |
|-------|-------|
| **What** | Create `docs/HANDSOFF.md` with current Linux/repo-based workflow context; archive `docs/AGENTS.md` to `docs/archive/` |
| **Why** | AUDIT_SUMMARY.md §2.1: `AGENTS.md` is "Windows-only handoff doc (Git Bash, `Z:\\` paths, Windows Python). Replace or rewrite for Linux." The original is stale for the current Linux-based workflow |
| **Risk** | 🟡 Medium — AGENTS.md was the AI handoff doc; after rewrite, agents should read HANDSOFF.md instead |
| **Rollback** | `git mv docs/archive/AGENTS.md docs/ && git rm docs/HANDSOFF.md` |

```bash
# Write new HANDSOFF.md with current Linux/repo context
# (new file at docs/HANDSOFF.md)

# Archive original
git mv docs/AGENTS.md docs/archive/AGENTS.md

git commit -m "phase3: rewrite AGENTS.md→HANDSOFF.md for Linux workflow"
```

---

### 3.3 Rewrite `PLAN.md` → `ROADMAP.md`

| Field | Value |
|-------|-------|
| **What** | Create `docs/ROADMAP.md` with forward-looking project roadmap; archive `docs/PLAN.md` to `docs/archive/` |
| **Why** | AUDIT_SUMMARY.md §2.1: `PLAN.md` is "original project plan from Windows era. Current project uses ROADMAP.md-style tracking. Replace with ROADMAP.md." |
| **Risk** | 🟡 Medium — PLAN.md is linked from DOCS_INDEX.md; update the index after this change |
| **Rollback** | `git mv docs/archive/PLAN.md docs/ && git rm docs/ROADMAP.md` |

```bash
# Write new ROADMAP.md
# (new file at docs/ROADMAP.md)

# Archive original
git mv docs/PLAN.md docs/archive/PLAN.md

git commit -m "phase3: rewrite PLAN.md→ROADMAP.md with forward-looking roadmap"
```

---

## Phase 4 — Future / Nice-to-Have (Risk: Low–Medium)

Optional improvements that can be deferred. These are independently useful
but not blocking for the restructuring.

---

### 4.1 Update `.gitignore` and clean build artifacts

| Field | Value |
|-------|-------|
| **What** | Add `*.o`, `*.d`, `__pycache__/`, `*.pyc` to `.gitignore`; optionally remove any tracked build artifacts |
| **Why** | AUDIT_SUMMARY.md §3.5: "Compiled `.o` and `.d` files from the ScummVM fork build are present in the tree (~400+ object files). These should be gitignored or cleaned" |
| **Risk** | 🟢 Low — gitignore changes are additive; removing tracked .o files is a larger operation |
| **Rollback** | `git checkout HEAD~1 -- .gitignore` |

```bash
# Add to .gitignore:
# *.o
# *.d
# *.pyc
# __pycache__/

# To remove already-tracked build artifacts (careful, this affects scummvm/fork/):
# git rm --cached scummvm/fork/**/*.o scummvm/fork/**/*.d

git commit -m "phase4: update .gitignore for build artifacts"
```

---

### 4.2 Consolidate log parsers: `diagnose.py` ↔ `hd_diagnose.py`

| Field | Value |
|-------|-------|
| **What** | Unify `scripts/diagnose.py` and `scripts/hd_diagnose.py` into a single tool with `--json` / `--table` flags |
| **Why** | SCRIPT_INVENTORY.md §3.2: "Nearly the same thing — parse ScummVM HD debug logs. Unify into a single `diagnose.py` with `--json` / `--table` flags." |
| **Risk** | 🟡 Medium — both scripts may have unique features; ensure combined version covers all use cases |
| **Rollback** | `git checkout HEAD~1 -- scripts/diagnose.py scripts/hd_diagnose.py` |

---

### 4.3 Archive historical pipeline scripts

| Field | Value |
|-------|-------|
| **What** | Move `scripts/full_pipeline.sh` and `scripts/setup_build_env.sh` to `scripts/archive/` |
| **Why** | SCRIPT_INVENTORY.md §2.3: `full_pipeline.sh` is "superseded by `setup.py` w/ `setup_wizard/`"; `setup_build_env.sh` is "MSYS2-only, not applicable to Linux build" |
| **Risk** | 🟢 Low — `git mv` preserves history; active workflows use `setup.py` and `setup.sh` |
| **Rollback** | `git mv scripts/archive/full_pipeline.sh scripts/ && git mv scripts/archive/setup_build_env.sh scripts/` |

```bash
mkdir -p scripts/archive
git mv scripts/full_pipeline.sh scripts/archive/full_pipeline.sh
git mv scripts/setup_build_env.sh scripts/archive/setup_build_env.sh
git commit -m "phase4: archive historical pipeline scripts (full_pipeline, setup_build_env)"
```

---

### 4.4 Update `DOCS_INDEX.md` after all changes

| Field | Value |
|-------|-------|
| **What** | Update `docs/DOCS_INDEX.md` to reflect new paths (archived docs, renamed files, new files) and updated status fields |
| **Why** | DOCS_INDEX.md is the "single source of truth" for navigation — it must accurately reflect the post-restructure layout |
| **Risk** | 🟢 Low — documentation-only change |
| **Rollback** | `git checkout HEAD~1 -- docs/DOCS_INDEX.md` |

---

## Summary: All Operations

| Phase | # | Operation | Risk | Type |
|-------|---|-----------|------|------|
| **0** | 0.1 | Remove `setup_wizard/steps/__init__.py` | ⚪ Very Low | Delete |
| **0** | 0.2 | Remove `tests/test_room_debug.cpp` | ⚪ Very Low | Delete |
| **0** | 0.3 | Remove `add_object_alpha.py` v1–v3 | ⚪ Very Low | Delete |
| **0** | 0.4 | Remove `demo_upscale.py`, `demo_upscale_stage.py` | ⚪ Very Low | Delete |
| **0** | 0.5 | Remove `config/paths.yaml` | ⚪ Very Low | Delete |
| **1** | 1.1 | Create `docs/archive/` | 🟢 Low | Create dir |
| **1** | 1.2 | Archive `INDEX.md`, `PATH_A_ANALYSIS.md`, `HD_COSTUME_PLAN.md`, `RESEARCH.md` | 🟢 Low | `git mv` |
| **2** | 2.1 | Consolidate `add_object_alpha` v4–v6 | 🟡 Medium | Edit + Delete |
| **2** | 2.2 | Remove room-specific scripts (3 files) | 🟢 Low | Delete |
| **2** | 2.3 | Remove Windows-path scripts (2 files) | 🟡 Medium | Delete |
| **3** | 3.1 | Merge `HD_QUALITY_ANALYSIS.md` + `PLAN_QUALITY_FIX.md` | 🟡 Medium | Create + Archive |
| **3** | 3.2 | Rewrite `AGENTS.md` → `HANDSOFF.md` | 🟡 Medium | Create + Archive |
| **3** | 3.3 | Rewrite `PLAN.md` → `ROADMAP.md` | 🟡 Medium | Create + Archive |
| **4** | 4.1 | Update `.gitignore` for build artifacts | 🟢 Low | Edit |
| **4** | 4.2 | Consolidate `diagnose.py` / `hd_diagnose.py` | 🟡 Medium | Edit + Archive |
| **4** | 4.3 | Archive `full_pipeline.sh`, `setup_build_env.sh` | 🟢 Low | `git mv` |
| **4** | 4.4 | Update `DOCS_INDEX.md` | 🟢 Low | Edit |

---

## Files That Are NOT Changed

| Area | Reason |
|------|--------|
| **`scummvm/fork/`** | Full ScummVM source tree — not touched per explicit instruction |
| **`scummvm/patches/`** | Reference patches adjacent to fork — already in place, no changes proposed |
| **`config/hd_manifest.json`** | Active runtime config — keep |
| **`config/object_map.json`** | Active runtime config — keep |
| **`config/upscale/`** | Active shell scripts — keep (except updating caller in 2.1) |
| **`setup_wizard/`** (except `steps/__init__.py`) | Active Python package — keep |
| **`tests/`** (except `test_room_debug.cpp`) | Active test infrastructure — keep |
| **`README.md`** | Project overview — keep |
| **`setup.py`, `setup.sh`** | Entry points — keep |
| **Active docs** (`BUILD.md`, `STRUCTURE.md`, `TECHNICAL_REPORT.md`, `STATUS.md`, `FORK_PLAN.md`, `HD_MANIFEST_SPEC.md`) | Current reference docs — may be kept or moved per Phase 1 discussion |

---

## Testing After Each Phase

After each phase, verify:

```
# Check branch is still repo-organization
git branch --show-current

# No uncommitted changes
git status --short

# Files exist where expected / don't exist where deleted
ls -la docs/archive/  # after Phase 1
ls -la scripts/       # after Phase 2 deletions

# Build still works (if build environment is available)
# cd scummvm/fork && make -j$(nproc) 2>&1 | tail -5
```
