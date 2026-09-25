# Object layer textures carry their mask through NUTcracker index 39

Status: fixed in the texture pass described below. The pipeline step is in the repo.

## Why layers are a separate case

`scripts/extract_all_raw.py` composites each layer with

```python
layer = resize_pil_image(*room_bg_image.size, 39, im, ImagePosition(x1=obj_x, y1=obj_y))
```

So a layer is the object placed on a full screen canvas, and it carries two masks:

1. the canvas mask: index 39, whose palette colour is an ordinary room colour. Measured: `(63,63,27)` for room 9, `(107,79,19)` for room 22, `(19,19,11)` for room 18. A colour based rule is therefore useless here, `scripts/mask_index.py` cannot find it by colour.
2. the object's own mask inside that canvas. Its index is the border dominant palette colour of the object source. Measured: glove index 5 covering 43.8% of the object, banjo index 5, lantern index 34.

Before the fix all 234 layer textures were fully opaque (0.0% transparent pixels), so the canvas area
was drawn as image content.

## What the fix does

`scripts/fix_mask_alpha.py --layer --object-hd <hd>/objects`:

- the object inside the canvas is an exact rectangle: bounding box of the non-39 area, fill grade
  1.000 on 13 of 14 sampled sources (the fourteenth, `0072_morts-lantern`, 0.972 because its art
  contains a pixel that equals index 39), and its size matches the object source size
- the alpha of the sibling object texture `<hd>/objects/<name>` is placed at that rectangle, alpha is
  only lowered
- everything outside the rectangle stays transparent
- the visible rim is filled from the inside (4 px, geometry, no colour test). The mask colour of a
  layer is a normal room colour, a colour test would hit real image pixels: for the treasure door
  339,972 pixels match the mask colour within tolerance, and they are artwork.

## Verification

- cross check against the sibling object texture, which is already reviewed and shipped: visible area
  of the layer against the object texture. First attempt with colour rules: median 1.7%, worst case
  43.5%. With the object texture alpha: **0.000% deviation in all 14 sampled files**, including the
  cases that failed before (`0022_clring-a-gb-banjo-object` was +52.3%, `0009_cannon-door-keyhole`
  +43.5%, `0072_morts-lantern` +32.6%).
- whole run over the layer folders in all four texture copies, per file abort rule unchanged (changed
  pixels must stay inside the dilated mask area)
- runtime: filling only the visible rim takes 0.9 s per file instead of 9 s

## Note for the engine

`hd_object_manager.cpp` line 249 states that layer files are pre-composited on the full background and
not suitable for runtime compositing, they would overwrite the whole screen. The code therefore only
loads the standalone object file. The layer textures are shipped for completeness and for a future
engine path that composites them over the HD background; with this fix they contain exactly the object
pixels for that purpose.
