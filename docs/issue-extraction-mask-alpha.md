# Extraction should write the object mask as alpha (root fix for the magenta backgrounds)

Follow up to #22. The shipped texture fix removes the mask colour after upscaling. This issue tracks the fix at the source, so the problem cannot come back with the next pipeline run.

## Problem

`scripts/extract_all_raw.py` writes the object and layer images as 8-bit palette PNGs with `im.putpalette(palette)` and no transparency information. Every sampled file in the released source pack is mode `P` with `info['transparency'] is None`.

Consequences downstream:

1. `scripts/upscale_esrgan.py`, `upscale_image()`: `cv2.imread(path, cv2.IMREAD_UNCHANGED)` returns 3 channels for a palette PNG without a `tRNS` chunk, so the code takes `alpha = np.full(..., 255)`. RealESRGAN then upscales the mask colour as artwork and blurs it into the object edges. The cleanup `out_np[alpha_4x < 128] = 0` cannot help, `alpha_4x` is 255 everywhere.
2. `scripts/add_object_alpha_v6.py` reconstructs the mask from the border dominant palette index (`mask_orig = (orig_arr != bg_idx)`). Measured on a sample of 80 sources this proxy is right in only 31 of the 39 files that carry a mask index. Where the source is missing or is not mode `P`, the code keeps the HD alpha, magenta included.

## Fix

In the extraction step:

- write the object and layer PNGs with the mask index declared, either as a `tRNS` chunk (`im.save(path, transparency=idx)`) or as RGBA with alpha 0 at the mask index. The mask index comes from `scripts/mask_index.py` (magenta family plus border contact) or, better, from the decoder itself: the unfilled value of the BOMP decode.
- make `upscale_image()` build the alpha from that mask instead of assuming fully opaque, so the upscaler never sees the mask colour as content.
- optionally pre-fill the masked areas with the neighbouring colour before upscaling. Then a soft mask edge blends object colours instead of magenta, which removes the halo at the root.
- `add_object_alpha_v6.py` can then go away, or use `mask = (orig_arr != mask_idx)` instead of the border heuristic.

Note: `header.transparency` from the room settings is **not** the object mask index. Measured for room 3: the room header reports `TRNS=5` (palette colour `(107,199,27)`), while the cursor texture's mask is index 255. `scripts/check_trns_mask.py` documents that dead end.

## Acceptance

- re-extract a room, check that its object PNGs carry transparency information
- upscale one object and confirm its HD texture has no magenta in the mask area and no magenta fringe
- run `scripts/fix_mask_alpha.py` afterwards; expect it to change nothing
