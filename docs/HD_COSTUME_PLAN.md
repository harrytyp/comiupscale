# Plan: Fix HD Costume Animation

## Problem
The HD costume manager tries to load individual PNG frames by `a->_frame`, 
but `a->_frame` never changes (always 6 for the sword). The actual animation 
cel cycling happens inside the AKOS bytecode interpreter (AKSQ processing), 
which we don't hook into.

The SD system works because it:
1. Takes `a->_frame` → computes AKSQ index via `anim = dir + frame * 8`
2. Looks up AKCH[anim] → gets offset into AKSQ data
3. Processes AKSQ bytecode → determines which cel (0-4) to display
4. Decodes cel data → draws to 8-bit virtual screen

The HD system reads `a->_frame` (constant 6) and only loads one PNG.

## Solution: Two-phase approach

### Phase 1: Intercept SD costume output (quick win)
Instead of trying to replicate the AKSQ cel selection, intercept the 
SD-rendered 8-bit costume output AFTER it was correctly processed by the AKOS.

**How (gfx.cpp, Step 2.6 replacement):**
1. Remove the current HD costume PNG lookup (hasCostume/loadCostume)
2. Instead, for each actor with a costume:
   a. Let the SD system fully render the costume to the 8-bit virtual screen
   b. Read the actor's bounding box from the virtual screen (actor position ± cost size)
   c. Nearest-neighbor upscale that 8-bit region 4x using the current palette
   d. Write the 4x result to `_hdComposite` at the correct HD position
3. The SD system already handles all AKSQ cel cycling, positioning, layers

**Pros:** Full animation, correct position, correct transparency (palette index 
0 handling), works for ALL costumes, immediate result
**Cons:** No RealESRGAN crispness — same 4x pixel-art quality as the background 
compositing (step 2)

### Phase 2: Add RealESRGAN frames back (when available)
Once all frames are extracted and upscaled:
1. For each actor, record which AKSQ cel index is being displayed
2. On the next frame, pre-load the HD PNG for that cel
3. Composite the HD PNG over the upscaled SD output
4. Only applies to cels where HD PNG exists — all others use SD upscale

## Implementation order
1. Replace hasCostume/loadCostume calls with SD interception
2. Implement the 8-bit→HD upscale for each actor's bounding box
3. Verify all costume animations play correctly
4. Add RealESRGAN frame overlay as optional enhancement

## Key code locations
- gfx.cpp, line ~1414: Current HD costume overlay loop (Step 2.6)
- akos.cpp, line 93: `costumeDecodeData` — AKSQ processing
- actor.cpp, line 2522: `drawActorCostume` — SD rendering entry point
- base-costume.h, line 160: `drawCostume` — draws to virtual screen
