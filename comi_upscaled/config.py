"""
Config — load/save config.yaml with schema validation.

Uses strictyaml if available, falls back to pyyaml. The config
is a living document: missing keys get filled with defaults.
"""

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# ── Default config (all keys, no surprises) ──────────
DEFAULT_CONFIG = {
    "game": {"path": "", "id": "monkey3"},
    "mode": "express",
    "upscale": {
        "enabled": True,
        "engine": "realesrgan-ncnn-vulkan",
        "model": "realesrgan-x4plus-anime",
        "scale": 4,
        "gpu": "auto",
        "tile_size": 0,
    },
    "alpha": {"enabled": True, "filter": "lanczos"},
    "assets": {
        "pre_upscaled_url": "",
        "pre_upscaled_checksum": "",
        "cutscene_videos_url": "",
        "cutscene_videos_checksum": "",
    },
    "scummvm": {
        "source": "build",
        "fork_repo": "",
        "binary_url": "",
        "platform": "auto",
    },
}

VALID_FILTERS = {"lanczos", "bilinear", "nearest"}
VALID_MODES = {"express", "full", "bring-your-own"}
VALID_MODELS = {
    "realesrgan-x4plus",
    "realesrgan-x4plus-anime",
    "realesr-animevideov3",
    "realesrnet-x4plus",
}


def project_root():
    """Return the absolute path to the project root (two levels up from this file)."""
    return Path(__file__).resolve().parent.parent


def config_path():
    return project_root() / "config.yaml"


def load() -> dict:
    """Load config.yaml, fill missing keys with defaults."""
    path = config_path()
    cfg = dict(DEFAULT_CONFIG)  # deep enough for our shallow needs

    if path.exists() and yaml:
        try:
            with open(path) as f:
                user = yaml.safe_load(f) or {}
            _deep_merge(cfg, user)
        except Exception as e:
            print(f"[WARN] Could not parse config.yaml: {e}")

    return cfg


def save(cfg: dict):
    """Save config.yaml, preserving all keys."""
    if not yaml:
        print("[ERROR] PyYAML not installed — cannot save config.")
        return
    path = config_path()
    with open(path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"  Config saved → {path}")


def validate(cfg: dict) -> list:
    """Return a list of validation warnings. Empty list = valid."""
    warnings = []

    if cfg["mode"] not in VALID_MODES:
        warnings.append(f"Unknown mode '{cfg['mode']}'. Choose from: {', '.join(VALID_MODES)}")

    if cfg["alpha"]["filter"] not in VALID_FILTERS:
        warnings.append(f"Unknown alpha filter '{cfg['alpha']['filter']}'. Choose from: {', '.join(VALID_FILTERS)}")

    if cfg["upscale"]["enabled"] and cfg["mode"] == "full":
        if cfg["upscale"]["model"] not in VALID_MODELS:
            warnings.append(f"Unknown upscale model '{cfg['upscale']['model']}' — make sure it exists in the models directory")

    if cfg["mode"] == "full" and not cfg["game"]["path"]:
        warnings.append("Full mode requires a game path")

    if cfg["mode"] == "express":
        if not cfg["assets"]["pre_upscaled_url"] and not cfg["assets"]["cutscene_videos_url"]:
            warnings.append("Express mode needs asset download URLs — configure them or switch mode")

    return warnings


# ── Helpers ──────────────────────────────────────────
def _deep_merge(base, overlay):
    """Recursively merge overlay into base (in-place)."""
    for k, v in overlay.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def fmt(cfg: dict) -> str:
    """Pretty-print the config as a string."""
    lines = [
        f"  Mode:          {cfg['mode']}",
        f"  Game path:     {cfg['game']['path'] or '(not set)'}",
    ]
    if cfg["upscale"]["enabled"] and cfg["mode"] != "express":
        lines += [
            f"  Upscale model: {cfg['upscale']['model']}",
            f"  GPU:           {cfg['upscale']['gpu']}",
        ]
    lines += [f"  Alpha filter:  {cfg['alpha']['filter']}"]
    if cfg["mode"] == "express":
        lines += [f"  Asset source:  {cfg['assets']['pre_upscaled_url'] or '(not set)'}"]
    return "\n".join(lines)
