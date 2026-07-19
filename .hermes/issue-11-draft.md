## Performance Analysis: renderHDComposite() — 7 Bottlenecks

After a thorough code review of `renderHDComposite()` in `gfx.cpp`, here are the identified performance bottlenecks, ranked by impact.

---

### #1 (HIGH): Full HD Composite Rebuild (Step 2 — `gfx.cpp:1308-1359`)

**Location:** `gfx.cpp:1308-1359` — the 8-bit pixel scan loop

**Problem:** Every frame, the code iterates over **every pixel** of the HD composite buffer (typically 1920×1080 = 2,073,600 pixels). For each pixel it:
1. Maps the HD coordinate back to 8-bit coordinate (via precomputed lookup table)
2. Reads the 8-bit pixel from `_virtscr[kMainVirtScreen]`
3. Checks against the clean background (`_hdCleanValid[]` + `_hdCleanBackground`)
4. Skips palette index 255 (transparent)
5. Looks up the palette RGB
6. Writes RGBA to `_hdComposite`

**Cost:** ~2M iterations × 60 FPS = **120 million pixel checks per second**
**No dirty rect optimization** — the entire HD surface is rebuilt from scratch every frame, even when nothing changes.

**Suggested fix:** Integrate with ScummVM's existing dirty rect system (`_activeDirtyRects`, `_markAllDirty`). Only re-composite HD pixels for regions that are actually dirty in the 8-bit engine.

---

### #2 (HIGH): Per-Object Pixel Diff Scan (Step 2.5 — `gfx.cpp:1529-1541`)

**Location:** `gfx.cpp:1529-1541` — visible pixel counting inside the FLOBJ loop

**Problem:** For each FLOBJ (floating object), the code scans **every pixel** of the object's bounding box to count visible foreground pixels. This determines whether the HD texture passes culling.

- Object 114 (inventory background): 640 × 472 = **302,080 pixel checks** per frame
- When the inventory is open with 50+ item slots: potentially 400K+ checks total
- Inner loop per pixel: position math, `_hdCleanValid[]` check, 8-bit pixel read, clean pixel read, comparison

**Cost:** Potentially 300K+ iterations per frame just for culling.

**Suggested fix:** Implement sparse/strided sampling — instead of checking every pixel, check every Nth pixel (e.g., every 4th row/column). This would reduce the scan to ~6% of current cost while maintaining reliable culling accuracy.

---

### #3 (MEDIUM): HD Alpha Mask Allocation (`gfx.cpp:1404`)

**Location:** `gfx.cpp:1404` — `byte *hdAlphaMask = (byte *)calloc(hdW * hdH, 1);`

**Problem:** Every frame allocates, zero-fills, and later frees a 2+ MB byte buffer for the alpha mask. This is used to track which pixels have been touched by HD objects/costumes to prevent Step 2.6b from overwriting them.

```
calloc(1920 * 1080, 1) = 2,073,600 bytes per frame
→ ~124 MB/s memory allocation at 60 FPS
```

**Suggested fix:** Pool-reuse the mask buffer across frames. Only reallocate if resolution changes. `memset` is cheaper than `calloc` (no page fault overhead).

---

### #4 (MEDIUM): Full Frame `copyRectToScreen` (Step 3 — `gfx.cpp:2079-2086`)

**Location:** `gfx.cpp:2084` — `_system->copyRectToScreen()`

**Problem:** The **entire** HD composite buffer (1920×1080 × 4 bytes = ~8 MB) is copied to the display subsystem every frame, regardless of how much actually changed.

```
1920 × 1080 × 4 = 8,294,400 bytes per frame
→ ~480 MB/s framebuffer copy at 60 FPS
```

**Suggested fix:** Track dirty rectangles during composite and only copy changed regions. Alternatively, use SDL2 textures with streaming access to avoid the extra copy.

---

### #5 (LOW): HD Debug Log File I/O (`gfx.cpp:2096-2109`)

**Location:** `gfx.cpp:2100-2106` — `hd_state.log` write

**Problem:** Every frame, the debug buffer is flushed to disk via `fopen()` + `fwrite()` + `fclose()`. This means **60 file open/close operations per second**, even when the buffer is empty (the emptiness check still runs).

**Suggested fix:** 
- Keep the `FILE*` handle open for the session lifetime (close on exit)
- Skip the entire block if `_hdDebugLog` is empty and no debug flags are set

---

### #6 (LOW): Cache Pruning — O(n²) (hd_object_manager.cpp:293-305)

**Location:** `hd_object_manager.cpp:293-305` — `pruneCache()`

**Problem:** `pruneCache()` removes one entry at a time by scanning ALL entries to find the oldest (`lastUsed`). If N entries need removal, this is O(n²). It's called on every cache miss.

**Suggested fix:** Convert to a batch approach: scan once to find the N oldest entries, remove them all. Or better, use a `std::priority_queue` or `std::multimap` keyed by `lastUsed` for O(log n) removal.

---

### #7 (LOW): HD Verification / Debug Code in Hot Path (`gfx.cpp:1649-1684`)

**Location:** `gfx.cpp:1649-1684` — per-object verification block

**Problem:** For every object that passes culling, a verification block runs that:
1. Computes expected HD texture size from 8-bit dimensions
2. Builds a color histogram by sampling pixels
3. Checks if textures landed in the correct screen position via random sampling
4. Prints detailed debug output

This appears to be development/debug code that was never guarded with `#ifdef DEBUG` or removed.

**Suggested fix:** Wrap in `#ifndef NDEBUG` or gate behind a runtime flag (`_hdVerifyEnabled`).

---

### Current Impact

Without profiling data added to the engine, it's hard to measure exact frame times. The total per-frame cost of `renderHDComposite()` is roughly:

```
Step 2 (full pixel scan):  ~8-15ms  (depends on HD resolution)
Step 2.5 (FLOBJ culling):  ~2-5ms   (depends on number + size of objects)
Step 2.5 (HD blit):        ~1-3ms   (depends on number of unculled objects)
Step 2.6 (costumes):       ~1-3ms
Step 3 (copyRectToScreen): ~2-4ms   (varies by driver/backend)
Alpha mask alloc:          ~0.5-1ms
Debug overhead:            ~0.2-0.5ms

Total estimate:            ~15-32ms per frame
```

For 60 FPS target (16.6ms budget), the worst case already overshoots by 2×. For high-resolution displays (4K → 3840×2160 = 4× more pixels), the problem scales linearly.

### Priority Recommendations for Optimization

1. **Add frame profiling** — measure actual hot spots before optimizing
2. **Dirty rect compositing** — biggest single win, potentially 10-100× reduction in Step 2 cost
3. **Sparse pixel sampling** for culling — 10-20× reduction in Step 2.5 culling cost
4. **Alpha mask pool reuse** — eliminates allocation overhead
5. **Remove/guard debug/verification code**
