# Object layer textures carry their mask through NUTcracker index 39

Follow up to #22. The 234 texture files in `hd/objects_layers` still contain a mask colour wherever the layer composite is transparent, because the mask step skips them on purpose.

## Why they are skipped

`scripts/extract_all_raw.py` composites each layer with

```python
layer = resize_pil_image(*room_bg_image.size, 39, im, ImagePosition(x1=obj_x, y1=obj_y))
```

The `39` is the index NUTcracker treats as transparent for that composite. It is not a magenta palette entry, and the palette colour behind index 39 is whatever the room palette happens to hold there. `scripts/mask_index.py` therefore finds no mask and leaves the file alone.

Measured example, `objects_layers/0000_clring-a-balcony-door_0000.png` (1072x480): index 39 covers 94.8% of the image and 100% of the border, so structurally it is a clean mask.

## Fix

Extend the mask rule for the layer folder: accept index 39 when its area touches the image border, in addition to the magenta family rule. Then run the same step:

```
python3 scripts/fix_mask_alpha.py --hd <hd>/objects_layers --src-zip comi-original-assets.zip --prefix objects_layers --apply
```

Verification is the same as in #22: changed pixels must stay inside the dilated mask, changed files grouped by room must match the intended group, residual magenta measured afterwards.

Not urgent: the layers are drawn only where a room background is replaced, and the visible complaints so far came from the object textures.
