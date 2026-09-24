HD Assets v1.0.5 carries the corrected object textures and a full part 1 for fresh installs.

## What is in this release

| File | Contents | Size |
|------|----------|------|
| `hd_assets_part1.zip` | backgrounds, objects, objects_layers, fonts | ~537 MB |
| `hd_textures_v1.0.5_objects_layers.zip` | objects, objects_layers only, for people who already have v1.0.4 loaded | ~123 MB |

Use part 1 for a fresh install. Use the small pack if you already extracted v1.0.4 and only want the corrected textures, it replaces `hd/objects` and `hd/objects_layers`.

Costumes stay in HD Assets v1.0.4 (`hd_assets_part2.zip` to `hd_assets_part4.zip`), they are unchanged.

Applying: extract into your game folder so the `hd/` folders are replaced or merged. For the small pack, only `hd/objects` and `hd/objects_layers` are touched.

## What was wrong

The SCUMM mask of the object images was upscaled as image content instead of being turned into alpha, so 366 room 3 system and inventory textures carried a visible magenta background or a magenta fringe around inventory icons, the inventory background, the cursor and the dialog arrows. The extracted source PNGs declare no transparency at all, and the alpha step reconstructed the mask from a border heuristic that misses.

Analysis, evidence and code references: Issue #22. Pipeline documentation: `docs/TEXTURE_MASK_PIPELINE.md`.

## Scope, and why it is limited on purpose

Only textures whose source palette proves the mask are touched. Rule in `scripts/mask_index.py`: the mask is the palette entry whose colour is in the magenta family AND whose area touches the image border.

- processed: 366 of 600 object textures, all in room 3. Opaque magenta in those files: 1,811,664 to 912 pixels.
- untouched on purpose: the logo texture and all room object textures. Their violet is artwork, not mask. An earlier upload removed those pixels and damaged the textures, that was corrected.
- untouched: object layers (composites of room objects, tracked in Issue #24).

## Reproduce

```
python3 scripts/fix_mask_alpha.py --hd <hd>/objects --src-zip comi-original-assets.zip --apply
bash scripts/apply_mask_alpha_all.sh            # all four texture copies
```

Per file the step verifies that changed pixels stay inside the 2 px dilated mask, otherwise the file is left alone and reported. After the run the changed files are grouped by room and compared with the approved group.

## Follow ups

- Issue #23: extraction should write the mask as alpha (root fix, so this cannot come back)
- Issue #24: object layer mask through NUTcracker index 39
