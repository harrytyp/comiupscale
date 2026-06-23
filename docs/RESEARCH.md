# Research Findings: Existing Solutions for SCUMM V8 HD Upscaling

After extensive research across GitHub, here's what exists.

---

## 1. MMUCS (haywirephoenix/MMUCS) — ⭐ Actively Developed ⚡

**This is the most relevant finding by far.**

**URL:** https://github.com/haywirephoenix/MMUCS  
**Status:** v0.3.0 released 8 hours ago (pre-release), 61 commits, actively developed  
**License:** PolyForm Noncommercial 1.0.0  
**Platform:** Godot Engine with C# scripts  

### What it is

MMUCS (Modular Media Unpacker Content Studio) is a **Godot-powered SCUMM V8
content explorer and visualizer** — built specifically for modding **The Curse
of Monkey Island** (COMI).

> From the README: *"I originally built MMUCS to aid my own pursuit of modding
> The Curse of Monkey Island (COMI), with the ultimate goal of creating extended
> background art and higher-resolution sprites."*

### What Already Works (v0.3.0)

| Feature | Status |
|---------|--------|
| Load LA0/LA1/LA2 archives | ✅ Working |
| Browse resource block hierarchy | ✅ Working |
| View room backgrounds (SMAP) | ✅ Working |
| View objects (OBIM with SMAP/BOMP) | ✅ Working (v0.2.0+) |
| AKOS animation viewer + cel cache | ✅ Working |
| Indexed palette rendering pipeline | ✅ Working |
| Zoomable viewports | ✅ Working |
| Hex viewer & metadata panel | ✅ Working |
| Floating/docking UI system | ✅ Working |
| Dynamic theming | ✅ Working |

### Planned / TODO

| Feature | Status |
|---------|--------|
| Export functionality | ⏳ "decoding is done" — just needs UI |
| SCUMM Runner (full game engine) | ⏳ Planned |
| Script decoder | ⏳ Planned |
| AKOS animations playable | ⏳ "instructions are decoded" |
| Hotspot display in Room panel | ⏳ Planned |

### Why This Matters for Our Project

MMUCS already does what we need:
1. **Reads LA files** and renders rooms, objects, AKOS animations
2. **Specifically targets COMI** (SCUMM V8)
3. **Uses Godot** — a modern engine that renders at any resolution natively
4. **Has indexed rendering** — correct palette display, no color issues
5. **Is actively developed** (v0.1.0 → v0.3.0 in one week!)

**The game-changer:** Since MMUCS is a Godot application (not ScummVM), it
renders everything through a modern graphics pipeline. There are NO hardcoded
room dimensions, NO walkbox coordinate problems, NO script coordinate issues.
Loading our upscaled 4x textures would just work at native resolution.

### Prebuilt Binaries Available

Release v0.3.0 ships 4 platform assets (Windows, macOS, Linux). Can be
downloaded from the releases page.

---

## 2. NUTcracker (BLooperZ/nutcracker) — ★62 stars

This is the tool we're already using. Key findings from its issues:

**AKOS Support Issue (#13):** The AKOS decoder was added in Oct 2022 specifically
for a "remaster" project. The issue author "haywirephoenix" (same person behind
MMUCS) was doing exactly what we're doing — extracting AKOS costumes for
upscaling. Key details:
- AKOS had color palette issues (red channel used for transparency)
- Some AKOS frames triggered an assertion error (removed assert from `akos.py`)
- The developer (BLooperZ) acknowledged AKOS was "in development"
- The issue is **closed as completed** — so the decoder is now stable

**NUTcracker's `sputm room encode` + `sputm build`** is the reimport pipeline
we've already documented, and there is NO built-in coordinate scaling.

---

## 3. No ScummVM HD Texture Fork Exists

I searched extensively for:
- ScummVM forks with HD texture replacement support
- ScummVM issues about texture upscaling
- Any GitHub repos doing SCUMM game HD modding

**Result: No public ScummVM fork supports HD asset replacement.** The ScummVM
engine reads resources in the original format and there's no mechanism for
loading higher-resolution replacements.

The only realistic paths for HD COMI are:
1. **Patch original game files** (our approach — needs coordinate scaling)
2. **Use MMUCS** (Godot replacement — no coordinate issues, but not a complete game yet)
3. **Modify ScummVM C++ source** (engine fork — complex but could be complete)

---

## 4. Other Related Projects

| Project | Creator | Relevance |
|---------|---------|-----------|
| **haywirephoenix/nutcracker issues** | haywirephoenix | Requested AKOS support specifically for COMI upscaling |
| **ScummRev** | haywirephoenix | AKOS viewer predecessor (mentioned in nutcracker issue) |
| **AkosView** | Unknown | Legacy AKOS viewer (mentioned in nutcracker issue) |
| **scumm-8** (Liquidream) | PICO-8 demake | Not relevant to upscaling |

---

## Implications for Our Project

1. **MMUCS is the most promising path forward** — it's a Godot-based SCUMM V8
   viewer/runner built specifically for COMI modding. It can already render rooms
   and AKOS animations at any resolution. With export functionality coming, it
   might be the ideal platform for an HD remaster.

2. **No coordinate-patching shortcuts exist** for native ScummVM — we'd be
   writing the first SCUMM V8 coordinate scaler ourselves.

3. **NUTcracker + MMUCS together** could be the complete pipeline:
   - NUTcracker: Extract assets → upscale → re-encode
   - MMUCS: Render upscaled assets at 4x without coordinate issues
   - Alternatively: MMUCS might eventually support loading external HD textures

4. **The developer (haywirephoenix) is working on the same problem** and is
   actively releasing updates. Following/collaborating with them could save
   months of work.

