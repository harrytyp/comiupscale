# APPROACH B: Verb-based Analysis — Are Inventory Items Verbs in COMI V8?

**Status: COMPLETE — Findings are definitive**

---

## 1. Definitive Answer: NO — Inventory Items Are NOT Verbs in COMI V8

**COMI V8 inventory items are FLOBJs (Floating Objects), NOT verb slots.** They are rendered through the `_objs[]` object system, not the `_verbs[]` verb system.

### Direct Evidence

**Evidence 1: Log analysis** (`hd_state.log`, frames 149-175):
```
F=149 INVOBJ: oi=31 obj=118 fl=9  state=0 pos=(0,0) sz=(80x56)  ← skeleton-arm-icon
F=149 INVOBJ: oi=30 obj=231 fl=8  state=0 pos=(0,0) sz=(80x56)  ← pirate-literature-icon
F=149 INVOBJ: oi=29 obj=120 fl=7  state=0 pos=(0,0) sz=(80x56)  ← two-balloons-icon
F=149 INVOBJ: oi=28 obj=395 fl=0  state=0 pos=(232,88) sz=(96x160)
...
F=150 step2.5 objects: loaded=9 skipped=0 culled=2
```

All inventory items (`obj_nr` 118, 231, 120, 124) have `fl>0` (FLOBJ flag) and are processed through **Step 2.5** (FLOBJ object rendering).

The log contains:
- **0 instances** of `"drawVerbBitmap CALL"` — drawVerbBitmap is NEVER called
- **0 instances** of `"drawVerb CALL"` — the V7 drawVerb logging prints nothing
- **0 instances** of `"step2.8b"` — Step 2.8b renders ZERO items
- **14 instances** of `"verbDraw=0"` — `_hdVerbDrawCount` stays at 0 every frame

**Evidence 2: `addObjectToInventory()`** (`object.cpp:34-65`):
```cpp
void ScummEngine::addObjectToInventory(uint obj, uint room) {
    // ...
    slot = getInventorySlot();
    _inventory[slot] = obj;         // Adds to inventory array
    dst = _res->createResource(rtInventory, slot, size);  // Creates rtInventory resource
    // NO call to setVerbObject() — NO verb entry created
}
```

**Evidence 3: `whereIsObject()` for inventory items**:
```cpp
case WIO_INVENTORY:   // Not WIO_VERB
```
Inventory items are found via `WIO_INVENTORY`, not verb lookups.

**Evidence 4: The v0.0.64 commit assumption was WRONG.**

The commit message stated: *"COMI V8 inventory items are managed through the Verb system (_verbs[] array)"* — this is factually incorrect. The commit author never verified this assumption against actual log evidence.

---

## 2. Why Step 2.8b Doesn't Fire for Inventory Items

Step 2.8b (`gfx.cpp:2024-2064`) iterates over ALL `_verbs[]` slots:
```cpp
for (int vi = 0; vi < _numVerbs; vi++) {
    VerbSlot *vst = &_verbs[vi];
    if (!vst->hd_obj_nr || vst->hd_obj_nr == 114)  // skip bg
        continue;
    // ...
}
```

For this to render an inventory item, its verb slot must have `hd_obj_nr > 0`. This is ONLY set by `setVerbObject()` (`verbs.cpp:1489-1490`):
```cpp
_verbs[verb].hd_obj_nr = object;
_verbs[verb].hd_room = room;
```

And `setVerbObject()` is ONLY called from `SO_VERB_IMAGE` (`script_v8.cpp:1023-1031`):
```cpp
case SO_VERB_IMAGE:     // Set verb image
    b = pop();          // room
    a = pop();          // object number
    if (_curVerbSlot && a != vs->imgindex) {
        setVerbObject(b, a, _curVerbSlot);
        vs->type = kImageVerbType;
        vs->imgindex = a;
    }
```

COMI V8 scripts do NOT call `SO_VERB_IMAGE` for inventory items. Therefore, no verb slot ever gets `hd_obj_nr` set for inventory item object numbers (117-274). Step 2.8b is **dead code** for inventory items.

### Why Some Verb Slots DO Get hd_obj_nr

The COMI scripts do call `SO_VERB_IMAGE` for:
- The engagement circle (verb coin) — object numbers depend on room
- Dialog/UI elements

But NOT for inventory items.

### The Verb Slot Capacity

For COMI V8, `_numVerbs = 50` (read from MAXS block at `resource.cpp:1285`). Slots 0-49. But there are typically 5-25 actual verb slots used at any time, and they're for the engagement circle and dialog system, NOT inventory items.

---

## 3. What Would It Take to Make Step 2.8b Handle FLOBJs?

### Option A: Fix Step 2.5 (FLOBJ Path) Instead — RECOMMENDED
Since inventory items ALREADY go through Step 2.5 correctly (they're in `_objs[]`), the right fix is to fix Step 2.5's culling and layer-file skip logic:

1. **Fix culling** (`gfx.cpp:1485-1508`): When a FLOBJ has `fl_object_index != 0` and a valid HD texture in room 3, skip the pixel-based culling. The 8-bit inventory items are drawn on the Verb Virtual Screen, not the Main Virtual Screen, so the clean-background diff never detects them.

2. **Fix layer-file check** (`gfx.cpp:1461-1468`): The inventory background (obj_nr 114) has `fl_object_index != 0` (it's a FLOBJ), so it should NOT be classified as a layer file. The existing check `od.fl_object_index == 0` already handles this correctly for FLOBJs.

3. **Fix `findObjectRoom()`** (`hd_object_manager.cpp:283-291`): Currently returns the first room in the HashMap, which happens to be room 3 for inventory items. Verify this is reliable.

### Option B: Dynamically Create Verb Entries in Step 2.8b — NOT RECOMMENDED
Change Step 2.8b to iterate FLOBJs instead of verbs:
```cpp
// In Step 2.8b, replace verb iteration with FLOBJ iteration
for (int vi = ...) { ... }  →  for (int oi = 0; oi < _numLocalObjects; oi++) {
    ObjectData *od = &_objs[oi];
    if (!od->fl_object_index) continue;  // Only FLOBJs
    // check HD texture, position, blit
}
```

**Problem**: This duplicates Step 2.5's work and risks double-rendering. Plus, Step 2.5 already positions items at their correct FLOBJ coordinates (x_pos/y_pos), which is more accurate than verb `curRect`.

### Option C: Have Scripts Create Verb Entries — IMPRACTICAL
Modify COMI V8 scripts to call `SO_VERB_IMAGE` for each inventory item. Not feasible — scripts are in SCUMM bytecode and would need reverse-engineering and patching.

---

## 4. Risk Assessment

### Current State (v0.0.64)
| Component | Status | Root Cause |
|---|---|---|
| Inventory BG (obj 114) | ❌ SD | Rendered via Step 2.5, culled because 8-bit diff fails for verb-screen objects |
| Inventory icons (obj 117-274) | ❌ SD | Rendered via Step 2.5, culled because pixel detection fails |
| Engagement circle | ❌ SD | Verb system, but no HD textures in object_map.json |
| Step 2.8b | ⚠️ Dead code | Iterates verb slots, inventory items aren't verbs |

### If We Fix Step 2.5 Instead of Step 2.8b
- **Low risk**: Step 2.5 already handles FLOBJs correctly for room objects. The fix is to disable culling for FLOBJ inventory items and fix the layer-file check.
- **No duplication**: Step 2.8b can remain as-is (or be removed) since it's unused.
- **No double-render**: FLOBJs rendered in Step 2.5, verbs in Step 2.8 — separate domains.

### If We Persist with Step 2.8b
- **High risk**: Double-rendering if both Step 2.5 AND Step 2.8b render the same items
- **Medium risk**: Position mismatch — FLOBJ positions (x_pos/y_pos) may differ from verb positions (curRect)
- **High complexity**: Requires adding verb entries dynamically, managing state, syncing with FLOBJ lifecycle

---

## 5. Key Code Locations

| File | Lines | Purpose |
|---|---|---|
| `gfx.cpp` | 2024-2064 | Step 2.8b — verb-based HD item compositing (currently dead code) |
| `gfx.cpp` | 1431-1645 | Step 2.5 — FLOBJ object rendering (where inventory items ARE handled) |
| `gfx.cpp` | 1485-1508 | Culling logic — kills inventory FLOBJs |
| `gfx.cpp` | 1461-1468 | Layer-file skip — incorrectly skips some FLOBJs |
| `verbs.cpp` | 1231-1386 | `drawVerbBitmap()` — only called for image-type verb slots |
| `verbs.cpp` | 1417-1491 | `setVerbObject()` — sets `hd_obj_nr`, only called from `SO_VERB_IMAGE` |
| `verbs.cpp` | 1036-1128 | `ScummEngine_v7::drawVerb()` — V7/V8 verb drawing |
| `verbs.cpp` | 519-539 | `redrawVerbs()` — iterates ALL verb slots, calls `drawVerb()` |
| `script_v8.cpp` | 1023-1031 | `SO_VERB_IMAGE` — only way `hd_obj_nr` gets set |
| `object.cpp` | 34-65 | `addObjectToInventory()` — does NOT create verb entries |
| `resource.cpp` | 1285 | `_numVerbs = 50` for COMI V8 (MAXS block) |
| `scumm.h` | 539 | `VerbSlot *_verbs` — dynamically allocated array |

---

## 6. Conclusion

**Approach B (Verb-based fix) is the wrong approach.** Inventory items in COMI V8 are FLOBJs, not verbs. Step 2.8b is dead code that never fires for inventory items because no verb slot ever gets `hd_obj_nr` set for inventory item object numbers.

**The correct fix is in Step 2.5 (FLOBJ path)**, where inventory items already exist and are actively loaded — they're just killed by culling heuristics that don't account for verb-screen overlay rendering.

**Recommendation**: Abandon Approach B. Fix Step 2.5's culling logic instead (Approach A).
