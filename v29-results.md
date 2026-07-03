## v0.0.29-debug — Results & Analysis

### What was tried

Three coordinated changes from v0.0.27, plus file-based debug logging:

1. **V8 FLOBJ pass-through** (restored from v0.0.26): All V8 FLOBJs with `od.state=0` are processed regardless of state.
2. **Universal room fallback**: Objects whose HD textures live in a different room (e.g. Room 3) are loaded from that room.
3. **Culling bypass for cross-room objects**: Objects loaded from a different room skip the diff-based culling.
4. **File-based logging**: `hd_debug.log` written to game directory showing every object entering Step 2.5 for first 120 frames.

### What happened (user report)

- **Difficulty selection screen**: Inventory HD assets visible where they shouldn't be.
- **After cutscene**: Inventory HD assets permanently overlaid on the game world, cannot be interacted with or closed.
- HD textures load and render — but ALWAYS visible, never hidden.

### Root cause confirmed by debug log at frame 120 (inventory open)

```
oi=3  obj=114  fl=3  odState=0  getState=0  pos=(0,0)  sz=(640x472)  name=inventory-bg-object
oi=22 obj=120  fl=7  odState=0  getState=0  pos=(0,0)  sz=(80x56)    name=two-balloons-icon-object
oi=2  obj=115  fl=2  odState=0  getState=0  pos=(0,0)  sz=(80x40)    name=increment-inventory-arrow
```

Two critical findings:

**A) `inventory-bg-object` (obj 114) is a FLOBJ, not a room object!**
- `fl=3` means `fl_object_index=3`, not 0 as previously assumed.
- All inventory-related objects (bg, icons, arrows) are FLOBJs with `fl>0`.
- My earlier assumption that obj 114 would need non-FLOBJ room fallback was wrong.

**B) `getState()=0` for ALL FLOBJs even when inventory is visible.**
- V8 COMI scripts do NOT use `putState()` / `_objectStateTable` for FLOBJ visibility.
- FLOBJ visibility is controlled through a different mechanism (object draw queue or SCUMM variables).
- My v0.0.27 approach (using `getState() != 0` as universal gate) would have skipped ALL inventory objects.

**C) FLOBJ positions in non-home rooms are `(0,0)`.**
- The FLOBJ placeholders in Room 9 have `pos=(0,0)` — they're not positioned correctly.
- Real positions are only set when the inventory screen is actually active.

### Why the fix failed

The three changes (room fallback, layer exception, culling bypass) all work correctly to SHOW the HD textures — but they remove every gate that previously prevented FLOBJs from rendering in wrong rooms/contexts. Since there is no working visibility signal for V8 FLOBJs, they render PERMANENTLY in every room.

### Next steps needed

A proper visibility signal for V8 FLOBJs is required:
1. Dump the full `_objectStateTable` to find ANY non-zero entries when inventory opens
2. Check SCUMM variables for inventory-open indicators
3. Check the object draw queue
4. Use Verb VirtScreen content as visibility signal
