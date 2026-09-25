The mask is now written as transparency at extraction time, so the upscaler cannot mistake it for image content any more. Commit `d4084491`.

**1. Extraction writes the mask as tRNS**

`scripts/extract_all_raw.py` saves object and layer PNGs with the mask index as `transparency`, so every later reader sees the masked area as transparent instead of opaque RGB.

The index is measured per room instead of guessed (shared rule in `scripts/mask_detect.py`, used by both the pipeline and the test):

- the palette entry that covers at least 60 percent of the image border and 15 percent of the area,
- agreed on by at least 80 percent of the room's object images,
- whose palette colour matches a mask colour measured in the game: (227,0,195) magenta in the system room, (107,199,27) green in the ship, (141,47,255) violet, (0,255,0) green.

Without that consensus nothing is written. A mask set by mistake cuts artwork away, which is the more expensive error. The colour check exists because a border-only rule hits the logo room, whose blue border is artwork (room 1, index 53, (0,87,171)); that is the same confusion your visual review corrected earlier. The per room decision is recorded in `mask_indices.json` next to the raw images, with the vote count.

**2. Upscaler removes the mask colour before scaling**

`scripts/upscale_esrgan.py` fills the masked area from its neighbours first (`cv2.inpaint`, 3 px), so the upscaler cannot pull the mask colour into the sprite edge. The alpha is then taken over binary with `INTER_NEAREST`, because the game only knows hard masks, and this matches the state that was approved for the shipped textures. Sources without a mask keep the previous soft contour path. Both readers are supported: cv2 returns the tRNS as a fourth channel, PIL only via the palette index.

**3. Measurement** (`scripts/test_root_fix.py`, runs without a GPU)

```
mask detection     room 3  index 255 magenta 60/60   room 39 index 255 violet 60/60
                   room 55 index 5   green   3/3     logo room: no consensus, no mask
tRNS round trip    transparency read, mask correct
shipped textures   room 3: 60 files compared, worst deviation 0.089 percent
fill routine       magenta 3755 -> 0 and 3307 -> 0 pixels
```

The 0.089 percent agreement matters most: the measured detection reproduces the mask that was approved by visual review, it does not invent a new one.

**Not executed here:** `cv2.inpaint` and the ESRGAN step itself, this environment has neither cv2 nor torch. The fill logic was verified through the reference implementation in `mask_detect.py`; the GPU run belongs on the machine that has the model. Documented in `docs/TEXTURE_MASK_PIPELINE.md`.
