## Performance Analysis — Full-Frame Cost of renderHDComposite()

### Background
The HD composite renderer runs every frame in `renderHDComposite()`. For COMI at default HD resolution (2560×1888, 4× 640×472), this processes millions of pixels per frame. This issue documents the verified performance hotspots.

---

## Verified Findings

### 1. 🔴 Step 2.6b — Full-Screen 4.8M Pixel Scan (Worst Offender)

**File:** `gfx.cpp`, lines 2067-2093

**What it does:** Iterates **every pixel** of the HD composite (2560×1888 = 4,833,280 pixels) to re-overlay 8-bit UI pixels on top of HD costume/object content.

```cpp
for (int dy = 0; dy < hdH; dy++) {       // 1888 iterations
    for (int dx = 0; dx < hdW; dx++) {    // 2560 iterations → 4.8M inner loops
        // Per-pixel:
        // 1. alpha mask lookup (hdAlphaMask)
        // 2. coordinate conversion (dy→sy, dx→sx via division)
        // 3. CLIP both converted coords
        // 4. actor BBox mask lookup
        // 5. cleanValid check
        // 6. 8-bit framebuffer pixel read (getBasePtr)
        // 7. clean background pixel read (getBasePtr)
        // 8. pixel comparison
        // 9. if dirty: palette lookup (3 reads) + composite write
```

**Verified:** There is NO dirty-rect or region-optimization. Every frame scans all 4.8M pixels regardless of how much of the screen actually changed.

At 60 FPS: ~290M pixel iterations/second.

---

### 2. 🟡 actorBBoxMask — calloc+free Every Frame

**File:** `gfx.cpp`, lines 2045-2094

**What it does:** Allocates a 302KB mask (640×472 bytes) on the heap every frame, iterates all actors to mark their bounding boxes, then frees it.

```cpp
byte *actorBBoxMask = (byte *)calloc(bboxMaskSize, 1);  // 302KB heap alloc + zero
for (int ai = 0; ai < _numActors; ai++) {                // ~20 actors
    // ... calculate bbox for each actor, mark in mask
    for (int y = ...) for (int x = ...)                  // ~1M marks total
        actorBBoxMask[y * visW + x] = 1;
}
// ...
free(actorBBoxMask);                                      // 302KB heap free
```

**Problems:**
- `calloc` + `free` on the heap **every frame** causes memory pressure and fragmentation
- Actor bounding boxes rarely change between frames — the mask could be cached and only invalidated when actors move or change visibility
- The bbox loop marks ~800K-1.5M pixels per frame (20 actors × ~200×200 average bbox)

---

### 3. 🟡 Texture Surface copyFrom per Frame (Both Step 2.5 and 2.5b)

**File:** `hd_object_manager.cpp`, lines 248-254

**What it does:** `loadObject()` uses an LRU texture cache, BUT on cache hit it does `dest.copyFrom(cacheEntry.surface)` which **allocates a new pixel buffer and copies all pixels**:

```cpp
// Cache hit:
if (cacheIt != _textureCache.end()) {
    dest.copyFrom(cacheIt->_value.surface);  // ← alloc+copy every frame!
    return true;
}
```

**Impact per object per frame:**
- Inventory background (obj=114): 2560×1888×4 = **19 MB** alloc + copy
- Inventory items (obj=117-274): ~320×224 = 287KB avg each
- Room objects: varies (up to full screen)

With 2-10 objects processed every frame: **30-100MB of alloc+copy+free per frame**.

Objects are freed immediately after rendering (`hdObjSurf.free()` in Step 2.5/2.5b, `hdCostumeSurf.free()` in Step 2.6).

---

### 4. 🟢 Step 2 (Background Copy) — Full-screen every frame when dirty

**File:** `gfx.cpp`, lines ~1270-1380

When `_fullRedraw` is true or during room transitions, Step 2 copies the entire 8-bit framebuffer to the HD composite (640×472 → 2560×1888). This is a simple nearest-neighbor upscale with palette expansion (8-bit → 32-bit RGBA).

Cost: ~4.8M pixel writes, but no alpha blending — just direct pixel copy.

---

## Estimated Cost per Frame

At 2560×1888 HD resolution, ~10 room objects, ~5 blast queue items, ~8 visible actors:

| Operation | Pixel Ops | Allocs | Notes |
|-----------|-----------|--------|-------|
| **Step 2.6b full scan** | **4.8M** | 1× calloc(302KB) | ALWAYS runs when clean valid |
| **Step 2.6b actor bbox build** | ~1M | — | Included in above loop |
| **Step 2.5 FLOBJ loop** | ~500K-2M | 10× surfaces | 1 copyFrom per object |
| **Step 2.5b Blast queue** | ~300K-2M | 2-10× surfaces | ~19MB for background alone |
| **Step 2.6 Costume render** | ~500K-2M | 8× surfaces | 1 per visible actor limb |
| **Step 2 (BG copy)** | 4.8M | — | Only on full redraw |
| **Step 3 (composite copy)** | 4.8M | — | copyRectToScreen |
| **Total (typical frame)** | **~12-18M pixels** | **~50-120 MB alloc/free** | |

At 30 FPS: **360-540 million pixel ops/sec**, **1.5-3.6 GB/sec alloc/free churn**.

---

## Viable Optimizations (prioritized)

### P1: Step 2.6b — Limit scan to changed regions (BIGGEST WIN)

**Current:** Full HD scan (4.8M pixels/frame)  
**Proposed:** Scan only 8-bit dirty rects × 4 scale

The ScummEngine already knows which screen areas changed. Instead of scanning every HD pixel, convert 8-bit dirty rects to HD coordinates and only scan those regions.

**Estimated improvement:** 10-100× reduction in Step 2.6b cost (depending on how much of the screen changes per frame).

---

### P2: Reuse actorBBoxMask across frames

**Current:** `calloc(302KB)` + build + `free` every frame  
**Proposed:** Static buffer, only rebuild when actors change

```cpp
static byte *actorBBoxMask = nullptr;
static int actorBBoxMaskSize = 0;
static int lastFrameMarked = -1;

if (lastFrameMarked != _hdFrameCount) {
    // Only re-mark if actors moved
    if (!actorBBoxMask || actorBBoxMaskSize < bboxMaskSize) {
        actorBBoxMask = (byte *)realloc(actorBBoxMask, bboxMaskSize);
        actorBBoxMaskSize = bboxMaskSize;
    }
    memset(actorBBoxMask, 0, bboxMaskSize);  // faster than calloc
    for (actors) { /* mark bbox */ }
    lastFrameMarked = _hdFrameCount;
}
```

**Track invalidation:** Add a `_hdActorDirty` flag set when any actor changes position, visibility, or costume. When not dirty, reuse existing mask.

**Estimated improvement:** Eliminates 302KB heap alloc/free + 1M bbox marks per frame for static scenes.

---

### P3: Avoid surface copyFrom — use cache reference directly

**Current:** Every frame: `dest.copyFrom(cacheEntry.surface)` → alloc + copy pixels → render → free  
**Proposed:** Return a `const Surface*` pointer from the cache, or use a shared reference-counted surface

```cpp
// Instead of: Graphics::Surface hdObjSurf; loadObject(... hdObjSurf);
// Use: const Graphics::Surface *hdObjSurf = cacheLookup(obj_nr);
if (hdObjSurf) {
    renderFromSurface(hdObjSurf, ...);  // read-only access
}
```

**Problem:** The rendering code currently modifies the destination composite but only reads from the source texture. A const reference would be sufficient.

**Estimated improvement:** Eliminates ~30-120MB of alloc+copy+freed per frame.

---

### P4: Step 2.6b — Pre-compute palette lookup table

**Current:** For every dirty pixel: `_currentPalette[curPix * 3 + 0/1/2]` (3 array lookups)  
**Proposed:** Pre-compute a lookup table `paletteToRGB32[256]` that maps 8-bit palette indices directly to 32-bit RGBA values. Update when palette changes.

**Estimated improvement:** Reduces 3 lookups + bit-shifts to 1 array access.

---

## Non-viable Optimizations (rejected after analysis)

### ~~Reuse HD surface between frames (no copy)~~
The `hdObjSurf` is a local variable that's modified/read and freed. Currently, each call to `loadObject()` returns the same cached data via `copyFrom`. Since the rendering code reads it without modifying it, we could return a const reference. **This IS viable** (moved to P3 above).

### ~~Skip Step 2.6b entirely when nothing changed~~
Step 2.6b is needed every frame because foreground objects (verbs, text, GDI elements) are re-drawn by the 8-bit engine every frame. However, a dirty-rect scan (P1) would naturally skip unchanged regions.

---

## Summary

The single biggest performance issue is **Step 2.6b's full-resolution scan** (P1), which processes 4.8M pixels every frame regardless of need. Combined with heap alloc/free churn from texture surfaces (P3) and the actor bbox mask (P2), these three optimizations together could reduce per-frame overhead by **~70-90%** for static scenes.

**Measurable impact:** Scenes with few actors/changes would see the most benefit (many rooms in COMI are mostly static with only 1-2 animated actors).
