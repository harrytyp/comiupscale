# Object and layer textures ship with a visible magenta background

## Symptom

391 of the 600 object textures and 30 of the 234 object layer textures in HD Assets v1.0.4 carry a visible magenta area. It shows up as a purple background on inventory icons and as a purple fringe around in-game objects (balcony door, rubber tree). The cursor texture `0003_system-cursor-icon` also carries mask magenta, but the engine draws the pointer from the SD cursor image (`useIm01Cursor` in `cursor.cpp`), so that file only matters if the HD cursor path is used.

## Root cause

The magenta is the SCUMM mask that never became alpha. Three steps contribute:

**1. Extraction writes palette PNGs without transparency.**
`scripts/extract_all_raw.py` saves the object images with `im.putpalette(palette)` and no alpha. Evidence from the shipped source pack (`comi-original-assets.zip`): every sampled object is mode `P` with `info['transparency'] is None`. The mask lives in palette index 255, and the colour of that index depends on the room palette: `(227,0,195)` magenta in the system room, `(107,199,27)` green outdoors, `(141,47,255)` purple elsewhere. Since no transparency is declared, every later step treats the mask colour as image content.

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

A palette PNG without a `tRNS` chunk comes back with 3 channels, so the `else` branch applies, alpha is fully opaque, and RealESRGAN upscales the mask colour as artwork. The later cleanup `out_np[alpha_4x < 128] = 0` cannot help because `alpha_4x` is 255 everywhere. That is why the mask does not appear as a flat magenta block but as a soft magenta fringe pulled into the object edges. (The batch upscale itself ran with the RealESRGAN ncnn binary on the same palette inputs, which has exactly the same effect: with no declared transparency the mask colour is ordinary RGB content.)

**3. The alpha step reconstructs the mask from a heuristic.**
`scripts/add_object_alpha_v6.py`, lines 119 to 141, derives the mask from the source using the border dominant palette index:

```python
bg_idx = int(unique[np.argmax(counts)])
mask_orig = (orig_arr != bg_idx).astype(np.uint8) * 255
```

That proxy is only correct when the mask index happens to dominate the border. In a sample of 80 source files, index 255 is present in 39, and it is the border dominant index in only 31 of those, so the remaining files keep their mask colour. Where the source file is missing or is not mode `P`, the script falls back to `hd_out = np.array(hd.convert('RGBA'))` and keeps the HD alpha as is, which still contains the magenta.

## Scope in v1.0.4

- 391 of 600 object textures, 1.985.662 opaque mask pixels
- 30 of 234 object layer textures
- heaviest cases: `0003_inventory-bg-object_0000.png` 75986 px, `0001_logo-logo-object_0000.png` 40566 px, `0003_lice-icon-object_0001.png` 26188 px, `0022_clring-a-balcony-door_0000.png` 14369 px, `0022_other-tree-anim-object_0000.png` 14089 px

## Fix shipped (texture level)

HD Assets **v1.0.5** contains the corrected `hd/objects` and `hd/objects_layers`. Tool used: `scripts/add_object_alpha_v7.py`.

- derives the mask from the source when available (palette index, alpha channel, or magenta detection) instead of keeping the HD alpha
- removes hard mask magenta (`r > 140`, `b > 120`, `g < 100`)
- removes the soft magenta fringe only within 6 px of a hard magenta pixel, so genuine pink artwork survives. Example: `0028_pink-chest-anim-object_0000.png`, whose own pink is palette index 229, RGB `(255,163,215)`. An earlier, wider rule removed 30744 pixels there, the shipped one removes 921 and leaves the artwork intact.

Verification per file, recomputed independently of the tool's own report:

- changed pixels are a subset of the mask definition
- all non mask pixels are byte identical to the previous file
- black and white pixel counts unchanged (for example 1101 black and 941 white in the cursor texture, before and after)
- after the pass: 0 files with saturated magenta in 4 texture folders x 600 objects and 4 x 234 layers

## Proper fix, still open

1. Extraction: write the mask index as alpha, or add a `tRNS` chunk for index 255, so the mask never enters the RGB pipeline. `scripts/extract_all_raw.py`, `read_objects` path.
2. Upscaling: for palette inputs, build the alpha from index 255 before upscaling instead of assuming fully opaque. `scripts/upscale_esrgan.py`, `upscale_image()`.
3. Alpha step: use the known mask index (`mask = (orig_arr != 255)`) instead of the border dominant index, or drop the step once 1 and 2 are done. `scripts/add_object_alpha_v6.py`.
4. Better than any post processing: fill the masked areas with the neighbouring colour before upscaling, then the upscaler has no magenta to blur in the first place.
