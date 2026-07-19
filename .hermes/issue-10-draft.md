## Problem

Inventory items (obj_nr 105–274) never display HD textures when the inventory is open. The HD textures exist on disk (365 PNGs in `hd/objects/` for Room 3) and are correctly loaded by `HdObjectManager::loadObject()`, but they are immediately discarded by the pixel-culling heuristic in Step 2.5 of `renderHDComposite()`.

This issue has been open since the project began. The v0.0.64 workaround (Step 2.8b) was based on an incorrect assumption and does not fire.

## Root Cause

### Why It Fails

In `renderHDComposite()` Step 2.5 (`gfx.cpp`), the FLOBJ processing loop works as follows for inventory items:

1. V8 FLOBJ with `state=0` passes through the initial state gate (line 1446–1448) ✅
2. Room fallback → `HdObjectManager::findObjectRoom()` → Room 3 → HD texture loaded ✅
3. **Position**: uses `_objs[oi].x_pos` / `_objs[oi].y_pos` — these are **(0,0)** for all inventory FLOBJs
4. **Culling**: compares 8-bit pixels at screen position (0,0) vs clean background → `visiblePixels = 0`
5. Line 1577: the `(0,0)` position override forces threshold to 1 pixel
6. `visiblePixels(0) < threshold(1)` → **CULLED** ❌

The 8-bit inventory items are drawn by COMI scripts via GDI commands at their actual slot positions (e.g., x=520, y=300), but the culling check runs at the FLOBJ position (0,0), sees nothing, and kills the HD texture.

### Why `_objs[].x_pos` Is Always (0,0) for Inventory FLOBJs

**COMI V8 inventory items are drawn via `superBlastObject` / `blastShadowObject` opcodes**, NOT through the regular object drawing pipeline (`o8_drawObject`). This was a key discovery of the forensic analysis.

```
Script: superBlastObject(obj_nr, x, y, w, h)
  → kernelSetFunctions case 119 → enqueueObject(obj, x, y, ...)
  → stores CORRECT position in _blastObjectQueue[].rect (left, top)
  → never touches _objs[].x_pos (stays at resource-default 0)
```

The `_blastObjectQueue[]` has the exact screen coordinates, but Step 2.5 never reads it — it only reads the stale `_objs[].x_pos = 0`.

### Why Step 2.8b (v0.0.64) Doesn't Fire

Step 2.8b (added in commit `bb24e18f`) iterates all `_verbs[]` checking `hd_obj_nr > 0` and composites HD textures at verb slot positions.

**Inventory items are NOT verbs in COMI V8.** They are FLOBJs. The v0.0.64 commit assumption *"COMI V8 inventory items are managed through the Verb system"* was never verified against actual game output. A live `hd_state.log` trace from a gameplay session (Room 14, inventory open) confirms:
- **0 calls** to `drawVerbBitmap` or `drawVerb` for inventory items
- **0 items** rendered by Step 2.8b
- **All inventory items** rendered through Step 2.5 (FLOBJ path) with `fl_object_index > 0`

Step 2.8b is **dead code** for inventory items. It only catches the inventory background (obj=114) which IS set up as a verb via `SO_VERB_IMAGE`.

### Race Condition

The `inventoryActive` flag is set at line 1547 when cursor FLOBJ (obj=105) has `visiblePixels > 100`. The FLOBJ loop iterates in **reverse order** (high obj_nr first). Inventory items (106–274) are processed **before** the cursor (105), so they never see `inventoryActive=true` on frames where the flag first becomes available.

## Proposed Fix: Blast-Object Position Cache with Priority-Filtered Rendering

### Design (reviewed by GLM 5.2 via Nvidia NIM)

The fix uses a **persistent position cache** populated during script execution, combined with a **priority filter** to avoid object-type confusion:

#### Step 1: Hook `superBlastObject()` to cache positions (script_v8.cpp)

In `kernelSetFunctions`, `case 119` (superBlastObject) and `case 118` (blastShadowObject):

```cpp
// === HD MOD: Cache blast object positions for inventory items ===
if (_hdScale > 1 && args[1] >= 105 && args[1] <= 274) {
    // Only cache superBlastObject (case 119), NOT blastShadowObject (case 118)
    // Shadows have offset positions that would misplace HD textures
    _hdInventoryPositions[args[1]] = Common::Point(args[2], args[3]);
}
// ===============================================================
```

This runs at the exact moment the script specifies the item's correct screen position. The cache persists across frames — no flickering on static inventory.

Declaration (in `scumm.h`):
```cpp
// HD mod: cache of inventory item screen positions from superBlastObject
Common::HashMap<uint16, Common::Point> _hdInventoryPositions;
```

Cleared when inventory closes (in `scumm.cpp` or the script opcode handler for closing inventory):
```cpp
if (_hdScale > 1)
    _hdInventoryPositions.clear();
```

#### Step 2: Fix culling + rendering in Step 2.5 (gfx.cpp)

Modify the inventory FLOBJ handling in `renderHDComposite()` Step 2.5:

```cpp
// Before the FLOBJ loop, set inventoryActive from the authoritative cache
bool blastInventoryActive = !_hdInventoryPositions.empty();
// Use blast detection OR existing cursor detection
if (blastInventoryActive)
    inventoryActive = true;

// In the FLOBJ loop, when processing a potential inventory item:
if (od.fl_object_index != 0 && od.x_pos == 0 && od.y_pos == 0) {
    if (inventoryActive) {
        // Look up the correct position from the script-validated cache
        auto it = _hdInventoryPositions.find(od.obj_nr);
        if (it != _hdInventoryPositions.end()) {
            int realX = it->value.x;
            int realY = it->value.y;
            // Use (realX, realY) for:
            //   a) culling diff — check if 8-bit has foreground pixels HERE
            //   b) HD texture position — render at (realX * hdScale, realY * hdScale)
            // Bypass the (0,0) threshold override at line 1577
        }
    }
    // If not found in cache (or inventory inactive):
    // fall back to existing (0,0) culling behavior
}
```

#### Step 3: Priority-filtered rendering

Only render inventory FLOBJs whose HD textures are actually visible and not occluded:

```cpp
// After position override, apply priority filter:
// Skip items that are behind the inventory background or off-screen
if (realY >= invBgBottom || realX >= invBgRight)
    continue;  // Item outside inventory panel area

// Skip items whose 8-bit slot is empty (no foreground pixels at slot position)
int visiblePixels = countDiffPixels(realX, realY, od.width, od.height);
if (visiblePixels < sw * sh / 10)  // < 10% of slot area
    continue;  // Empty slot, don't render HD
```

The 10% threshold is generous enough to pass for any occupied slot but strict enough to skip truly empty slots (0% pixels ≠ background).

### Why This Fix Will Work

| Issue | How Addressed |
|-------|---------------|
| **Correct position** | `superBlastObject()` provides the exact screen position set by the COMI script |
| **No flickering** | Cache persists across frames, not dependent on per-frame blast queue state |
| **No race condition** | `_hdInventoryPositions.empty()` works on first frame regardless of loop order |
| **No shadow offset** | `blastShadowObject` (case 118) is explicitly excluded — only `superBlastObject` positions cached |
| **No verb confusion** | Works entirely through FLOBJ/script system, not verbs |
| **Reliable inventory signal** | `!_hdInventoryPositions.empty()` when any inventory items have been drawn → no false positives from cursor pixels |
| **Safe fallback** | If cache miss → existing (0,0) culling behavior preserved |
| **Save/Load safe** | Cache is cleared on room change and inventory close — repopulated by scripts on next frame |
| **Performance** | HashMap lookup: O(1) per FLOBJ, cache cleared only on inventory state change |

### Prior Art (all failed attempts)

| Version | Approach | Why Failed |
|---------|----------|------------|
| v0.0.17 | FLOBJ size filter | Blocked inventory too |
| v0.0.18 | Always render FLOBJs | Too permissive — icons in every room |
| v0.0.19 | Home room check | Too restrictive — inventory has home room 3, player in room 9 |
| v0.0.20 | Culling introduced | Kills all inventory (Main VirtScreen diff, inventory is Verb VirtScreen) |
| v0.0.22 | getState() fix | Helps state detection but culling still kills |
| v0.0.23 | Verb timestamp | Timing unreliable, missed frames |
| v0.0.53 | Cursor-canary detection | inventoryActive set but (0,0) threshold still kills |
| v0.0.64 | Step 2.8b verb loop | Inventory items are NOT verbs — dead code |

### Open Questions

1. **COMI inventory slot layout**: What are the exact SD slot positions (x, y, width, height) for each inventory slot in COMI V8? The blast object cache gives us per-item positions, but we may also want grid-aware rendering for empty slots or scrolling.

2. **Multi-state items**: Some inventory items have HD textures for state=1 (hover/selected). Should we render the hover state HD texture when the item is moused over? This requires reading `_objectStateTable[obj_nr]` or detecting mouse position.

3. **Engagement circle**: The grab/view/speak verb coin at the bottom-right is still not HD — it's not in `object_map.json` at all. Separate issue.

4. **`_hdInventoryPositions` cache size**: Max ~80 entries (inventory capacity). HashMap overhead is negligible.

### Files to Modify

| File | Change |
|------|--------|
| `engines/scumm/scumm.h` | Add `Common::HashMap<uint16, Common::Point> _hdInventoryPositions` |
| `engines/scumm/script_v8.cpp` | Cache position in `case 119` (superBlastObject) |
| `engines/scumm/gfx.cpp` | Use cache in Step 2.5 for position + culling bypass |
| `engines/scumm/scumm.cpp` | Clear cache on room change / inventory close |

### Verification

1. Build fork → open inventory → verify HD item icons at correct slot positions
2. Close inventory → verify HD overlay fully removed
3. Move through different rooms with inventory closed → verify NO HD inventory icons appear in room
4. Interact with items (pick up, use) → verify HD updates correctly
5. Save/load with inventory open → verify HD appears after reload
6. Empty inventory → verify no HD artifacts or crashes

### GLM 5.2 Review Summary

The approach was critically reviewed by GLM 5.2 via Nvidia NIM. Key feedback incorporated:
- ✅ **Persistent cache** instead of blast-queue scan (avoids flickering, static-frame issue)
- ✅ **Shadow exclusion** (only superBlastObject, not blastShadowObject)
- ✅ **HashMap lookup** instead of O(n) queue scan
- ✅ **Priority filter** to skip empty/off-screen slots
- ⚠️ Cast to `ScummEngine_v6` avoided (use `_hdInventoryPositions` in `ScummEngine` directly)
