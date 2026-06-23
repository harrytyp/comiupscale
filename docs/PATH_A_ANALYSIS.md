# Path A Investigation: Full HD Patching for COMI Upscaled

This document details every coordinate-bearing data structure in "The Curse of
Monkey Island" (SCUMM V8) that must be patched to support 4x upscaled assets
inside the game engine.

---

## 1. RMHD — Room Header

**Location:** `ROOM/RMHD` in each `LFLF_{room}` chunk  
**Size:** 32 bytes  
**Format (V8, 24 byte payload):**

```
struct RoomHeaderV8 {
    uint32 version;       // always 0x320 (800)
    uint32 width;         // e.g. 640
    uint32 height;        // e.g. 480
    uint32 numObjects;    // number of objects in room
    uint32 zbuffers;      // z-buffer count
    uint32 transparency;  // transparency mode
};
```

**Must scale:** `width` and `height` → multiply by 4.  
**Example:** `640×480` → `2560×1920`

**Impact:** The engine allocates render buffers based on these dimensions.

---

## 2. BOXD — Walkbox Definitions

**Location:** `ROOM/BOXD` in each room  
**Size:** 8 + 4 + (numBoxes × 52) bytes  
**Format (V8):**

```cpp
struct BoxV8 {                            // 52 bytes each
    int32 ulx, uly;   // upper-left  corner
    int32 urx, ury;   // upper-right corner
    int32 lrx, lry;   // lower-right corner
    int32 llx, lly;   // lower-left  corner
    uint32 mask;      // palette mask
    uint32 flags;     // walkbox behavior flags
    uint32 scaleSlot; // scale slot index
    uint32 scale;     // scale value
    uint32 unk2;      // unknown
};
```

The count is stored as `uint32` right after the chunk header (8 bytes).

**Must scale:** All 8 coordinate fields (`ulx`, `uly`, `urx`, `ury`, `lrx`, `lry`, `llx`, `lly`) → multiply by 4. Coordinate value `-32000` (0xFFFF8300) indicates an inactive box — do NOT scale these.

**Example:** Box `(209,142)-(233,142)-(287,1)-(259,1)` would become `(836,568)-(932,568)-(1148,4)-(1036,4)`

**Impact:** Characters walk on the wrong areas if not scaled.

---

## 3. BOXM — Walkbox Connectivity Matrix

**Location:** `ROOM/BOXM` in each room  
**Format:** A matrix of 0xFF-terminated byte sequences. Each box's entry lists the indices of adjacent/reachable boxes, ending with 0xFF.

**Example from room 1:** `00 00 00 FF 01 01 01 FF`

**Does it need scaling?** No — it contains box indices, not coordinates. Only the number of entries matters, and it stays the same.

---

## 4. SCAL — Scale Data

**Location:** `ROOM/SCAL` in each room  
**Size:** 8 + (numScaleSlots × ?) bytes  
**Format (V8):** Seems to be all zeros for most rooms in COMI. The SCUMM V8 engine uses scale slots (defined in the room scripts) rather than the SCAL table.

**Does it need scaling?** The SCAL chunk may contain scale values (0-255) but in COMI (V8) it appears unused for most rooms. Needs investigation per room, but unlikely to need coordinate scaling.

---

## 5. OBIM → IMHD — Object Image Headers

**Location:** `ROOM/OBIM_{id}/IMHD`  
**Size:** Variable (V8 format is ~80+ bytes)  
**Format (V8, from proom.py):**

```python
struct IMHDv8 {
    char name[40];        // null-terminated object name
    uint32 version;       // always 0x000003E8?
    uint32 imageCount;    // number of images
    int32  x;             // object X position
    int32  y;             // object Y position
    int32  width;         // object width
    int32  height;        // object height
    uint32 actorDir;      // actor direction
    uint32 flags;         // flags
    // ... hotspot data follows
};
```

**Must scale:** `x`, `y`, `width`, `height` → multiply by 4.

**Impact:** Objects appear at wrong screen positions, clickable areas misaligned with backgrounds.

---

## 6. OBCD → CDHD — Object Code Headers

**Location:** `ROOM/RMSC/OBCD/CDHD`  
**Format:** Contains object code header data including bounding boxes and flags for scripted object behavior.

May contain coordinate data for object interaction boxes. Needs further investigation per room.

---

## 7. SCRP — Room Scripts (Bytecode)

**Location:** `ROOM/SCRP_{id}`  
**Size:** Variable, thousands of bytes per room  
**Format:** SCUMM V8 bytecode (opcodes + arguments)

This is the **hardest challenge**. Scripts contain embedded pixel coordinates in
various opcodes. Some are immediate values (hardcoded in the bytecode stream),
others are runtime values pushed onto the stack.

### Opcodes with coordinate-related arguments:

| Opcode | Args | What it does |
|--------|------|-------------|
| `o6_panCameraTo` | `uint16 x` | Pans camera to X position |
| `o6_setCameraAt` | `uint16 x` | Sets camera at X position |
| `o6_walkActorTo` | actor, x, y | Walks actor to (x,y) |
| `o6_putActorAtXY` | actor, x, y | Places actor at (x,y) |
| `o6_drawObjectAt` | object, x, y | Draws object at (x,y) |
| `o6_setBlastObjectWindow` | ? | Sets blast window coordinates |
| `o6_distPtPt` | x1,y1,x2,y2 | Distance between points |
| `ROOM_SCROLL` | x, y | Room scroll offset |
| `ROOM_SCREEN` | x, y | Room screen coordinates |
| `ROOM_SCALE` | y1, y2, scale, ? | Room scale parameters |

Most of these take their coordinates via **stack operations** — the X and Y
values are pushed as separate `pushWord`/`pushByte` instructions before the
opcode call. This makes naive binary patching impossible.

**To correctly scale script coordinates, you would need:**
1. A full SCUMM V8 bytecode disassembler/reassembler
2. Understanding which push operations feed into coordinate-consuming opcodes
3. A bytecode rewriter that multiplies coordinate values by 4

This is essentially a **script compiler/decompiler** — a major engineering
effort comparable to what the ScummVM team built for `descumm`.

---

## 8. MAXS — Maximum Values Table

**Location:** Top-level chunk in LA0  
**Format:** Contains game-wide maximum values including maximum X/Y dimensions, maximum number of objects, etc.

**Must scale:** Any coordinate-related maximum values.

---

## Summary: Work Required for Path A

| Component | Complexity | Effort | Notes |
|-----------|-----------|--------|-------|
| **RMHD** (room dimensions) | Low | ~1 hour | Simple uint32 multiplication in 93 rooms |
| **BOXD** (walkboxes) | Low | ~2 hours | Multiply 4-8 coordinate pairs per box, watch for -32000 sentinel |
| **BOXM** (box matrix) | None | 0 | Contains indices, not coordinates |
| **SCAL** (scale table) | Low | ~1 hour | Mostly unused in COMI, verify per room |
| **IMHD** (object positions) | Low | ~2 hours | Multiply x/y/width/height for ~600 objects across 93 rooms |
| **OBCD/CDHD** (code headers) | Medium | ~4 hours | Needs reverse engineering per room |
| **SCRP** (scripts) | **Very High** | **Weeks–months** | Full bytecode analysis, disassembler, rewriter needed |
| **MAXS** (max values) | Low | ~30 min | Simple scaling |

### The Script Problem

There are **thousands of scripts** across 93 rooms. Each script is a sequence
of SCUMM V8 bytecodes with embedded values. Some values are coordinates, some
are indices, some are string offsets, some are jump targets.

Without a full bytecode rewriter, you would need to:
1. Manually identify every coordinate value in every script
2. Understand the context (is this value a coordinate or something else?)
3. Multiply only coordinate values

This is extremely error-prone and would likely introduce game-breaking bugs.

### Recommended Approach

**Short term:** Write a Python script using NUTcracker's resource tree that
patches all the LOW-complexity items (RMHD, BOXD, IMHD). This handles the
structural coordinate data and gives ~80% of the visual correctness.

**For scripts:** Instead of patching SCUMM bytecode (which is extremely
complex), consider an alternative approach:

> **Hybrid Path:** Upscale → encode at 4x → patch room headers & walkboxes →
> keep scripts at original coordinates → run in ScummVM with the "adjust
> coordinates at runtime" approach.

ScummVM's SCUMM engine could theoretically be patched to multiply all incoming
script coordinates by 4 (or divide screen coordinates by 4 internally). This
would be a much smaller change to ScummVM itself (maybe 50-100 lines of C++
in the opcode handlers) than trying to rewrite all game scripts.

**Alternatively:** Skip the game engine entirely and use the upscaled assets
for:
- HD cutscene videos (rebuild from upscaled frames via ffmpeg)
- Reference art / wallpapers
- A fan-made "HD version" using a different renderer
