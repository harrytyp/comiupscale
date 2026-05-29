#!/usr/bin/env python3
"""
COMI Upscaled — The Curse of the HD Monkey Island

A setup wizard and pipeline orchestrator for upscaling
The Curse of Monkey Island to 4K resolution.

Usage:
    python setup.py                  # Full interactive wizard
    python setup.py --mode full      # Skip mode selection, start pipeline
    python setup.py --config-only    # Just configure, don't run
    python setup.py --help           # All options
"""

import os
import sys
import argparse

# Ensure we're in the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from setup_wizard import ui, config, pipeline


def wizard_mode(cfg):
    """Interactive mode selection wizard."""
    ui.title_screen()
    ui.panel(
        "Welcome, Pirate!",
        "You are about to embark on a grand adventure:\n"
        "upscaling The Curse of Monkey Island to glorious 4K.\n\n"
        "Choose your path wisely, for the seas are treacherous\n"
        "and the pixels are plentiful.",
    )

    # ── Mode ──
    ui.section("Choose Your Mode")
    ui.info("express  → Download upscaled assets (fast, needs internet)")
    ui.info("full     → Extract + upscale from game files (slow, best quality)")
    ui.info("bring-your-own → Supply your own HD assets (expert)")

    mode = ui.ask("Your choice", default=cfg.get("mode", "express"))
    if mode not in {"express", "full", "bring-your-own"}:
        ui.warn(f"Unknown mode '{mode}', using express")
        mode = "express"
    cfg["mode"] = mode

    # ── Game path ──
    if mode != "express":
        ui.section("Game Files")
        path = cfg.get("game", {}).get("path", "")
        if not path:
            path = ui.ask("Path to your Monkey Island 3 folder")
        if path:
            cfg.setdefault("game", {})["path"] = path

    # ── Alpha filter ──
    ui.section("Alpha Mask Quality")
    ui.info("Controls how sprite transparency edges look when upscaled:")
    ui.info("  lanczos  → Best anti-aliasing (recommended)")
    ui.info("  bilinear → Good quality, faster")
    ui.info("  nearest  → No anti-aliasing, fastest (jagged edges)")
    filt = ui.ask("Filter", default=cfg.get("alpha", {}).get("filter", "lanczos"))
    if filt not in {"lanczos", "bilinear", "nearest"}:
        filt = "lanczos"
    cfg.setdefault("alpha", {})["filter"] = filt

    # ── Upscale model ──
    if mode == "full":
        ui.section("Upscale Model")
        ui.info("Available models for RealESRGAN:")
        ui.info("  realesrgan-x4plus-anime  → Best for hand-drawn art (default)")
        ui.info("  realesrgan-x4plus        → General photo upscale")
        ui.info("  realesr-animevideov3      → Optimized for anime")
        model = ui.ask("Model", default=cfg.get("upscale", {}).get("model", "realesrgan-x4plus-anime"))
        cfg.setdefault("upscale", {})["model"] = model

    # ── Summary ──
    ui.section("Configuration")
    ui.info(config.fmt(cfg))

    if not ui.confirm("Looks good?", default=True):
        ui.info("Run 'python setup.py' again to reconfigure.")
        return False

    config.save(cfg)
    return True


def main():
    ap = argparse.ArgumentParser(
        description="COMI Upscaled — The Curse of the HD Monkey Island"
    )
    ap.add_argument("--mode", choices=["express", "full", "bring-your-own"],
                    help="Skip wizard, set mode directly")
    ap.add_argument("--config-only", action="store_true",
                    help="Configure and save, but don't run the pipeline")
    ap.add_argument("--game", help="Path to Monkey Island 3 game folder")
    ap.add_argument("--alpha-filter", choices=["lanczos", "bilinear", "nearest"],
                    help="Alpha mask resize filter")
    ap.add_argument("--model", help="RealESRGAN model name")
    ap.add_argument("--gpu", default="auto", help="GPU device ID")
    ap.add_argument("--version", action="store_true", help="Show version")
    args = ap.parse_args()

    # ── Version ──
    if args.version:
        import setup_wizard
        print(f"COMI Upscaled v{setup_wizard.__version__}")
        return

    # ── Load config, apply CLI overrides ──
    cfg = config.load()

    if args.mode:
        cfg["mode"] = args.mode
    if args.game:
        cfg["game"]["path"] = os.path.abspath(args.game)
    if args.alpha_filter:
        cfg["alpha"]["filter"] = args.alpha_filter
    if args.model:
        cfg["upscale"]["model"] = args.model
    if args.gpu:
        cfg["upscale"]["gpu"] = args.gpu

    # ── Interactive wizard (if no --mode) ──
    if not args.mode:
        if not wizard_mode(cfg):
            return

    # ── Config-only ──
    if args.config_only:
        config.save(cfg)
        ui.success("Configuration saved! Run 'python setup.py' to start the pipeline.")
        return

    # ── Run pipeline ──
    warnings = config.validate(cfg)
    if warnings:
        for w in warnings:
            ui.warn(w)
        if not ui.confirm("Continue anyway?", default=False):
            return

    # Save before running
    config.save(cfg)

    try:
        pipeline.run(cfg)
    except KeyboardInterrupt:
        ui.warn("\nPipeline interrupted by user.")
        ui.info("Progress was saved where possible — you can resume.")
        sys.exit(1)
    except Exception as e:
        ui.error(f"Pipeline failed: {e}")
        ui.insult()
        sys.exit(1)


if __name__ == "__main__":
    main()
