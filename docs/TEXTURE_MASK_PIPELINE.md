# HD texture pipeline and the object mask

This page documents how the HD object textures are produced, where the object mask
comes from, and how a mask problem is fixed reproducibly. It exists because a
one-off colour filter once damaged textures (see Issue #22).

## Pipeline order

| Step | Script | Output |
|------|--------|--------|
| 1. Extract | `scripts/extract_all_raw.py` (NUTcracker) | 1x palette PNGs: backgrounds, objects, objects_layers, fonts, costumes |
| 2. Upscale | `scripts/upscale_esrgan.py` / RealESRGAN ncnn | 4x PNGs, RGB plus an alpha contour |
| 3. Alpha from source | `scripts/add_object_alpha_v6.py` (legacy) | alpha from the border dominant palette index |
| 3b. Alpha from mask | `scripts/fix_mask_alpha.py` (current) | alpha from the proven mask, magenta band filled |
| 4. Manifest | `scripts/hd_manifest_gen.py` | load list for the fork |
| 5. Package | `scripts/build_texture_pack.py` | release ZIPs |

The engine loads the result from `hd/objects` and `hd/objects_layers`
(`hd_object_manager.cpp`, path pattern `%04d_%s_%04d.png` = room, name, state).

## Where the mask lives

The extracted sources are 8-bit palette images with no transparency at all
(`info['transparency'] is None`). The mask is a palette entry. Its colour depends on
the room palette, and it is not always the same index:

| Source | Mask index | Palette colour | Area | Border share |
|--------|-----------|----------------|------|--------------|
| `0003_system-cursor-icon_0000` | 255 | (227,0,195) | 96.1% | 100% |
| `0003_lice-icon-object_0000` | 255 | (227,0,195) | 97.6% | 100% |
| `0003_inventory-bg-object_0000` | 255 | (227,0,195) | 14.4% | 76.5% |
| `0001_logo-logo-object_0000` | 33 (not a mask) | (203,0,223) | 14.9% | 0% |
| `0022_clring-a-balcony-door_0000` | none | - | - | - |

Because the mask colour equals a magenta in most room palettes, an upscaled texture
shows a magenta background where the mask was never turned into alpha. The same
magenta also appears blurred into the object edges, because the upscaler treats it
as image content.

## The rule that decides

`scripts/mask_index.py` returns a mask index only if **both** conditions hold:

1. the palette colour is in the magenta family (`r > 200`, `b > 150`, `g < 60`), and
2. the area of that index touches the image border (at least 10% of the border pixels).

A magenta area that sits entirely inside the image is artwork (the logo case), and a
texture whose palette has no magenta entry at all has no mask to remove (the room
object case). The rule reproduces the manual review outcome exactly.

## The step

`scripts/fix_mask_alpha.py --hd <folder> --src-zip comi-original-assets.zip --apply`

- mask from the 1x source, upscaled with NEAREST (the game mask is binary, a soft
  edge leaves semi transparent magenta pixels behind)
- alpha is only lowered, never raised
- RGB inside the mask and in the 2 px band just inside it is filled from the
  neighbouring pixels, but only where the colour is still in the magenta family;
  every other colour is artwork and stays untouched
- abort rule per file: if a changed pixel lies outside the 2 px dilated mask, the
  file is written unchanged and reported

`scripts/apply_mask_alpha_all.sh [BACKUP_DIR]` runs the step over all four texture
copies (linux release, game folder, windows release, fork) and can restore a known
state first. `scripts/restore_pristine_textures.sh` restores from the backups.

## Verification

- per file inside the step: change set must be a subset of the dilated mask
- per run outside the step: group the changed files by room and compare with the
  approved group, measure the residual magenta, expect zero aborts
- review sheets: `scripts/asset_review_sheets.py --before <backup> --after <hd> --out <dir>`
  writes before and after contact sheets per asset type

Last run: 366 of 600 object textures changed, all `0003_*` (room 3 system UI,
inventory background, inventory icons). Opaque magenta in those files went from
1,811,664 to 912 pixels. Logo and room objects untouched, object layers untouched,
0 aborts.

## Object layers (the second step)

`hd/objects_layers` is a different case and gets its own mode (`--layer --object-hd <hd>/objects`).

A layer is the object placed on a full screen canvas. It carries two masks:

1. the canvas mask: NUTcracker index 39, set by `resize_pil_image(*room_bg_image.size, 39, im, ...)`
   in the extraction. Its palette colour is an ordinary room colour (measured `(63,63,27)` for room 9,
   `(107,79,19)` for room 22), so a colour test is useless here.
2. the object's own mask inside that canvas.

The object area inside the canvas is an exact rectangle (checked on 14 sources, fill grade 1.000, and
its size matches the object source size, for example 176x152 for `0022_clring-a-balcony-door`), and
the corresponding object texture is already reviewed and shipped. So the layer step does not guess:

- find the object rectangle as the bounding box of the non index 39 area
- take the alpha of the sibling object texture (`<hd>/objects/<name>`) and place it at that rectangle
- everything outside stays transparent, alpha is only lowered

Result: the layer shows exactly the pixels the object texture shows. Verified on 14 files across 7
rooms: visible area of layer against object texture, deviation 0.000% in all 14 cases.

Runtime note: fill the visible rim only. Filling every transparent pixel of a 2560x1920 image cost
about 9 s per file, restricting the fill to the rim costs 0.9 s.

## Tools that must not be used

`scripts/add_object_alpha_v7.py` is deprecated. It decided by colour alone and
removed real violet from the logo and from room object textures.

## Open work

- Issue about the extraction: write the mask as alpha or as a `tRNS` chunk so the
  mask never enters the RGB pipeline, and pre-fill masked areas before upscaling.
- Issue about the object layers: they carry their mask through NUTcracker index 39
  (border share 100%), which is not a magenta entry, so `mask_index.py` skips them
  on purpose.
