"""Central path resolver for all scripts.

Usage:
    from paths import PROJECT_ROOT, ASSETS, GAME, etc.
    from paths import trace  # optional: print path resolution

All paths are absolute, resolved relative to the project root
(one directory up from scripts/).

Debugging:
    import paths
    paths.trace = True   # prints every path lookup
    paths.validate()      # checks all paths exist, returns report
"""

import os

# Enable path tracing (set to True before importing to see all lookups)
trace = os.environ.get('PATHS_TRACE', '').lower() in ('1', 'true', 'yes')


def _path(*parts):
    """Resolve a path relative to PROJECT_ROOT and trace it if enabled."""
    p = os.path.normpath(os.path.join(PROJECT_ROOT, *parts))
    if trace:
        exists = "✓" if os.path.exists(p) else "✗"
        print(f"  [paths] {exists} {os.path.join(*parts)}")
    return p

# Project root is the parent of scripts/
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# ── Assets ──
ASSETS_EXTRACTED = _path('assets', 'extracted', 'COMI')
ASSETS_UPSCALED = _path('assets', 'upscaled')

# ── Game ──
GAME_DIR = _path('game')
GAME_HD_DIR = _path('game', 'hd')
GAME_VIDEOS_DIR = _path('game', 'hd', 'videos')

# ── Extracted asset subdirectories ──
EXTRACTED_BACKGROUNDS = _path('assets', 'extracted', 'COMI', 'IMAGES', 'backgrounds')
EXTRACTED_OBJECTS = _path('assets', 'extracted', 'COMI', 'IMAGES', 'objects')
EXTRACTED_OBJECTS_LAYERS = _path('assets', 'extracted', 'COMI', 'IMAGES', 'objects_layers')
EXTRACTED_COSTUMES = _path('assets', 'extracted', 'COMI', 'costumes')
EXTRACTED_FONTS = _path('assets', 'extracted', 'COMI', 'fonts')

# ── Upscaled asset subdirectories ──
UPSCALED_BACKGROUNDS = _path('assets', 'upscaled', 'backgrounds')
UPSCALED_OBJECTS = _path('assets', 'upscaled', 'objects')
UPSCALED_OBJECTS_LAYERS = _path('assets', 'upscaled', 'objects_layers')
UPSCALED_COSTUMES = _path('assets', 'upscaled', 'costumes')
UPSCALED_FONTS = _path('assets', 'upscaled', 'fonts')
UPSCALED_CUTSCENES = _path('assets', 'upscaled', 'cutscenes')

# ── Config ──
CONFIG_DIR = _path('config')
HD_MANIFEST = _path('config', 'hd_manifest.json')
OBJECT_MAP = _path('config', 'object_map.json')

# ── Tools ──
NUTCRACKER_SRC = _path('tools', 'nutcracker', 'src')
NUTCRACKER_BIN = _path('tools', 'nutcracker-Windows_X64')
REALESRGAN_DIR = _path('tools',
                        'realesrgan-ncnn-vulkan-v0.2.0-windows')

# ── Deploy target (HD files go here) ──
HD_COSTUMES = _path('game', 'hd', 'costumes')
HD_OBJECTS = _path('game', 'hd', 'objects')
HD_OBJECTS_LAYERS = _path('game', 'hd', 'objects_layers')
HD_VIDEOS = _path('game', 'hd', 'videos')
