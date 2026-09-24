Texture pack with the magenta mask removed from the object and object layer textures. This fixes the purple background on inventory icons, the purple fringe around in-game objects and the purple rim on the verb coin cursor. Root cause and full analysis: Issue #22.

## Contents

| Folder | Files | State |
|--------|-------|-------|
| `hd/objects` | 600 textures | corrected |
| `hd/objects_layers` | 234 textures | corrected |

122.5 MB in total. Everything else (backgrounds, fonts, costumes, videos) is unchanged, keep those from HD Assets v1.0.4.

## How to apply

Extract this archive into your game folder so that `hd/objects` and `hd/objects_layers` are replaced. It is a drop in replacement for those two folders inside `hd_assets_part1.zip`, so you do not need to download the 512 MB part again.

## What was wrong

391 object textures and 30 layer textures carried a visible magenta background or fringe. The SCUMM mask (palette index 255, colour `(227,0,195)` in most room palettes) was upscaled as image content instead of being turned into alpha, because the extracted source PNGs declare no transparency at all.

## Verification

Every corrected texture was checked twice, independently of the tool's own report:

- changed pixels are a subset of the mask definition (hard magenta plus a fringe within 6 px of it)
- all non mask pixels are byte identical to the previous file
- black and white pixel counts unchanged, for example 1101 black and 941 white in the cursor texture before and after
- after the pass: 0 files with saturated magenta in 4 texture folders x 600 objects and 4 x 234 layers

## Files

- `hd_textures_v1.0.5_objects_layers.zip` (122.5 MB)
