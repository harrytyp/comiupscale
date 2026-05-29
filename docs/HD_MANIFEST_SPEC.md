# HD Manifest Specification

The HD manifest tells the ScummVM fork where to find replacement assets.
It sits in the game directory alongside COMI.LA0 as `hd_manifest.json`.

## Format

```json
{
  "version": 1,
  "engine": "scumm",
  "game": "monkey3",
  "scale": 4,
  "asset_dirs": {
    "backgrounds": "hd/backgrounds",
    "objects": "hd/objects",
    "costumes": "hd/costumes",
    "fonts": "hd/fonts",
    "cutscenes": "hd/cutscenes"
  },
  "backgrounds": {
    "0001": { "file": "hd/backgrounds/bg_0001.png", "w": 2560, "h": 1920 },
    "0002": { "file": "hd/backgrounds/bg_0002.png", "w": 2560, "h": 1920 }
  },
  "metadata": {
    "upscale_model": "realesrgan-x4plus-anime",
    "upscale_by": "RealESRGAN-NCNN-Vulkan v0.2.0",
    "created": "2026-05-23",
    "source_game": "Curse of Monkey Island (COMI.LA0/1/2)"
  }
}
```

## Directory Convention (No Manifest Mode)

If no `hd_manifest.json` exists, the engine scans:

```
<game_dir>/hd/
├── bg_0001.png         → background room 1
├── bg_0002.png         → background room 2
├── obj_0001.png        → object 1
└── fonts/
    └── ...
```

Filename → room mapping: `bg_XXXX.png` where XXXX is the 4-digit room ID
from the extracted filenames (e.g. `0001_logo.png` → room 1).

## Background Asset Mapping

From our extracted assets (`CMI UPSCALED/extracted/COMI/IMAGES/backgrounds/`):

| Room ID | Name | Original | HD (4x) |
|---------|------|----------|---------|
| 0001 | logo | 640x480 | 2560x1920 |
| 0002 | thx | 640x480 | 2560x1920 |
| 0004 | chapter1 | 640x480 | 2560x1920 |
| 0005 | chapter2 | 640x480 | 2560x1920 |
| 0006 | chapter3 | 640x480 | 2560x1920 |
| 0009 | cannon | 640x480 | 2560x1920 |
| 0010 | cannon-v | 640x480 | 2560x1920 |
| 0011 | waterln | 640x480 | 2560x1920 |
| 0012 | treasure | 640x480 | 2560x1920 |
| 0013 | plndrmap | 640x480 | 2560x1920 |
| 0014 | fortbase | 1496x480 | 5984x1920 |
| 0015 | town | 2096x480 | 8384x1920 |
| 0016 | chkn-int | 640x480 | 2560x1920 |
| 0017 | cu-elpol | 640x480 | 2560x1920 |
| 0018 | offstage | 640x480 | 2560x1920 |
| 0019 | stage | 640x480 | 2560x1920 |
| 0020 | spotlght | 640x480 | 2560x1920 |
| 0021 | brbr-int | 640x480 | 2560x1920 |
| 0022 | clring-a | 1072x480 | 4288x1920 |
| 0023 | clring-b | 640x480 | 2560x1920 |
| 0024 | pistols | 640x480 | 2560x1920 |
| 0025 | banjo | 1280x480 | 5120x1920 |
| 0026 | bchclub | 640x480 | 2560x1920 |
| 0027 | beachhot | 640x480 | 2560x1920 |
| 0028 | brimbch | 640x480 | 2560x1920 |
| 0029 | voodoo-e | 640x480 | 2560x1920 |
| 0030 | voodoo-i | 640x480 | 2560x1920 |
| 0031 | snake | 640x480 | 2560x1920 |
| 0032 | quiksand | 640x480 | 2560x1920 |
| 0033 | danjrbch | 1200x480 | 4800x1920 |
| 0034 | danjrbay | 640x480 | 2560x1920 |
| 0035 | lc-deck | 640x480 | 2560x1920 |
| 0036 | lc-qurtr | 640x480 | 2560x1920 |
| 0037 | lc-plank | 640x480 | 2560x1920 |
| 0038 | elanemap | 640x480 | 2560x1920 |
| 0072 | morts | 640x480 | 2560x1920 |
| 0087 | easyhard | 640x480 | 2560x1920 |
| 0089 | comb | 640x480 | 2560x1920 |
| 0090 | crownest | 640x480 | 2560x1920 |
| 0091 | credits | 640x480 | 2560x1920 |

## Manifest Generator Script

`scripts/hd_manifest_gen.py` scans the background PNGs and generates
an `hd_manifest.json`:
