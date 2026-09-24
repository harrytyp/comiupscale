Texture pack with the magenta mask removed from the object textures. This release was replaced on 2026-09-24, the first upload had over-cleaned textures. Root cause and analysis: Issue #22.

## Contents

| Folder | Files | State |
|--------|-------|-------|
| `hd/objects` | 600 textures | 366 corrected (room 3 system, inventory and icon textures) |
| `hd/objects_layers` | 234 textures | unchanged |

123.1 MB in total. Everything else (backgrounds, fonts, costumes, videos) is unchanged, keep those from HD Assets v1.0.4.

## How to apply

Extract the archive into your game folder so that `hd/objects` and `hd/objects_layers` are replaced. It is a drop in replacement for those two folders inside `hd_assets_part1.zip`.

## Scope, and why it is limited on purpose

Only textures whose source palette proves the mask are touched. Rule in `scripts/mask_index.py`: the mask is the palette entry whose colour is in the magenta family AND whose area touches the image border.

- processed: 366 textures, all in room 3 (system UI, inventory background, inventory icons). Opaque magenta went from 1811664 to 912 pixels.
- skipped on purpose: the logo texture and all room object textures. Their purple is artwork, not mask. An earlier version of this pack removed those pixels and damaged the textures. That is corrected in this upload.
- object layers are untouched, they are composites of room objects.

## Reproduce

```
python3 scripts/fix_mask_alpha.py --hd <hd>/objects --src-zip comi-original-assets.zip --apply
```

Per file the step verifies that changed pixels stay inside the 2 px dilated mask. If a pixel outside changes, the file is left alone and reported. Independent recount after the run: changed files grouped by room (must be the approved group), residual magenta measured.
