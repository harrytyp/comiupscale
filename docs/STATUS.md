# COMI Upscaled — Status Report (2026-05-26)

## What Works

| Feature | Status | Notes |
|---------|--------|-------|
| **HD Backgrounds** (40) | ✅ | 2560×1920, full room coverage |
| **HD Objects** (384 mapped) | ✅ | object_map.json, composite pipeline |
| **HD Object Layers** (234) | ✅ | Layer compositing |
| **HD Costumes** (25,304 frames) | ✅ | sub=1 only (base anim sets), LRU cache 512 |
| **HD Font sheets** (5/5 loaded) | ✅ | Loaded from disk, ready for charset integration |
| **SMUSH cutscenes (8-bit)** | ✅ | Correct passthrough during cutscene playback |
| **Fork build** | ✅ | MSYS2 MinGW64, ENABLE_SCUMM_7_8=1 |
| **rclone sync** | ✅ | Local SSD build → NAS deploy |
| **Alpha fixup** (LANCZOS) | ✅ | All HD objects and costumes have alpha masks |
| **No crashes** | ✅ | OOB protection, surface format validation |

## What's Broken / Not Yet

| Issue | Status | Root Cause | Priority |
|-------|--------|------------|----------|
| **HD Videos (MP4)** | ❌ | ffmpeg pipe (hd_video_player.cpp) — CreateProcessA fails, falls back to 8-bit | High |
| **Sword cursor (difficulty screen)** | ❌ | Verb/UI element, not a room object — different rendering path | High |
| **Object culling (ramrod etc.)** | ❌ | `_hdCleanBackground` diff heuristic — stationary interactive objects get culled | High |
| **Costume sub selection** | ⚠️ | All costumes forced to sub=1 — needs actor state → AKOS sub mapping | Medium |
| **HD Font rendering** | ⚠️ | Disabled globally — charset integration incomplete (glyph pos, palette, shadows) | Medium |
| **Flickering** | ❌ | Multiple potential causes: cache miss, redraw logic, vsync | High |
| **Difficulty screen zoom/glitch** | ❌ | Possibly font-related or object overlay issue | Medium |

## Build Details

- **Binary**: `C:\Users\kolja\build\preconf\scummvm.exe` (29MB, GCC 16.1.0)
- **Rebuild**: `cd /c/Users/kolja/build/preconf && touch dists/scummvm.o dists/.deps/scummvm.d && mingw32-make -j12`
- **Game path**: `Z:\Projekte\COMI-Upscaled\ScummVM\monkey3`
- **HD assets**: `ScummVM/monkey3/hd/`

## Pipeline

1. `bash hd_config/batch_upscale.sh` → RealESRGAN 4x upscale
2. `python scripts/hd_manifest_gen.py` → generate manifest
3. `python scripts/deploy_hd.py` → deploy assets
4. Build fork → `scummvm.exe`

## Known Issues (Detailed)

### HD Videos
`hd_video_player.cpp` spawns ffmpeg via CreateProcessA with `ffmpeg -i <mp4> -f rawvideo -pix_fmt BGRA -vf crop=2560:1920:160:120 -`. If ffmpeg is not in PATH or `ffmpeg_path` config is unset, the pipe fails silently and the SMUSH player falls back to 8-bit playback.

### Sword Cursor
The difficulty screen sword (`easyhard-choice-object` in room 0087) is a cursor/verb element, not rendered as a room object. The HD object pipeline only handles room objects. Requires extending HdObjectManager to handle UI/verb elements.

### Object Culling (Ramrod)
`renderHDComposite()` Step 2.5 captures `_hdCleanBackground` before the HD pass. If an object is stationary (same pixels as previous frame), the diff is zero and the HD object is skipped. Freshly animated objects trigger the diff correctly. Fix: track object draw state independently and always draw HD objects that exist in `object_map.json`.

### Flickering
Likely caused by: (a) HD costumes being loaded/unloaded per frame (cache warming), (b) composite surface being fully redrawn each frame without double-buffering, (c) HD background blitting over the 8-bit surface without proper synchronization.
