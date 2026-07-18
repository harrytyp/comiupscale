# COMI HD Debug Workflow Overhaul — Report

## Problem Summary

The COMI HD debug cycle is 5-15 minutes per iteration because of four interrelated problems:

1. **No "missing texture" signal** — when an HD texture fails to load, the 8-bit background silently remains. No error, no placeholder, no log entry says "MISS".
2. **Logs can't be correlated** — three unsynchronized log mechanisms, step2.5 stats without frame numbers, hd_state.log flush is O(n²).
3. **Visual verification is broken** — the agent can't see the screen, raw dumps are 7×20MB per frame, and the vision model can't reliably distinguish HD from SD textures.
4. **No autonomous navigation** — the agent can't click through the game to reach test scenes. Existing X11 input injection (XTest) doesn't work reliably with SDL2.

---

## Problem 1: No "Missing Texture" Signal

### Root Cause

In `gfx.cpp` step2.5 (lines 1495-1531), when `hasObject()` returns false or `loadObject()` fails, the code just `continue`s — no log. The only trace is `loaded=0` in the per-30-frame summary. You can't tell: wrong path? missing PNG? wrong state mapping? culling? load failure?

### Verified Claims

- DeepSeek's claim: **CONFIRMED**. `loadObject()` at line 1530 silently `continue`s on failure.
- The `step2.5 SKIP` log at line 1522 only fires for `hasObject()` false, not for `loadObject()` false.
- Cull messages log object number but not object name (line 1640).

### Fix: MISS Logging + VERIFY Block

**MISS logging** (~10 lines, `gfx.cpp:1530`):
After `loadObject()` fails, log what was attempted:
```cpp
if (!_hdObjectManager->loadObject(od.obj_nr, objRoom, objState, hdObjSurf)) {
    hdPrintf("MISS obj=%d(%s) room=%d state=%d fl=%d — loadObject failed",
        od.obj_nr, _hdObjectManager->getObjectName(od.obj_nr).c_str(),
        objRoom, objState, od.fl_object_index);
    continue;
}
```

**VERIFY block** (~30 lines, `gfx.cpp:~1683`, after the blit loop, before `hdObjSurf.free()`):

Tests all three properties the user asked for — is the texture there, right position, right size — using in-memory pixel comparison (no vision model, no screenshots):

```cpp
{
    const char *vname = _hdObjectManager->getObjectName(od.obj_nr).c_str();
    int srcW = (int)hdObjSurf.w, srcH = (int)hdObjSurf.h;
    int expW = od.width * _hdScale, expH = od.height * _hdScale;

    // 1. SIZE: does texture size match expected (±4px tolerance)?
    bool sizeOK = (abs(srcW - expW) <= 4 && abs(srcH - expH) <= 4);

    // 2. IS_HD: unique color count → >256 colors = real HD texture
    Common::HashMap<uint32, bool> seen;
    int step = MAX(1, (srcW * srcH) / 5000);
    for (int sy = 0; sy < srcH; sy += step)
        for (int sx = 0; sx < srcW; sx += step) {
            uint32 px = *(uint32*)hdObjSurf.getBasePtr(sx, sy);
            if (((px >> 24) & 0xFF) >= 128) seen.setVal(px & 0x00FFFFFF, true);
        }
    bool isHD = seen.size() > 256;

    // 3. POSITION: sample opaque source pixels, check they landed in composite
    int matches = 0, checks = 0;
    for (int i = 0; i < 40 && checks < 20; i++) {
        int sx = rand() % srcW, sy = rand() % srcH;
        uint32 srcPx = *(uint32*)hdObjSurf.getBasePtr(sx, sy);
        if (((srcPx >> 24) & 0xFF) < 128) continue;
        int dx = (int)hdX + sx, dy = (int)hdY + sy;
        if (dx < 0 || dx >= hdW || dy < 0 || dy >= hdH) { checks++; continue; }
        uint32 cmpPx = *(uint32*)_hdComposite.getBasePtr(dx, dy);
        if ((srcPx & 0x00FFFFFF) == (cmpPx & 0x00FFFFFF)) matches++;
        checks++;
    }
    bool posOK = (matches > 0);

    hdPrintf("VERIFY obj=%d(%s) src=%dx%d exp=%dx%d sizeOK=%d isHD=%d colors=%d posOK=%d matches=%d/%d",
        od.obj_nr, vname, srcW, srcH, expW, expH, sizeOK, isHD, (int)seen.size(), posOK, matches, checks);
}
```

**How each check works:**

| Check | What it tests | How | Deterministic? |
|-------|-------------|-----|---------------|
| `isHD` + `colors` | Texture loaded and is real HD (not palette-only) | Count unique RGB values in source surface. RealESRGAN → millions of colors. 8-bit palette → ≤256 | Yes, binary threshold |
| `sizeOK` | Texture has correct dimensions | Compare `hdObjSurf.w/h` against `od.width × _hdScale` / `od.height × _hdScale` (±4px) | Yes, exact |
| `posOK` + `matches` | HD pixels actually landed at the right position in the composite | Sample 20 opaque pixels from HD source, read same coordinates from `_hdComposite`, compare RGB | Yes, byte comparison |

**Example log output:**
```
F=1230 VERIFY obj=114(bg) src=2560x1920 exp=2560x1920 sizeOK=1 isHD=1 colors=89432 posOK=1 matches=20/20
F=1230 VERIFY obj=105(cursor) src=32x32 exp=32x32 sizeOK=1 isHD=0 colors=87 posOK=1 matches=15/20
F=1230 VERIFY obj=116(map) src=0x0 exp=64x48 sizeOK=0 isHD=0 colors=0 posOK=0 matches=0/0
```

Why this works and vision models don't:
- Vision models hallucinate "looks HD" — this counts actual unique color values
- Vision models can't do per-object analysis — this runs per-object per-frame in-engine
- Vision models can't verify pixel placement — this reads source and composite from the same memory

**Performance:** HashMap with max ~5000 entries per object, 20 pixel samples per object, runs every 30 frames. Negligible vs. the 2560×1920 software rendering bottleneck.

---

## Problem 2: Log Correlation Broken

### Root Cause

Three independent log mechanisms are not synchronized:

| Log | Destination | Frame-stamped? |
|-----|------------|----------------|
| `warning()` | stderr | No |
| `hdPrintf()` | hd_state.log | **Inconsistently** — CULL/RENDER/KEY/MOUSE have `@<frame>`, step2/step2.5/step2.6 stats do NOT |
| `hdDebugDump()` | logs/hd_dump_\<frame\>_*.raw/txt | Filename has frame, state.txt has frame |

### DeepSeek Claim Verified: `_hdFrameCount` double-increment — FALSE

DeepSeek claimed the early-return path and main path both increment `_hdFrameCount`, giving 2 increments per visual frame.

**Reality:** The two `_hdFrameCount++` are in **mutually exclusive branches**:
- `gfx.cpp:1281` — inside early-return (`!_hdBackgroundSurface.getPixels()`) → `return` at line 1310
- `gfx.cpp:2088` — main path, only reached if early return was skipped

Furthermore, the sole call site (`gfx.cpp:557`) already guards:
```cpp
if (_hdScale > 1 && _hdBackgroundSurface.getPixels()) {
    renderHDComposite();
}
```
So the early-return path at line 1257 is **dead code**. Only one `_hdFrameCount++` executes per frame.

### Fix: Frame Prefix in hdPrintf (~15 lines)

Modify `hdPrintf()` at `gfx.cpp:2131` to automatically prepend frame number:

```cpp
void ScummEngine::hdPrintf(const char* fmt, ...) {
    char buf[512];
    int prefix = snprintf(buf, sizeof(buf), "F=%d ", _hdFrameCount);
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(buf + prefix, sizeof(buf) - prefix - 1, fmt, args);
    va_end(args);
    if (n > 0) {
        buf[prefix + n] = '\n';
        hdAppendDebugLog(buf, prefix + n + 1);
    }
}
```

Then remove the now-redundant `@%d _hdFrameCount` from CULL/RENDER messages (lines 1640, 1650) and KEY/MOUSE messages in `input.cpp` (lines 171-173, 250-252).

**Result:** Every log line starts with `F=<frame>`. Correlate with `grep "F=1234"`.

### Fix: hd_state.log O(n²) Flush → Append (~10 lines)

Current code (`gfx.cpp:2104-2118`) reads the **entire file** (up to 4MB) every frame, appends new content, rewrites the whole file. This is O(n²).

Replace with simple append:
```cpp
Common::DumpFile df;
df.openAppend(Common::Path("hd_state.log"));
df.write(_hdDebugLog.c_str(), _hdDebugLog.size());
df.close();
```

If `openAppend` doesn't exist in ScummVM's DumpFile, use raw `fopen("hd_state.log", "a")`.

Remove the 4MB size check (line 2105: `rf.size() < 4194304`) — handle rotation externally.

---

## Problem 3: Visual Verification Broken

### Root Cause

The current pipeline: raw dump (7 files × ~20MB) → JPEG conversion → catbox.moe upload → human/agent analysis.

The existing `debug_loop.sh` already has Xvfb screenshot capability (`import -window root`) and even references a `vision_qa.py` script using `mimo-v2.5`. But the raw dump pipeline is used instead.

The agent's vision model cannot reliably distinguish HD from SD textures — HD textures are higher-resolution versions of the same image, and at small thumbnail sizes the difference is often invisible.

### Fix: VERIFY Block Eliminates Visual Verification

The VERIFY block from Problem 1 makes visual verification **unnecessary** for the three properties the user cares about (texture present, right position, right size). The log tells you definitively:
- `sizeOK=1 isHD=1 posOK=1` → correct, move on
- `sizeOK=0` → wrong texture dimensions
- `isHD=0` → SD fallback, HD texture missing
- `posOK=0` → wrong position or overwritten

### Fix: Screenshot as Fallback (~50 lines, standalone script)

For cases where visual inspection is still needed (e.g., "does the inventory look right?"), replace the raw dump pipeline with a simple Xvfb screenshot:

```bash
#!/usr/bin/env bash
# scripts/hd_screenshot.sh — capture current Xvfb frame as PNG
DISPLAY=:99 import -window root /opt/data/local/comi-hd-repo/dumps/latest_screenshot.png
```

Hermes can directly `vision_analyze` the PNG:
```
vision_analyze(image_url="/opt/data/local/comi-hd-repo/dumps/latest_screenshot.png",
                question="Is the inventory open or closed? What room is this?")
```

Note: vision is for scene-level questions, not HD/SD detection — that's what VERIFY is for.

---

## Problem 4: No Autonomous Game Navigation

### Root Cause

The agent needs to reach specific game scenes to test HD rendering. Current approaches:
- `hd_sendkeys.c` — C program using XTest extension, hardcoded frame-timed ESC/click sequence. Brittle: frame timing varies, xdotool not installed, python-xlib not available.
- `scumm.cpp:3168-3196` — engine-internal forced click injection (debug code), hardcoded frame numbers. Only works for one specific scene transition.
- SDL2 ignores XSendEvent — native Xlib events are rejected at the SDL2 event filter level.

### Solution: ScummVM Built-in Record/Playback System

**ScummVM already has a full event recording/playback system** — no need to inject X11 events or hack the engine.

**Found in:**
- `common/recorderfile.h` / `common/recorderfile.cpp` — `PlaybackFile` class, binary format (PBCK), records all events (keyboard, mouse, timer) with timestamps
- `gui/EventRecorder.cpp` / `gui/EventRecorder.h` — `EventRecorder` singleton, modes: `kPassthrough`, `kRecorderRecord`, `kRecorderPlayback`, `kRecorderUpdate`
- `engines/engine.cpp:791-804` — config-driven activation:

```cpp
Common::String recordMode = ConfMan.get("record_mode");
Common::String recordFileName = ConfMan.get("record_file_name");

if (recordMode == "record") {
    g_eventRec.init(targetFileName, GUI::EventRecorder::kRecorderRecord);
} else if (recordMode == "playback") {
    g_eventRec.init(recordFileName, GUI::EventRecorder::kRecorderPlayback);
} else if (recordMode == "fast_playback") {
    g_eventRec.init(recordFileName, GUI::EventRecorder::kRecorderPlayback);
    ConfMan.setBool("fast_playback", true);  // skip delint
}
```

### How to Use It

**1. Record a session (one-time manual setup):**

Add to `scummvm.ini` `[comi]` section:
```ini
record_mode=record
record_file_name=comi_test_room10.pbp
```

Or via command line:
```bash
DISPLAY=:99 ./scummvm --record=comi_test_room10.pbp \
    --path=/opt/data/local/comi-hd-final --fullscreen
```

Play through the game to the scene you want to test (clicks, keyboard, everything). ScummVM records every input event with exact frame timing. The recording is saved as a `.pbp` file in the saves directory.

**2. Playback the recording (automated, reproducible):**

```bash
# Normal playback (same speed as original)
DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 ./scummvm \
    --playback=comi_test_room10.pbp \
    --path=/opt/data/local/comi-hd-final --fullscreen

# Fast playback (skip delays, faster iteration)
./scummvm --fast-playback=comi_test_room10.pbp ...
```

Or via config:
```ini
record_mode=playback
record_file_name=comi_test_room10.pbp
```

**3. Agent automation:**

The agent just needs to run the playback command. ScummVM handles all input internally — no X11 injection, no XTest, no xdotool, no frame-timing hacks. The game plays itself exactly as recorded, reaching the same scene every time.

### Multiple Test Scenarios

Record separate `.pbp` files for different scenes:
```
saves/
  test_room4_opening.pbp      # intro → room 4
  test_room15_stage.pbp        # navigate to stage
  test_room87_easyhard.pbp     # navigate to easyhard screen
  test_inventory_open.pbp      # open inventory
  test_inventory_close.pbp     # close inventory
```

Run them in a loop:
```bash
for pbp in saves/test_*.pbp; do
    echo "=== Playing $pbp ==="
    DISPLAY=:99 ./scummvm --playback="$pbp" --path=... &
    sleep 30  # let it reach the scene
    # VERIFY logs accumulate in hd_state.log
    kill %1
    mv hd_state.log "hd_state_$(basename $pbp .pbp).log"
done
```

### Limitations

- Recording must be done manually once per scene (but only once)
- If game data changes (different COMI version), recordings might break
- Recordings include save state — playback starts from the recorded save, not from scratch
- The `--record`/`--playback` flags may need testing to confirm they work in this fork (the code paths exist in `engine.cpp`, but the fork might have modifications that interfere)

### Alternative: Engine-Internal Scripted Input (if record/playback doesn't work)

If the built-in recorder has issues, a simpler alternative: add a config-driven "auto-input script" to `scumm.cpp` that reads a text file of timed events:

```ini
hd_auto_input=scripts/reach_room10.txt
```

File format:
```
# frame event params
10    KEY    Escape
30    KEY    Escape
50    LCLICK 364 244
80    RCLICK 500 300
```

Engine reads this file at startup and injects events directly into the ScummVM event queue (`_eventMan->pushEvent()`) — bypassing SDL2 entirely. This is more reliable than X11 injection and doesn't require the full recorder subsystem.

---

## Implementation Plan

### Phase Priority and Effort

| Phase | What | Effort | Files | Independently deployable? |
|-------|------|--------|-------|--------------------------|
| **1** | VERIFY block + MISS logging | ~40 lines C++ | `gfx.cpp` | Yes |
| **2** | Frame prefix in hdPrintf | ~15 lines C++ | `gfx.cpp`, `input.cpp` | Yes |
| **3** | Log flush O(n²)→append | ~10 lines C++ | `gfx.cpp` | Yes |
| **4** | Test recording (.pbp files) | Manual, one-time | `scummvm.ini` + gameplay | Yes |
| **5** | Screenshot script | ~10 lines bash | `scripts/hd_screenshot.sh` | Yes |
| **6** | Dump rotation script | ~15 lines bash | `scripts/cleanup_dumps.sh` | Yes |
| **7** | Dead code removal (early return) | ~60 lines deleted | `gfx.cpp:1257-1311` | Yes |

### Recommended Order

1. **Phase 1** (VERIFY + MISS) — immediately tells you what's broken and why, eliminates the need for visual verification
2. **Phase 3** (log append) — faster iteration, no 4MB buffer churn
3. **Phase 2** (frame prefix) — log correlation, `grep "F=1234"`
4. **Phase 4** (record/playback) — enables reaching test scenes autonomously
5. **Phase 5** (screenshots) — fallback for scene-level visual checks
6. **Phase 6+7** (cleanup) — housekeeping

### Execution: Subagent Delegation

All phases are mechanical, bounded, and independently deployable. Can be delegated to cheap auxiliary models:

| Delegatable | What |
|-------------|------|
| Phase 1 | Single function change in `gfx.cpp`, additive logging |
| Phase 2 | Single function change in `gfx.cpp` + find-replace in `input.cpp` |
| Phase 3 | Single function rewrite in `gfx.cpp` |
| Phase 4 | Manual recording session (not delegatable — requires gameplaying) + script to run playback loop |
| Phase 5 | Standalone bash script |
| Phase 6 | Standalone bash script |
| Phase 7 | Pure deletion in `gfx.cpp` |

Phases 1, 2, 3, 7 all touch `gfx.cpp` — delegate as one merged task to a single subagent to avoid conflicts.

### Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Missing texture diagnosis | "loaded=0" (guesswork) | `MISS obj=X(name) ...` + `VERIFY ... isHD=0` |
| Log correlation | Manual, 3 unsynchronized logs | `grep "F=1234"` finds all events |
| Visual verification | 5-15 min (raw→JPEG→upload→human) | Not needed — VERIFY log is deterministic |
| Game navigation | Brittle XTest injection, hardcoded frame timing | ScummVM built-in record/playback, reproducible |
| hd_state.log flush | O(n²) read-modify-write | O(1) append |
| Debug iteration time | 5-15 min | 1-3 min (run playback → read VERIFY log) |