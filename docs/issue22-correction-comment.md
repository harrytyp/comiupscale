## Correction: colour based removal was unsafe, the shipped step is mask based now

Two problems with the first iteration, both fixed:

**1. The scope was too wide.** The first pass treated every pixel in the magenta family as mask. That is wrong for the logo and for room object textures:

- `0001_logo-logo-object_0000.png`: the magenta entry sits *inside* the image (border share 0), it is not the sprite mask.
- `0022_clring-a-balcony-door_0000.png`: the violet awning and sky are artwork. A pure colour rule removes 43182 pixels of real image there.
- `0028_pink-chest-anim-object_0000.png`: its own pink is palette index 229, RGB `(255,163,215)`.

Result of the correction: no logo texture and no room object texture is touched any more. The room object and logo textures were restored to their original state.

**2. The rule is structural now, not chromatic.** `scripts/mask_index.py` only accepts a palette entry as mask when both hold: the palette colour is in the magenta family (`r>200`, `b>150`, `g<60`) AND the area touches the image border (at least 10 percent of the border pixels). Measured on the shipped source pack:

| Source | Index | Share | Border share | Decision |
|---|---|---|---|---|
| `system-cursor-icon_0000` | 255 | 96.1% | 100% | mask |
| `lice-icon-object_0000` | 255 | 97.6% | 100% | mask |
| `inventory-bg-object_0000` | 255 | 14.4% | 76.5% | mask |
| `logo-logo-object_0000` | 33 | 14.9% | 0% | no mask, untouched |
| `clring-a-balcony-door_0000` | - | - | - | no magenta entry, untouched |
| `ramrod-object_0000` | - | - | - | no magenta entry, untouched |

The rule reproduces the manual review outcome: room 3 system and inventory textures are corrected, logo and room objects are left alone.

**Pipeline step.** `scripts/fix_mask_alpha.py`:

- mask from the source at 1x, upscaled with NEAREST (the game mask is binary, a soft edge left semi transparent magenta pixels behind)
- alpha is only ever lowered, never raised
- RGB inside the mask and in the 2 px band just inside it is filled from the neighbouring pixels, but only where the colour is still in the magenta family. Everything else is artwork and stays
- per file abort rule: changed pixels must stay inside the 2 px dilated mask area, otherwise the file is written unchanged and reported

Run: `bash scripts/apply_mask_alpha_all.sh` (`scripts/fix_mask_alpha.py` per folder), covering all four texture copies (linux, game, windows, fork).

**Result of the corrected pass**

- 366 of 600 object textures changed, all of them `0003_*` (room 3 system, inventory background, inventory icons). No other room, no logo.
- opaque magenta in those files: 1811664 to 912 pixels
- object layers untouched (they are composites of room objects, 0 files changed)
- 0 aborts, meaning no file had changes outside its mask

**Release.** `hd_assets_v1.0.5` was replaced with the corrected pack (same file name, `hd_textures_v1.0.5_objects_layers.zip`, 123.1 MB). Anyone who downloaded the first upload should load it again.
