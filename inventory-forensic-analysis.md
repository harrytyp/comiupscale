# Inventory Rendering Pipeline — HD Forensic Analysis

> Repository: `/opt/data/local/comi-hd-repo/scummvm/fork/engines/scumm/`
> Generated: 2026-07-18

---

## 1. Overview: Two-Path Inventory Rendering

COMI V8 inventory rendering takes **two separate paths** in the HD pipeline:

### Path A: Step 2.5 — FLOBJ Object Rendering (`gfx.cpp:1431-1645`)

- Iterates ALL `_numLocalObjects` in reverse ID order (highest→lowest z-order)
- Inventory items are **FLOBJs** (floating objects with `fl_object_index != 0`)
- In COMI V8, inventory FLOBJs always have `state=0` and `locked=1`
- Uses **pixel culling** — checks 8-bit foreground pixel count vs. threshold per object
- Falls back to alternate rooms via `HdObjectManager::findObjectRoom()` for inventory items
- Blits HD texture with alpha onto `_hdComposite`

### Path B: Step 2.8 + 2.8b — Verb Slot Rendering (`gfx.cpp:2004-2064`)

- Step 2.8: Large overlays (inventory background = obj 114) → `_hdVerbSurface` → composited directly
- Step 2.8b: Small inventory items → iterates VerbSlots, loads HD PNGs, blits at verb `curRect` position
- VerbSlot stores `hd_obj_nr` + `hd_room` (populated by `setVerbObject` in `verbs.cpp:1417`)
- HD textures loaded via `HdObjectManager::loadObject()` with **hardcoded state=0**

---

## 2. Inventory Active Detection (`gfx.cpp:1423-1563`)

No dedicated HD_INVENTORY flag exists. Detection is **heuristic-based**:

1. **Cursor visibility** (obj=105): `visiblePixels > 100` → sets `inventoryActive = true`
   - Cursor has ~0 visible pixels when inventory closed, ~3000 when open
   - Checked per-object in the loop — cursor (obj_nr=105) is a LOW-ID object

2. **Large FLOBJ gating** (obj at 0,0 position): `<33% foreground pixels → force cull`
   - Inventory items at position (0,0) with `<33% visible pixels` are assumed closed

3. **>50% screen FLOBJs** (obj=114 inventory-bg-object):
   - Threshold raised to 50% of area
   - ALSO gated on `inventoryActive` flag

**Failure point**: The `inventoryActive` flag is only set when the cursor FLOBJ (obj=105,
low ID ≈ z-front) is processed. Since iteration is reverse-ID order (highest first), 
all HIGHER-ID inventory items (e.g. 176 pistol, 137 ipecac) are processed BEFORE the 
cursor, so they miss the `inventoryActive` gate on the first frame.

---

## 3. HD Asset Loading for Inventory

### Room Mapping (`hd_object_manager.cpp:283-291`)

```cpp
int HdObjectManager::findObjectRoom(int obj_nr) const {
    // Returns the FIRST room in the rooms HashMap
    return rooms.begin()->_key;
}
```

All inventory icon objects are mapped to **room 3** in `object_map.json`.
`findObjectRoom()` returns the first room entry — for single-room objects this is correct.

### Object Map Coverage

- **446** `*icon-object*` entries in `object_map.json`
- **308** PNG files on disk at `release/windows/hd/objects/0003_*icon-object*`
- **~138 missing HD textures** for inventory items (mapped but no PNG)

### Asset Naming Convention

```
{room:04d}_{name}_{state:04d}.png
→ 0003_inventory-pistol-icon-object_0000.png
```

Inventory assets live in `hd/objects/` (not `hd/objects_layers/`).
All inventory items use room=3 only.

---

## 4. Identified Failure Points

### FAILURE 1: Double-Render Risk (Step 2.5 ↔ Step 2.8b)

The same inventory FLOBJ object can be rendered **twice**:
- Once by Step 2.5 (object loop at FLOBJ position)
- Once by Step 2.8b (verb loop at verb `curRect` position)

`drawVerbBitmap` syncs verb position to `_objs[oi].x_pos/.y_pos`, so positions usually
match. But **alpha blending is applied twice**, which can cause brightness artifacts
and visual doubling on semi-transparent inventory icons.

**Severity**: Medium. Cosmetic/missed-pixel on alpha edges.

---

### FAILURE 2: State=0 Hardcoding (`verbs.cpp:1255`)

```cpp
int state = 0;  // hardcoded
```

Inventory items in the verb system are **always loaded with state=0**. The object_map
defines both state 0 AND state 1 for most inventory icons (selected/highlighted variants).
Alternate states never get HD textures via the verb path.

**Severity**: Medium. Selected inventory items show the SD (8-bit) version instead of HD.

---

### FAILURE 3: Culling Heuristic Fragility (`gfx.cpp:1565-1593`)

Inventory rendering depends on pixel-count heuristics:
- 2% threshold for FLOBJs
- 33% threshold for items at (0,0)
- 50% + `inventoryActive` gate for full-screen objects

**Edge cases where culling fails:**
1. **Inventory closed but scene content bleeds into (0,0) area** → HD textures rendered when inventory is closed
2. **Inventory open but only 1-2 items visible (<33% coverage)** → HD textures culled
3. **Scene change mid-inventory** → stale clean background → wrong pixel counts

**Severity**: High. Causes inventory HD textures to appear when closed or disappear when open.

---

### FAILURE 4: `inventoryActive` Flag Race Condition (`gfx.cpp:1547`)

```cpp
if (od.obj_nr == 105 && od.fl_object_index != 0 && visiblePixels > 100) {
    inventoryActive = true;
```

The cursor (obj=105) has a **low object ID** (z-front, drawn last). In reverse-ID iteration,
higher-ID inventory items (137, 164, 176, 201...) are processed **BEFORE** the cursor.
They never see `inventoryActive=true` on the same frame's first pass.

**Severity**: Medium. Defers inventory-active detection by 1 frame, affecting only the
50%-threshold gate for large FLOBJs.

---

### FAILURE 5: Missing HD Inventory PNGs

- 446 icon-object entries in `object_map.json`
- Only 308 PNG files found on disk
- ~138 inventory items have no HD texture

Items without HD PNGs silently fall back to the 8-bit scaled composite (from Step 2).

**Severity**: High. These items always appear as upscaled SD sprites.

---

### FAILURE 6: Verb Room Fallback Gaps (`gfx.cpp:2034-2040`)

```cpp
int hdRoom = vst->hd_room;
if (!_hdObjectManager->hasObject(vst->hd_obj_nr, hdRoom, 0)) {
    int altRoom = _hdObjectManager->findObjectRoom(vst->hd_obj_nr);
    // ...
}
```

`vst->hd_room` is set by `setVerbObject()` using the **script-provided room**,
NOT always room 3. If `setVerbObject` was called with a non-room-3 value
(e.g., the player's current room), and no fallback is in the FLOBJ branch,
the verb's HD texture silently fails to load.

**Severity**: Medium. Depends on script behavior.

---

### FAILURE 7: No HD Inventory Scroll Support

The original V2 engine supports inventory scrolling via `_inventoryOffset`
(`verbs.cpp:414-420`). The HD pipeline has **no equivalent mechanism**.
Only FLOBJs that are currently active in the object list receive HD treatment.

**Severity**: Low (COMI V8 doesn't use the V2 inventory scroll system).

---

### FAILURE 8: `_userState & USERSTATE_IFACE_INVENTORY` Not Checked in HD Path

The original V2 inventory code checks `_userState & USERSTATE_IFACE_INVENTORY`
before rendering. The HD Step 2.5 path does **NOT** check this flag — it relies
entirely on pixel heuristics. If scripts set this flag to 0 but the 8-bit
composite still has foreground pixels in the inventory area, HD inventory
will render when it shouldn't.

**Severity**: Low (edge case, not common in COMI V8).

---

## 5. Data Flow Summary

```
Script calls setVerbObject(room, object, verb)
  → VerbSlot.hd_obj_nr = object
  → VerbSlot.hd_room = room
  
Engine draws via drawVerbBitmap(verb, x, y)
  → If object is LARGE (>90% HD canvas):
      Store in _hdVerbSurface for Step 2.8
  → If object is SMALL (inventory icon):
      Load+free HD texture, fall through to SD draw
      (Step 2.8b will re-blit HD version)

drawDirtyScreenParts() → renderHDComposite()
  Step 2:   Composite 8-bit game content over HD background
  Step 2.5: For each FLOBJ object (highest→lowest ID):
              1. Check hasObject(currentRoom, state)
              2. Fallback: try state=0
              3. Fallback (FLOBJ): try findObjectRoom()
              4. Pixel culling (2%/33%/50% thresholds)
              5. Load HD PNG via HdObjectManager
              6. Verify size/colors/position
              7. Alpha-blit to _hdComposite
              8. Mark hdAlphaMask
  Step 2.8:  If _hdVerbSurfaceValid: blit verb overlay
  Step 2.8b: For each verb with hd_obj_nr:
              1. Skip if hd_obj_nr == 114 (handled by 2.8)
              2. Load HD PNG via HdObjectManager
              3. Blit at verb curRect position in HD space
```

---

## 6. Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Entry point | `gfx.cpp` | 560-563 (`drawDirtyScreenParts`) |
| `renderHDComposite()` | `gfx.cpp` | 1235-2110 |
| Inventory detection | `gfx.cpp` | 1423-1593 |
| FLOBJ culling | `gfx.cpp` | 1517-1615 |
| FLOBJ blitting | `gfx.cpp` | 1620-1645 |
| FLOBJ verification | `gfx.cpp` | 1647-1700+ |
| Verb overlay (Step 2.8) | `gfx.cpp` | 2004-2023 |
| Verb items (Step 2.8b) | `gfx.cpp` | 2024-2064 |
| `drawVerbBitmap()` | `verbs.cpp` | 1231-1386 |
| `setVerbObject()` | `verbs.cpp` | 1417-1491 |
| VerbSlot struct | `verbs.h` | 47-63 |
| `HdObjectManager::loadObject()` | `hd_object_manager.cpp` | 232-274 |
| `HdObjectManager::findObjectRoom()` | `hd_object_manager.cpp` | 283-291 |
| `HdObjectManager::hasObject()` | `hd_object_manager.cpp` | 209-230 |
| HD members in engine | `scumm.h` | 555-587, 860-949 |
| Object map (JSON) | `config/object_map.json` | — |
| HD PNG assets | `release/windows/hd/objects/` | — |

---

## 7. Recommendations

1. **Fix Race Condition**: Move `inventoryActive` detection to BEFORE the FLOBJ loop, or do a pre-pass.
2. **Add State Awareness**: Pass the actual object state to `drawVerbBitmap` instead of hardcoding 0.
3. **Dedup Double Render**: Skip FLOBJs in Step 2.5 that are already handled by Step 2.8b, or vice versa.
4. **Generate Missing PNGs**: 138 inventory icon-objects have mapping entries but no PNG files.
5. **Add `_userState` Gating**: Check `USERSTATE_IFACE_INVENTORY` as a reliable signal alongside pixel heuristics.
6. **Verb Room Sync**: In Step 2.8b, always try `findObjectRoom()` first since inventory items are known to be in room 3.
