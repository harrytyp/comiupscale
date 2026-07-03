# Research: Inventory, Menu & Engagement Circle HD Problem

## Issue #3 — Root Cause Analysis

---

## 1. Relevant Files

### HD Compositing Pipeline
- **`engines/scumm/gfx.cpp`** — `renderHDComposite()` (lines 1229-1905)
  - **Step 2** (lines 1328-1368): Composite 8-bit content over HD background
  - **Step 2.5** (lines 1374-1543): Overlay HD object textures (FLOBJs)
  - **Step 2.8** (lines 1856-1884): Overlay HD verb overlay (inventory background)
- **`engines/scumm/verbs.cpp`** — `drawVerbBitmap()` (lines 1231-1314)
  - Loads HD textures for verb images (kImageVerbType)
  - Large overlays (inventory BG) → `_hdVerbSurface` for Step 2.8
  - Small items → Scale down to SD verb screen
- **`engines/scumm/verbs.h`** — `VerbSlot.hd_obj_nr` / `hd_room` (lines 61-62)
  - Stores per-verb which game object it corresponds to
- **`engines/scumm/input.cpp`** — Mouse scaling (lines 235-242)
  - `_mouse.x /= _hdScale` — Scales HD mouse coordinates back to SD

### HD Asset Management
- **`engines/scumm/hd_object_manager.h/cpp`** — `HdObjectManager`
  - `loadObject(obj_nr, room, state, dest)` — Load HD PNG from `hd/objects/`
  - `hasObject(obj_nr, room, state)` — Check if HD texture exists
  - `findObjectRoom(obj_nr)` — Find alternate room (e.g. Room 3 for inventory)
  - `buildObjectPath()` — Builds path: `hd/objects/{room:04d}_{name}_{state:04d}.png`
- **`engines/scumm/hd_asset_manager.cpp`** — Loads backgrounds (`hd/backgrounds/`)
- **`hd/object_map.json`** — Mapping: obj_nr → (name, rooms → states → PNGs)
  - 384 objects defined
  - Inventory items: obj_nr 105-274, all in **Room 3**
  - Inventory background: obj_nr 114 (`inventory-bg-object`)
  - Easyhard screen: obj_nr 1366 (`easyhard-choice-object`, Room 87)

### Engine Core
- **`engines/scumm/scumm.h`** — HD state: `_hdVerbSurface`, `_hdVerbSurfaceValid`, `_hdVerbScreenTimestamp`, `_hdVerbDrawCount`, `_hdScale`, `_hdBackgroundSurface`
- **`engines/scumm/object.cpp`** — `getState()`, `addObjectToInventory()`, `putState()`, `o6_setState()`
- **`engines/scumm/script_v8.cpp`** — `SO_VERB_IMAGE` (line 1023-1031): Calls `setVerbObject()` → sets `hd_obj_nr`
- **`engines/scumm/scumm.cpp`** — Initialization: `_verbs[i].hd_obj_nr = 0` (line 2140)

---

## 2. How the Inventory Rendering Pipeline Works

### 2a. SD Engine (Original)
1. Player opens inventory → Script calls `SO_VERB_ON` / `SO_VERB_IMAGE`
2. `setVerbObject(room, object, verb)` copies 8-bit image data from room resource to `rtVerb`
3. Sets `_verbs[verb].hd_obj_nr = object`, `_verbs[verb].hd_room = room`
4. `drawVerb()` renders the verb image onto the Verb Virtual Screen
5. FLOBJ items in the inventory are drawn through the object renderer

### 2b. HD Engine (our fork)
**Step 2.5 — FLOBJ Objects** (gfx.cpp lines 1393-1539):
1. All `_objs[]` are iterated in reverse ID order
2. V8 FLOBJs with state=0 are **still passed through** (lines 1410-1414)
3. `getState(od.obj_nr)` fetches the real state from `_objectStateTable[]`
4. If hasObject() fails in the current room, `findObjectRoom()` is tried (e.g. Room 3)
5. HD texture loaded → positioned at `od.x_pos, od.y_pos` in HD coordinates
6. **Culling** (lines 1485-1508): Checks if 8-bit pixels in the object area ≠ Clean Background
7. **Alpha blending**: Only pixels with alpha≥128 are drawn

**Step 2.8 — Verb Overlay** (gfx.cpp lines 1856-1884):
1. `_hdVerbSurface` (set by `drawVerbBitmap()` for large textures) is composited on top
2. Used ONLY for large textures (≥90% of HD canvas size)
3. Cleared at end of each frame

**drawVerbBitmap (verbs.cpp lines 1231-1314):**
1. Checks: `hd_obj_nr > 0` and `HdObjectManager::isEnabled()`
2. For **large** textures (≥90% HD canvas, e.g. inventory background):
   - Stored in `_hdVerbSurface` → composited by Step 2.8
3. For **small** textures (e.g. inventory icons):
   - Scales HD down to SD verb screen (downsampling: every 4th pixel)
4. Otherwise: Falls back to 8-bit `drawBitmap()`

---

## 3. What Has Gone Wrong — Root Causes

### Problem A: Inventory Background (obj_nr 114) not shown in HD

**Root cause: `_hdVerbSurface` only set for large textures, but the condition is too strict AND drawVerbBitmap isn't being called for it at all**

In `drawVerbBitmap()` (line 1265):
```cpp
bool isLarge = (hdSurf.w * 10 >= expectedHDW * 9 && hdSurf.h * 10 >= expectedHDH * 9);
```
The inventory background (obj_nr 114, `inventory-bg-object`) is 2560×1920 — same size as the HD canvas. But `drawVerbBitmap` is never called for it because:

1. The SCUMM scripts set the inventory BG via the **FLOBJ system**, not via `SO_VERB_IMAGE`
2. Room 3 (inventory) is never set as `_currentRoom` — it's an overlay
3. `Step 2.5` should pick up the FLOBJ with obj_nr 114, but state=0, fl_object_index=0 causes it to be skipped or classified as a "layer file"

**Previous fixes:**
- `v0.0.19`: FLOBJs only in their home room → too restrictive (reverted in v0.0.20)
- `v0.0.20`: Always render FLOBJs → too permissive (objects appeared in wrong rooms)
- `v0.0.22`: `getState()` instead of `_objs[].state` → helps visible objects, but not overlays
- `v0.0.23`: FLOBJ verb timestamp check → missed first frames due to timing

### Problem B: Inventory Icons missing / SD

**Root cause: Culling in Step 2.5 kills them**

Inventory icons (obj_nr 117-274) are FLOBJs with state=0 in `_objs[].state`, but `_objectStateTable[obj_nr] != 0` when the inventory is open.

The culling code (lines 1485-1508) checks whether the 8-bit screen has foreground pixels in the object area (diff against clean background). **Problem**: The Clean Background was captured from the **current room** (e.g. Room 9, cannon room), but the inventory is rendered **on top** as a verb screen overlay. The inventory items are NOT drawn through the room engine — they're drawn through the verb system on `[kVerbVirtScreen]`, not `[kMainVirtScreen]`. So the diff shows no change, and the HD objects get culled.

**Previous fixes:**
- `v0.0.22`: `getState()` fix — helps state-based objects, but not the culling
- Culling code (introduced between v0.0.8 and v0.0.20) was meant to improve performance, but incorrectly kills overlay FLOBJs

### Problem C: Engagement Circle (Grab/View/Speak) not HD

**Root cause: These UI elements don't exist as entries in object_map.json**

The engagement circle (verb coin in the bottom-right) is drawn in COMI through the **verb system** — individual verbs with `kImageVerbType`. Verbs are set via `SO_VERB_IMAGE` in `script_v8.cpp` (lines 1023-1030), which calls `setVerbObject()`.

Although `setVerbObject()` does set `hd_obj_nr` and `hd_room` (lines 1444-1445/1465-1466/1477-1478), these are only set **if the object is found in the current room's local objects** (loop over `_numLocalObjects-1..0` in setVerbObject).

For the engagement circle:
1. The verb images are embedded in the room resource (e.g. Room 0 or the current room's resource)
2. `hd_obj_nr` gets set, but the objects often have **no entry in object_map.json** — there are no entries for the Grab/View/Speak icon object numbers
3. Even if they did: `drawVerbBitmap` checks `hasObject(hd_obj_nr, hd_room, 0)` → false → fallback to SD

**Core issue**: The 8-bit verb images are NOT room objects in the `_objs[]` sense — they're stored as IMxx chunks in the room resource and have no corresponding entries in `object_map.json`. To support them in HD, either:
- Extract the verb images and add them to `object_map.json` and `hd/objects/`, OR
- Use a different mechanism (custom HD verb textures)

### Problem D: Easyhard Screen wrong position/scale

**Root cause: `_screenWidth/_screenHeight` vs `_roomWidth/_roomHeight` discrepancy**

In Step 2.5 (line 1474):
```cpp
int64 hdX = (int64)od.x_pos * hdW / MAX(1, _screenWidth);
```

Room 87 (easyhard-choice) has `_roomWidth != _screenWidth`. The HD object positioning code was changed from `_roomWidth/_roomHeight` to `_screenWidth/_screenHeight` in a previous version. For most rooms this is fine, but Room 87 has different dimensions → object is mispositioned.

### Problem E: Inventory BG (obj_nr 114) incorrectly classified as layer file

In Step 2.5 (lines 1461-1468):
```cpp
if (hdObjSurf.w >= hdW && hdObjSurf.h >= hdH && od.fl_object_index == 0) {
    hdObjSurf.free();
    continue; // Skip full-HD textures (pre-composited layer files)
}
```

The `inventory-bg-object` (obj_nr 114) has `fl_object_index == 0` and `hdObjSurf.w == hdW, hdObjSurf.h == hdH`. So it's interpreted as a "layer file" and **skipped**. This is correct for room backgrounds, but **wrong for the inventory overlay**, which is not a layer file.

---

## 4. Flow Diagram

```
Player opens inventory (right-click or I key)
  │
  ├─ SCUMM Script: SO_VERB_ON for inventory verbs
  │   └─ setVerbObject() sets hd_obj_nr / hd_room
  │
  ├─ drawVerb() / drawVerbBitmap()
  │   ├─ obj_nr 114 (inventory-bg-object) → 2560×1920 → isLarge=true
  │   │   └─ _hdVerbSurface stored → Step 2.8
  │   │
  │   ├─ obj_nr 117-274 (inventory icons) → small textures
  │   │   └─ HD→SD downscale onto Verb VirtScreen
  │   │
  │   └─ Engagement circle → hd_obj_nr 0 or not in object_map.json
  │       └─ Fallback to 8-bit drawBitmap()
  │
  ├─ Step 2 (renderHDComposite):
  │   └─ Clean Background diff (current room, e.g. Room 9)
  │       └─ Inventory pixels NOT in diff → no change detected
  │
  ├─ Step 2.5 (FLOBJ Objects):
  │   ├─ inventory-bg-object (obj_nr 114): state=0, fl_object_index=0
  │   │   ├─ (line 1416) → skipped because state==0 && not FLOBJ
  │   │   └─ (line 1465) → also classified as layer file
  │   │
  │   ├─ inventory icons (obj_nr 117+): FLOBJs
  │   │   ├─ getState() ≠ 0 (inventory open) → OK
  │   │   ├─ hasObject(currentRoom) → false (e.g. Room 9)
  │   │   ├─ findObjectRoom() → Room 3 → OK
  │   │   ├─ Culling: no visible diff → CULLED ✗
  │   │   └─ OR culling passes → Old SD pixels overlap HD ✗
  │   │
  │   └─ Result: HD textures loaded but culled or overwritten by SD
  │
  └─ Step 2.8 (Verb Overlay):
      └─ _hdVerbSurfaceValid → Composite inventory-bg-object
          └─ Problem: may never have been set (drawVerbBitmap not called)
```

---

## 5. Possible Solutions

### Approach A: Disable culling for FLOBJ inventory items
- In Step 2.5: When `od.fl_object_index != 0` and `getState() != 0`, skip the culling check
- **Risk**: Performance (unlikely with <20 items)
- **Advantage**: Simple, minimal code change
- Location: gfx.cpp lines 1485-1508

### Approach B: Ensure inventory BG is rendered as Verb Overlay
- Make sure `drawVerbBitmap` is called for obj_nr 114
- Or: Add inventory overlay detection in Step 2.5 (check if `_hdVerbScreenTimestamp` is recent)
- Location: verbs.cpp drawVerbBitmap + gfx.cpp Step 2.5

### Approach C: Fix FLOBJ layer check
- `inventory-bg-object` shouldn't be excluded as a layer file
- Check: If `fl_object_index == 0` AND `_hdVerbScreenTimestamp` is recent → let through
- Location: gfx.cpp lines 1461-1468

### Approach D: Add engagement circle to object_map.json
- Extract verb image objects from room resources
- Add new entries to object_map.json
- Ensure `setVerbObject()` sets correct obj_nr

### Approach E: Fix Room 87 easyhard coordinates
- Use `od.x_pos * hdW / MAX(1, _roomWidth)` for rooms with different dimensions
- Or: Special-case Room 87
- Location: gfx.cpp line 1474

---

## 6. Current Status (v0.0.26)

| Feature | Status | HD? |
|---------|--------|-----|
| Room backgrounds | ✅ Working | HD |
| Costumes (characters) | ✅ Working | HD |
| Objects in rooms | ✅ Mostly | HD |
| Fonts | ✅ Working | HD |
| **Inventory background** | ❌ **Missing** | **SD** |
| **Inventory icons** | ❌ **Missing** | **SD** |
| **Engagement circle** | ❌ **Missing** | **SD** |
| **Easyhard screen** | ❌ **Wrong position** | **SD** |
| Cutscene credits | ❌ Open (Issue #6) | SD |
| Shadows | ❌ Open (Issue #8) | Partial |

**Previous fixes (all failed):**
- v0.0.17: FLOBJ size filter → blocked inventory too
- v0.0.18: Always render FLOBJs → too permissive
- v0.0.19: Home room check → too restrictive
- v0.0.20: Culling introduced → kills inventory
- v0.0.22: getState() fix → helps state-based objects, not overlays
- v0.0.23: Verb timestamp → timing issue
- v0.0.24-26: FLOBJ improvements → but culling/coordinates/layer problems remain
