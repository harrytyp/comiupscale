"""Central path resolver for all scripts.

Usage:
    from paths import PROJECT_ROOT, ASSETS, GAME, etc.

All paths are absolute, resolved relative to the project root
(one directory up from scripts/).
"""

import os

# Project root is the parent of scripts/
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# ── Assets ──
ASSETS_EXTRACTED = os.path.join(PROJECT_ROOT, 'assets', 'extracted', 'COMI')
ASSETS_UPSCALED = os.path.join(PROJECT_ROOT, 'assets', 'upscaled')

# ── Game ──
GAME_DIR = os.path.join(PROJECT_ROOT, 'game')
GAME_HD_DIR = os.path.join(PROJECT_ROOT, 'game', 'hd')
GAME_VIDEOS_DIR = os.path.join(GAME_HD_DIR, 'videos')

# ── Extracted asset subdirectories ──
EXTRACTED_BACKGROUNDS = os.path.join(ASSETS_EXTRACTED, 'IMAGES', 'backgrounds')
EXTRACTED_OBJECTS = os.path.join(ASSETS_EXTRACTED, 'IMAGES', 'objects')
EXTRACTED_OBJECTS_LAYERS = os.path.join(ASSETS_EXTRACTED, 'IMAGES', 'objects_layers')
EXTRACTED_COSTUMES = os.path.join(ASSETS_EXTRACTED, 'costumes')
EXTRACTED_FONTS = os.path.join(ASSETS_EXTRACTED, 'fonts')

# ── Upscaled asset subdirectories ──
UPSCALED_BACKGROUNDS = os.path.join(ASSETS_UPSCALED, 'backgrounds')
UPSCALED_OBJECTS = os.path.join(ASSETS_UPSCALED, 'objects')
UPSCALED_OBJECTS_LAYERS = os.path.join(ASSETS_UPSCALED, 'objects_layers')
UPSCALED_COSTUMES = os.path.join(ASSETS_UPSCALED, 'costumes')
UPSCALED_FONTS = os.path.join(ASSETS_UPSCALED, 'fonts')
UPSCALED_CUTSCENES = os.path.join(ASSETS_UPSCALED, 'cutscenes')

# ── Config ──
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
HD_MANIFEST = os.path.join(CONFIG_DIR, 'hd_manifest.json')
OBJECT_MAP = os.path.join(CONFIG_DIR, 'object_map.json')

# ── Tools ──
NUTCRACKER_SRC = os.path.join(PROJECT_ROOT, 'tools', 'nutcracker', 'src')
NUTCRACKER_BIN = os.path.join(PROJECT_ROOT, 'tools', 'nutcracker-Windows_X64')
REALESRGAN_DIR = os.path.join(PROJECT_ROOT, 'tools',
                               'realesrgan-ncnn-vulkan-v0.2.0-windows')

# ── Deploy target (HD files go here) ──
HD_BACKGROUNDS = os.path.join(GAME_HD_DIR, 'backgrounds') if False else GAME_HD_DIR
HD_OBJECTS = os.path.join(GAME_HD_DIR, 'objects')
HD_OBJECTS_LAYERS = os.path.join(GAME_HD_DIR, 'objects_layers')
HD_COSTUMES = os.path.join(GAME_HD_DIR, 'costumes')
HD_VIDEOS = GAME_VIDEOS_DIR
