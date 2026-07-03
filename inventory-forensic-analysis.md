## In-Depth Analysis: Inventory Problem — Anatomy of 17 Failed Attempts

This is a forensic reconstruction of every attempt to fix the inventory/overlay HD rendering, spanning ~36 hours and 17 tagged versions. Understanding why each failed is critical to designing a fix that actually works.

---

### 1. THE FUNDAMENTAL TENSION

The inventory screen is a **hybrid overlay** in COMI's V8 engine:

- The **inventory background** (obj_nr 114, `inventory-bg-object`, 2560×1888) is a **room object** (`fl_object_index == 0`) that lives in **Room 3**
- The **inventory icons** (obj_nr 117-274, e.g. `hook-icon-object`, `cutlass-icon-object`) are **FLOBJs** (`fl_object_index != 0`) that also live in Room 3
- The **engagement circle** (grab/view/speak verb coin) is not in `object_map.json` at all — it's rendered by the verb system using images embedded in room resources

When the player opens the inventory while standing in Room 9:
- `_currentRoom = 9` (cannon room), NOT Room 3
- The 8-bit engine renders the inventory on the **Verb VirtScreen** (`[kVerbVirtScreen]`), not the Main VirtScreen
- The Main VirtScreen still shows Room 9's background with no inventory

The rendering code in `renderHDComposite()` was designed for **room content** (Main VirtScreen), not **verb overlays** (Verb VirtScreen). Every attempt to fix inventory forces an overlay mechanism through a room-object pipeline — and that's why they all break.

---

### 2. CHRONOLOGY OF FAILURE

#### Phase 0: Pre-v0.0.8 — The Room Fallback Era

These commits added FLOBJ rendering to Step 2.5 for the first time.

**Attempt 1: `4edba164` — "remove fl_object_index skip, use visW/visH for position"**
- **What it did**: Removed `if (od.fl_object_index) continue;` which had been skipping ALL floating objects. Changed positioning from `_roomWidth` to `visW` (= `_screenWidth`).
- **Why it failed**: FLOBJs from Room 3 didn't exist in the current room (e.g. Room 9). `hasObject(9, objState)` returned false → all skipped. Position change with visW broke Room 87 easyhard.

**Attempt 2: `ee3d4662` — "room fallback for inventory items + 8-pixel X alignment"**
- **What it did**: Added room fallback **inside** `hasObject()` and `loadObject()` in `HdObjectManager`. When the current room fails, it iterates ALL rooms looking for the object. Added `findObjectRoom()` method. Also added 8-pixel X alignment for strip-aligned rendering.
- **Why it failed**: The room fallback was TOO BROAD. Any object that existed in ANY room would be loaded from that room. Room-specific objects (e.g. a chair in Room 4) would appear in every room if their obj_nr matched. This caused objects appearing in wrong rooms everywhere.

**Attempt 3: `66872bf9` — "Restrict room fallback to inventory items only"**
- **What it did**: REVERTED the room fallback from HdObjectManager (back to strict room-only checks). Moved the room fallback logic to `RenderHDComposite()` Step 2.5, restricted to `fl_object_index != 0` (FLOBJs only). Non-FLOBJs get no fallback.
- **Why it failed**: The **inventory background** (obj_nr 114) has `fl_object_index == 0` → it gets NO room fallback. And the layer size check `if (hdObjSurf.w >= hdW && hdObjSurf.h >= hdH)` blocks it because it's 2560×1888, which is ≥ 2560×1920.

**Attempt 4: `92cc0f59` — "use 75% size threshold for layer detection"**
- **What it did**: Changed the layer detection from "≥100% of HD canvas" to "≥75% of HD canvas". This was meant to catch the `inventory-bg-object` at 2560×1888. 
- **Why it failed**: The 75% threshold was too aggressive. Many legitimate objects that should render in HD were also caught (objects that happened to be large in their room). Also, the inventory background still wasn't getting room fallback (it's fl_object_index == 0).

**Attempt 5: `2d943ea2` — "use od.state for inventory visibility (no thresholds)"**
- **What it did**: REVERTED the 75% threshold back to 100%. Added `if (od.fl_object_index && (od.state & 0xF) == 0) continue;` — skip FLOBJs with stale state=0.
- **Why it failed**: In V8, FLOBJs **ALWAYS** have `_objs[].state == 0` (they're never drawn by the 8-bit engine directly). They're synced from `_objectStateTable` once per frame by `updateObjectStates()`, and V8 scripts set their visibility via `putState()`. But `_objs[].state` is the stale pre-sync value. So ALL inventory FLOBJs were skipped because `od.state` was always 0. This COMPLETELY broke inventory.

---

#### Phase 1: v0.0.9 — The Verb Image Path

**Attempt 6: `5687d5a5` — "add HD verb images via drawVerbBitmap"** (major rework)
- **What it did**: Added `hd_obj_nr` and `hd_room` to `VerbSlot`. Set them in `setVerbObject()`. Added HD texture loading in `drawVerbBitmap()` that scales HD textures down to the SD verb screen. Reverted positioning back to `_roomWidth`.
- **Why it failed**: Only handled the "small texture" path (scale HD→SD verb screen). Had no mechanism for large overlays (inventory background). The HD textures were drawn on the SD verb screen and then upscaled back to HD by Step 2, losing quality. Also: many verbs don't go through `setVerbObject()` with useful `hd_obj_nr` values — engagement circle verbs have `hd_obj_nr = 0`.

**Attempt 7: `2b62318c` — "fix easyhard position, fix inventory BG"** (v0.0.9)
- **What it did**: Changed layer check to `if (hdObjSurf.w >= hdW && hdObjSurf.h >= hdH && od.fl_object_index == 0)` — allows FLOBJs through even at full size. Changed positioning to `_screenWidth` for easyhard fix.
- **Why it failed**: The inventory background (obj_nr 114) has `fl_object_index == 0`, so it's STILL blocked by the size check. The `fl_object_index != 0` exception only helps inventory ICONS (FLOBJs), not the BACKGROUND PANEL (room object).

---

#### Phase 2: v0.0.10-v0.0.13 — Full-Screen Verb Overlay + Debug

**Attempt 8: `f2944a80` — "full-screen verb HD compositing (Step 2.8)"** (v0.0.10)
- **What it did**: Added the **Step 2.8** verb overlay mechanism in `renderHDComposite()`. When `drawVerbBitmap` detects a full-screen texture (= exactly 2560×1920), it stores it in `_hdVerbSurface`. Step 2.8 composites it at the end. Removed 8-pixel strip alignment.
- **Why it failed**: The "full-screen" check was `hdSurf.w >= expectedHDW && hdSurf.h >= expectedHDH` (≥100%). But the inventory background at 2560×1888 is slightly SHORTER than the HD canvas (1920). So `isFullScreen = false` → it went through the SD downscale path instead. Also, `drawVerbBitmap` was only called if the verb had `hd_obj_nr > 0` AND the object existed in `hasObject()` — and the engagement circle verbs had `hd_obj_nr = 0`.

**Attempt 9: `e2c26529` — "relax full-screen check to 90%"** (v0.0.11)
- **What it did**: Changed the "full-screen" threshold from 100% to 90%. So 2560×1888 would now be detected as "large" (isLarge=true) and stored in `_hdVerbSurface`.
- **Why it failed**: Even though the inventory background (obj_nr 114) WOULD now be detected as large, it still required `drawVerbBitmap` to be called with `hd_obj_nr = 114` and `hasObject(114, room, 0) = true`. This required the verb to be set up with the correct obj_nr and room. The verb setup only works for objects in the current room, not Room 3. So the inventory background never triggers the large-texture path.

**Attempt 10: `ba8a4276` — "debug FLOBJ warning"** (v0.0.12)
- **What it did**: Added debug logging for FLOBJs in Step 2.5. No behavioral change.
- **Learned**: Confirmed that FLOBJs have `od.state = 0` and `getState() != 0` when inventory is open.

**Attempt 11: `171b5b2f` — "allow V8 flobj with state=0"** (v0.0.13)
- **What it did**: Changed the FLOBJ state=0 skip from "always skip" to "skip for V6, process for V8". V8 FLOBJs with state=0 now pass through to the hasObject check.
- **Why it failed**: The state check was `if (od.fl_object_index && (od.state & 0xF) == 0)` and the code now let V8 FLOBJs through. But the **inventory background** (obj_nr 114) has `fl_object_index == 0`, so it's still caught by the non-FLOBJ state=0 check and skipped. Also, V8 FLOBJs that passed through would try `hasObject(currentRoom, state)` → fail → `findObjectRoom()` → Room 3 → load PNG. But the **culling** code didn't exist yet, so they'd render over everything even when invisible.

---

#### Phase 3: v0.0.14-v0.0.16 — Verb Menu Activity Detection

**Attempt 12: `0448d2a8` — "only draw FLOBJs when verb menu is visible"** (v0.0.14)
- **What it did**: Added a loop over all verb slots to check if any verb has `curmode == 1` (visible). FLOBJs with state=0 are only processed if at least one verb is visible.
- **Why it failed**: The verb visibility check was too broad. Many games have permanent verbs (walk, stop) always visible. FLOBJs appeared in wrong rooms because "any verb visible" is almost always true. Also: the inventory background (non-FLOBJ) still got no special treatment.

**Attempt 13: `183d37de` — "block only full-screen FLOBJs in Step 2.5"** (v0.0.15)
- **What it did**: Replaced the verb visibility loop with a size-based approach. Full-screen FLOBJs (>90% of HD canvas) are blocked in Step 2.5, letting them go through drawVerbBitmap (Step 2.8) instead. Small FLOBJs (icons) continue to be rendered in Step 2.5.
- **Why it failed**: This was ALMOST correct, but the full-screen FLOBJ check also blocked the inventory background (obj_nr 114) because it has `fl_object_index == 0` and the code used `if (hdObjSurf.w >= hdW && hdObjSurf.h >= hdH && od.fl_object_index == 0)`. The FLOBJ-specific full-screen check used `od.fl_object_index && ... _game.version >= 7`. But the key problem: inventory icons (FLOBJs) would now pass through, but the culling didn't exist yet, so they'd render on top of the game world even when inventory was closed.

**Attempt 14: `ce5c4bf9` — "use _hdVerbDrawCount to detect verb menu activity"** (v0.0.16)
- **What it did**: Added `_hdVerbDrawCount` counter. `drawVerbBitmap()` increments it. Step 2.5 only processes FLOBJs if `_hdVerbDrawCount > 0` (meaning verbs were drawn this frame). Removed the full-screen FLOBJ size check.
- **Why it failed**: `_hdVerbDrawCount` was incremented EVERY time `drawVerbBitmap` was called, including for permanent verbs (like the walk cursor). It was reset to 0 at the end of each frame. The problem: `drawVerbBitmap` for inventory verbs might not be called in the same frame as `renderHDComposite`. Also: the inventory background (non-FLOBJ obj_nr 114) never gets through because the non-FLOBJ state=0 check blocks it.

---

#### Phase 4: v0.0.17-v0.0.19 — Size Filter / Always Render / Home Room

**Attempt 15: `02e18461` — "filter FLOBJs by size (>80% canvas = blocked)"** (v0.0.17)
- **What it did**: Replaced `_hdVerbDrawCount` check with size filter: FLOBJs with state=0 that are >80% of HD canvas are blocked. Small FLOBJs (icons) pass through.
- **Why it failed**: The 80% threshold blocked the inventory background (2560×1888 = 98% of 2560×1920). But it ALSO blocked inventory items that happen to have large transparent areas. Worse: without any verb visibility check, FLOBJs were processed in EVERY frame, loading textures pointlessly.

**Attempt 16: `e2c10bae` — "always render FLOBJs if HD exists"** (v0.0.18)
- **What it did**: Removed ALL FLOBJ size/visibility checks. V8 FLOBJs with state=0 ALWAYS pass through. If an HD texture exists, it's loaded and rendered. Added room-change debug output.
- **Why it failed**: This was TOO PERMISSIVE. Inventory FLOBJs from Room 3 (which exist as placeholders in EVERY room) would render in EVERY room at all times. You'd see cutlass icons, hook icons, etc. floating in the cannon room, on the beach, everywhere. The game became unplayable.

**Attempt 17: `3d0e80b4` — "FLOBJs only in their home room"** (v0.0.19)
- **What it did**: V8 FLOBJs with state=0 only pass through if `findObjectRoom(obj_nr) == _currentRoom`. Inventory items (home room = 3) only render in Room 3.
- **Why it failed**: The player opens the inventory while in Room 9. `_currentRoom = 9`. Inventory items' home room is 3. `findObjectRoom(obj_nr) = 3 != 9` → ALL inventory FLOBJs are skipped. The inventory is completely empty except for the 8-bit verb images. This was too restrictive because the inventory overlay must render regardless of the current room.

---

#### Phase 5: v0.0.20-v0.0.22 — Culling + getState()

**Attempt 18: `1716722c` — "rely on culling instead of home-room check"** (v0.0.20)
- **What it did**: REMOVED the home room check. Now ALL V8 FLOBJs pass through regardless of state and room. The **culling** code (introduced in this commit) is supposed to filter them: it checks if the 8-bit screen has visible foreground pixels in the object's area (diff against clean background).
- **Why it failed**: The culling checks the **Main VirtScreen** (`[kMainVirtScreen]`), but inventory content is on the **Verb VirtScreen** (`[kVerbVirtScreen]`). When the inventory is open, the Main VirtScreen still shows the room background with no inventory drawn on it. The clean background diff shows "no change" in the inventory icon areas → ALL inventory icons are culled. The inventory background (obj_nr 114, non-FLOBJ) is blocked by the state=0 check AND the layer size check. Result: nothing HD appears in the inventory.

**Attempt 19: `b48230c7` — "use getState() instead of _objs[].state"** (v0.0.22)
- **What it did**: Changed both FLOBJ and non-FLOBJ state checks to use `getState()` (reads `_objectStateTable[]`) instead of `od.state` (stale cached copy). This fixes the stale-state issue: when a script calls `putState(obj, non-zero)` mid-frame, `getState()` immediately sees it. Added explicit `continue;` for V8 FLOBJs with `objGlobalState == 0`.
- **Why it failed**: The getState() fix correctly reads the live state, BUT when the inventory is open, V8 FLOBJs get NON-ZERO states via `putState()`. The check `if (od.fl_object_index && objGlobalState == 0) { ... V8: still skip ... continue; }` now correctly skips them when closed and passes them when open. HOWEVER: the **inventory background** (obj_nr 114, non-FLOBJ) passes the state check when open, but the **layer size check** `if (hdObjSurf.w >= hdW && hdObjSurf.h >= hdH && od.fl_object_index == 0)` still catches it. And for FLOBJ icons that pass through, the culling still kills them because the Main VirtScreen diff shows nothing.

---

#### Phase 6: v0.0.23-v0.0.26 — Verb Timestamp Oscillation

**Attempt 20: `f3b5c898` — "FLOBJs drawn only when verb screen was recently updated"** (v0.0.23)
- **What it did**: REVERTED BACK to `od.state` for FLOBJ state check. Added `_hdVerbScreenTimestamp`. `drawVerb()` and `drawVerbBitmap()` set this timestamp. Step 2.5 only processes V8 FLOBJs if `_hdVerbScreenTimestamp + 2 >= _hdFrameCount` (verb screen updated within last 2 frames).
- **Why it failed**: The 2-frame tolerance was arbitrary and unreliable. Verb drawing and `renderHDComposite()` happen asynchronously — sometimes the timestamp would be 3 frames old when Step 2.5 ran. Missing frames caused flickering or missed overlays. The stale `od.state` check for non-FLOBJs also re-introduced the old state=0 bug for obj_nr 114.

**Attempt 21: `e9c042ab` — "trace drawVerb CALL and FLOBJ skip reason"** (v0.0.24-debug)
- **What it did**: Added debug logging for drawVerb and when FLOBJs are skipped due to stale verb timestamp. No behavioral change.
- **Learned**: Confirmed that drawVerb IS called for inventory verbs when the inventory opens, but the timestamp timing is unreliable.

**Attempt 22: `af4bd879` — "only set verb timestamp when verb is actually visible"** (v0.0.25)
- **What it did**: Added `vs->curmode && vs->verbid` guard to `_hdVerbScreenTimestamp` assignment in `drawVerb().` Previously it was set for ALL verb draws, including invisible ones.
- **Why it failed**: The timing problem wasn't about WHICH verbs set the timestamp, but about the frame-relative 2-frame window. Sometimes drawVerb runs, then later in the same frame renderHDComposite runs, and the timestamp matches. But on the next frame, no drawVerb runs (verb didn't change), so the timestamp becomes 1 frame stale → step 2.5 skips it → inventory HD disappears.

**Attempt 23: `75b1333a` — "always render V8 FLOBJs, remove verb timestamp tracking"** (v0.0.26, CURRENT)
- **What it did**: REMOVED the verb timestamp check entirely. V8 FLOBJs always pass through regardless. Removed all verb-based gating.
- **Why it STILL fails**: Same fundamental problem as v0.0.18 (always render) + v0.0.20 (culling). FLOBJs pass through but are killed by culling (Main VirtScreen diff). Non-FLOBJ inventory background (obj_nr 114) still killed by state=0 check and layer size check. The only difference from v0.0.18 is that the culling (added in v0.0.20) prevents the "icons in every room" problem, but also kills all inventory icons when they should be visible.

---

### 3. ROOT CAUSE PATTERN

All 23 attempts fail because they address **one** of these three issues but never all three:

| # | Problem | Attempts that addressed it | How they failed |
|---|---------|---------------------------|-----------------|
| **A** | Inventory bg (obj 114) not FLOBJ → no room fallback | 3,4,5,7,13,19 | All eventually blocked by the layer-size check `(hdObjSurf.w ≥ hdW && hdObjSurf.h ≥ hdH && fl==0)` |
| **B** | Culling kills FLOBJ icons because inventory is on Verb VirtScreen, not Main VirtScreen | 18,19,20,21,22,23 | Culling looks at Main VirtScreen diff, which shows no change when inventory is open |
| **C** | Verb overlay timing / detection unreliable | 8,9,12,14,15,20,21,22 | drawVerb/drawVerbBitmap timing relative to renderHDComposite is inherently race-prone |

No single fix ever simultaneously:
1. Gets the inventory background through the layer check
2. Prevents culling from killing inventory icons
3. Shows inventory content ONLY when actually visible

### 4. WHAT A REAL FIX NEEDS

A working solution must address at least **two** orthogonal concerns:

**For the inventory background (obj 114):**
- Allow full-screen non-FLOBJ objects through the layer check WHEN the inventory is known to be active
- Either: store it in `_hdVerbSurface` via drawVerbBitmap (requires drawVerbBitmap to be called with the right obj_nr)
- Or: add an exception in the layer check for known HUD objects (obj_nr 114)

**For inventory icons (FLOBJs):**
- The culling must be **bypassed** when the verb screen is active (inventory open)
- Or: switch to rendering inventory content from the **Verb VirtScreen** instead of the Main VirtScreen diff

**For both:**
- A reliable inventory-open signal is needed. `_hdVerbScreenTimestamp` from drawVerb is not reliable. Options:
  - Check `_objectStateTable[114] != 0` (inventory bg state)
  - Check `_objectStateTable` for any FLOBJ item != 0
  - Check `VAR(VAR_INVENTORY_OPEN)` or equivalent SCUMM variable
  - Check verb screen dimensions/content
