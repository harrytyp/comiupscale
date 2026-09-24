# Object and layer textures ship with a visible magenta background

Status: fixed at texture level in HD Assets v1.0.5. The root fix in the pipeline is tracked in the follow up issues listed at the end.

## Symptom

Object textures carry a visible magenta area: a purple background on inventory icons, a purple fringe around in-game objects, and a magenta rim in the mask areas of system textures. It shows up as a purple background on inventory icons and as a purple fringe around room objects.

## Root cause

The magenta is the SCUMM mask that never became alpha. Three steps contribute:

**1. Extraction writes palette PNGs without transparency.**
`scripts/extract_all_raw.py` saves the images with `im.putpalette(palette)` and no alpha. Evidence from the shipped source pack (`comi-original-assets.zip`): every sampled object is mode `P` with `info['transparency'] is None`. The mask lives in one palette entry whose colour depends on the room palette, for example `(227,0,195)` magenta in the system room, `(107,199,27)` green outdoors, `(141,47,255)` violet elsewhere. Since no transparency is declared, every later step treats the mask colour as image content.

Note: the room header's `TRNS` index is not the object mask index. Room 3 reports `TRNS=5`, while the cursor texture's mask is index 255 (`scripts/check_trns_mask.py`).

**2. Upscaling bakes the mask into the RGB and blurs it.**
`scripts/upscale_esrgan.py`, `upscale_image()`:

```python
img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
if img.shape[2] == 4:
    rgb, alpha = img[:, :, :3], img[:, :, 3]
else:
    rgb = img
    alpha = np.full((img.shape[0], img.shape[1]), 255, dtype=np.uint8)
```

A palette PNG without a `tRNS` chunk comes back with 3 channels, so the `else` branch applies, alpha is fully opaque, and RealESRGAN upscales the mask colour as artwork. The later cleanup `out_np[alpha_4x < 128] = 0` cannot help because `alpha_4x` is 255 everywhere. That is why the mask appears as a soft magenta fringe pulled into the object edges. (The batch upscale ran with the RealESRGAN ncnn binary on the same palette inputs, which has the same effect.)

**3. The alpha step reconstructs the mask from a heuristic.**
`scripts/add_object_alpha_v6.py`, lines 119 to 141, derives the mask from the border dominant palette index:

```python
bg_idx = int(unique[np.argmax(counts)])
mask_orig = (orig_arr != bg_idx).astype(np.uint8) * 255
```

In a sample of 80 sources, index 255 is present in 39, and it is the border dominant index in only 31 of those, so the rest keep their mask colour. Where the source file is missing or is not mode `P`, the script falls back to `hd_out = np.array(hd.convert('RGBA'))` and keeps the HD alpha as is.

## How to tell mask from artwork

Colour alone is not enough, and a first attempt with a pure colour rule damaged textures (documented in the first comment). The shipped rule in `scripts/mask_index.py` accepts a palette entry only when both hold:

1. palette colour in the magenta family (`r > 200`, `b > 150`, `g < 60`)
2. the area of that index touches the image border (at least 10% of the border pixels)

Measured on the source pack:

| Source | Index | Share | Border share | Decision |
|---|---|---|---|---|
| `0003_system-cursor-icon_0000` | 255 | 96.1% | 100% | mask |
| `0003_lice-icon-object_0000` | 255 | 97.6% | 100% | mask |
| `0003_inventory-bg-object_0000` | 255 | 14.4% | 76.5% | mask |
| `0001_logo-logo-object_0000` | 33 | 14.9% | 0% | no mask, untouched |
| `0022_clring-a-balcony-door_0000` | - | - | - | no magenta entry, untouched |
| `0009_ramrod-object_0000` | - | - | - | no magenta entry, untouched |

## Fix shipped

HD Assets v1.0.5 contains the corrected `hd/objects` (and a full `hd_assets_part1.zip` with the same corrected folders). Tool: `scripts/fix_mask_alpha.py`, driven by `scripts/apply_mask_alpha_all.sh`.

Result: 366 of 600 object textures changed, all `0003_*` (room 3 system UI, inventory background, inventory icons). Opaque magenta in those files went from 1,811,664 to 912 pixels. Logo, room objects and object layers untouched, 0 aborts.

Verification per file and per run is described in `docs/TEXTURE_MASK_PIPELINE.md`.

## Follow ups

- Extraction and upscale: write the mask as alpha or `tRNS`, build the upscaler alpha from it, pre-fill before upscaling.
- Object layers: extend the mask rule to NUTcracker index 39.
