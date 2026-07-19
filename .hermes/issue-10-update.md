## Update: Verified Root Cause + Implementation Plan

After in-depth code verification and a review by **GLM 5.2** (via Nvidia NIM), here is the verified root cause and a concrete, implementable fix.

---

### Root Cause (Verified ✅)

**Problem:** Inventory FLOBJs (obj_nr 105–274) are culled in `renderHDComposite()` because:

1. The SCUMP scripts draw inventory via `superBlastObject()` (opcode 119, `script_v8.cpp:1227`), which calls `enqueueObject()`.
2. `enqueueObject()` stores the **real screen position** in `_blastObjectQueue[]` (`object.cpp:1767`), **not** in `_objs[]`.
3. `_objs[].x_pos/_objs[].y_pos` remain at **(0,0)** for these objects.
4. `renderHDComposite()` at `gfx.cpp:1524-1525` reads `sx = od.x_pos; sy = od.y_pos` → **both 0**.
5. The pixel-diff scan at (0,0) finds **0 visible pixels** → `visiblePixels = 0`.
6. The FLOBJ inventory culling gate (`gfx.cpp:1577-1579`) culls because `0 < sw*sh/3`.

**Critical Timing Detail:** For V8, `removeBlastObjects()` (`object.cpp:1871`) is called **after** `renderHDComposite()` completes (`scumm.cpp:3220`). This means `_blastObjectQueue[]` is alive and valid when Step 2.5 runs.

---

### Verified Fix Points

#### 1. ✅ `USERSTATE_IFACE_INVENTORY` statt Pixel-Heuristik

**Location:** `scumm.h:236` — `USERSTATE_IFACE_INVENTORY = 0x40`
**Accessible from:** `ScummEngine::renderHDComposite()` via `_userState` (`scumm.h:1321`)

**Problem with current approach:** The `inventoryActive` flag is set by checking if cursor object (obj_nr=105) has visible pixels. But the FLOBJ loop iterates **in reverse order** (highest obj_nr first). Since cursor is 105 and inventory items are 117–274, items are processed **before** the cursor → they see `inventoryActive=false` (race condition).

**Fix:** Replace the pixel-scan heuristic with a direct state query:
```cpp
bool inventoryActive = (_userState & USERSTATE_IFACE_INVENTORY) != 0;
```
This is O(1), deterministic, and already used elsewhere (`verbs.cpp:350` — "Don't do anything unless the inventory is active").

**When inventory is OPEN:** All inventory FLOBJs that are on screen will have been drawn by scripts → positions are in the blast queue.
**When inventory is CLOSED:** No inventory FLOBJs will have been blasted → queue lookup returns nothing → items culled correctly.

---

#### 2. ✅ Persistent Position Cache via `superBlastObject()` Hook

**Why not direct queue lookup?** GLM 5.2 suggested scanning `_blastObjectQueue[]` directly from `renderHDComposite()`. However, `renderHDComposite()` is on `ScummEngine` while `_blastObjectQueue` is on `ScummEngine_v6`. A direct lookup would require a `(ScummEngine_v6*)` cast (`gfx.cpp` currently has no V6 casts). While this works at runtime (COMI is V8→V6→ScummEngine), it's fragile.

**Better approach (verified):** Hook `superBlastObject()` in `script_v8.cpp:1227` where we already have access to the correct position parameters:

```cpp
// In script_v8.cpp, case 119 (superBlastObject):
case 119:  // superBlastObject
    enqueueObject(args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8], 0);
    // NEW: cache position for HD rendering
    if (args[1] >= 105 && args[1] <= 274) {
        _inventoryHDPositions[args[1]] = Common::Point(args[2], args[3] + _screenTop);
    }
    break;
```

**Declaration** (`scumm_v6.h` or `scumm.h`):
```cpp
// HashMap<obj_nr, screen_position>
HashMap<int, Common::Point> _inventoryHDPositions;
```

**Cache lifetime:**
- Populated: Every frame when inventory scripts run (`superBlastObject` called)
- Invalidated: When inventory closes → check `_userState & USERSTATE_IFACE_INVENTORY` in `removeBlastObjects()` or at end of frame

---

#### 3. ✅ `blastShadowObject` Ignorieren (Mode-Unterscheidung)

**Code:** `script_v8.cpp:1224-1228`
```cpp
case 118:  // blastShadowObject
    enqueueObject(args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8], 3);
    break;
case 119:  // superBlastObject
    enqueueObject(args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8], 0);
    break;
```

`blastShadowObject` passes `mode=3`, `superBlastObject` passes `mode=0`. In `drawBlastObject()` (`object.cpp:1856-1860`):
```cpp
if ((bdd.scale_x != 255) || (bdd.scale_y != 255)) {
    bdd.shadowMode = 0;
} else {
    bdd.shadowMode = eo->mode;  // mode=3 → shadow rendering
}
```

**Shadow positions are OFFSET** from the actual item position — the SCUMP script passes different coordinates. If we cached a shadow position and rendered HD there, the item would appear at the wrong location.

**Fix:** Only cache positions from `superBlastObject` (mode=0). Shadow positions (mode=3) are ignored.

---

#### 4. ✅ Position-Only Cache (Kein komplettes Rect nötig)

**Current HD rendering** (`gfx.cpp:1512-1515`):
```cpp
int64 hdX = (int64)od.x_pos * hdW / MAX(1, _screenWidth);
int64 hdY = (int64)od.y_pos * hdH / MAX(1, _screenHeight);
int hdObjW = MIN<int>(hdObjSurf.w, (int)(hdW - hdX));
int hdObjH = MIN<int>(hdObjSurf.h, (int)(hdH - hdY));
```

**Current culling** (`gfx.cpp:1524-1527`):
```cpp
int sx = od.x_pos;
int sy = od.y_pos;
int sw = MIN<int>(od.width, visW - sx);
int sh = MIN<int>(od.height, visH - sy);
```

Only `sx/sy` and `hdX/hdY` need to be overridden — the **positional origin**. The FLOBJ's own `width`/`height` dimensions are correctly set in `_objs[]` and already used for the area calculations. The HD texture surface (`hdObjSurf`) has its own dimensions.

**Implementation in Step 2.5** (`gfx.cpp`, within the FLOBJ loop):

```cpp
// Around line 1524: override position if we have a cached blast position
if (od.fl_object_index != 0 && od.x_pos == 0 && od.y_pos == 0) {
    auto it = _inventoryHDPositions.find(od.obj_nr);
    if (it != _inventoryHDPositions.end()) {
        int blastX = it->value.x;
        int blastY = it->value.y;
        // Override culling position
        sx = blastX;
        sy = blastY;
        // Override HD rendering position
        hdX = (int64)blastX * hdW / MAX(1, _screenWidth);
        hdY = (int64)blastY * hdH / MAX(1, _screenHeight);
        // Recompute area bounds
        sw = MIN<int>(od.width, visW - sx);
        sh = MIN<int>(od.height, visH - sy);
        hdObjW = MIN<int>(hdObjSurf.w, (int)(hdW - hdX));
        hdObjH = MIN<int>(hdObjSurf.h, (int)(hdH - hdY));
    }
}
```

The existing culling logic then works correctly: at the real screen position, `visiblePixels` will be > threshold → HD texture renders at the right location.

---

### Summary: Implementation Steps (4 changes)

| # | File | Change |
|---|------|--------|
| 1 | `scumm_v6.h` | Add `HashMap<int, Common::Point> _inventoryHDPositions` |
| 2 | `script_v8.cpp:1227` | Cache position in `superBlastObject` case; skip in `blastShadowObject` case |
| 3 | `gfx.cpp:1524-1525` | Override `sx/sy` and `hdX/hdY` from cache when FLOBJ at (0,0) |
| 4 | `gfx.cpp` (around `inventoryActive`) | Use `(_userState & USERSTATE_IFACE_INVENTORY)` instead of cursor pixel heuristic |

**No changes needed:** `object.cpp`, `verbs.cpp`, `hd_object_manager.cpp`

---

### Alternatives Considered (and rejected)

1. **Direct blast queue lookup from Step 2.5** — requires `(ScummEngine_v6*)` cast. Works but fragile.
2. **Fix in Step 2.8b (verbs)** — Dead code, inventory items aren't verbs (`verbs.cpp:1227-1229`).
3. **Fix in `drawBlastObject()`** — Wrong layer; 8-bit engine draws at the right position, the issue is the HD composite pass.
4. **Fix via script patching** — Impossible without modifying game data files.
