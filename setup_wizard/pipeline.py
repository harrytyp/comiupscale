"""
Pipeline — master orchestrator for the COMI Upscaled workflow.

Each step is a function that takes (cfg, progress_bar) and returns
True on success, False on skip, raises on failure.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

from setup_wizard import ui

# ── Path helpers ─────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent


def _p(*parts):
    return str(ROOT.joinpath(*parts))


def _py():
    """Return the python interpreter to use."""
    return sys.executable or "python"


# ── Step implementations ─────────────────────────────

def step_detect(cfg, progress):
    """Detect system capabilities — OS, GPU, tools."""
    task = progress.add_task("  Detecting system...", total=1)
    ui.info(f"Python:  {sys.version.split()[0]}")
    import platform as _pl
    ui.info(f"System:  {_pl.system()} {_pl.release()}")
    ui.info(f"Machine: {_pl.machine()}")

    # Check RealESRGAN
    esrgan = _p("tools", "realesrgan-ncnn-vulkan-v0.2.0-windows", "realesrgan-ncnn-vulkan.exe")
    if os.path.exists(esrgan):
        ui.success("RealESRGAN found")
    else:
        ui.warn("RealESRGAN not found — upscaling will be unavailable")

    progress.update(task, completed=1)
    return True


def step_find_game(cfg, progress):
    """Locate COMI game files."""
    task = progress.add_task("  Locating game files...", total=1)

    path = cfg["game"]["path"]
    if path and os.path.isdir(path):
        ui.success(f"Game path: {path}")
        progress.update(task, completed=1)
        return True

    # Auto-discover common locations
    candidates = [
        "./game",
        "./Monkey3",
        "./COMI",
        "../COMI",
    ]
    if os.name == "nt":
        candidates += [
            "C:/Program Files/ScummVM/Monkey3",
            "D:/Games/Monkey Island 3",
        ]

    for c in candidates:
        full = _p(c)
        if os.path.isdir(full) and any(f.endswith(".LA0") for f in os.listdir(full)):
            cfg["game"]["path"] = os.path.abspath(full)
            ui.success(f"Found game: {cfg['game']['path']}")
            progress.update(task, completed=1)
            return True

    progress.update(task, completed=1)
    return False  # caller will prompt


def step_extract(cfg, progress):
    """Extract assets from game files (backgrounds, objects, cutscenes, costumes, fonts)."""
    if cfg["mode"] == "bring-your-own":
        ui.info("Bring-your-own mode — skipping extraction")
        return False  # skipped

    task = progress.add_task("  Extracting assets...", total=1)

    export_script = _p("scripts", "export_all.sh")
    if not os.path.exists(export_script):
        ui.warn("export_all.sh not found — skipping extraction")
        progress.update(task, completed=1)
        return False

    ui.info("This may take a few minutes...")
    result = subprocess.run(
        ["bash", export_script],
        cwd=ROOT, capture_output=True, text=True, timeout=600
    )

    if result.returncode == 0:
        ui.success("Assets extracted!")
        progress.update(task, completed=1)
        return True
    else:
        ui.error(f"Extraction failed (exit {result.returncode})")
        ui.warn(result.stderr[-300:] if result.stderr else "No details")
        progress.update(task, completed=1)
        return False


def step_upscale(cfg, progress):
    """Upscale backgrounds, objects, object layers, and costumes."""
    if cfg["mode"] == "express":
        ui.info("Express mode — skipping upscale")
        return False
    if cfg["mode"] == "bring-your-own":
        ui.info("Bring-your-own mode — skipping upscale")
        return False
    if not cfg["upscale"]["enabled"]:
        ui.info("Upscaling disabled in config — skipping")
        return False

    # ── Backgrounds ──
    task_bg = progress.add_task("  [bold]Backgrounds[/]", total=40)
    bg_script = _p("config", "upscale", "batch_upscale.sh")
    if os.path.exists(bg_script):
        subprocess.run(["bash", bg_script], cwd=ROOT, capture_output=True, timeout=600)
        done_bg = len(os.listdir(_p("assets", "upscaled", "backgrounds")))
        progress.update(task_bg, completed=done_bg)
        ui.success(f"Backgrounds: {done_bg} upscaled")
    else:
        progress.update(task_bg, completed=40)

    # ── Objects + layers ──
    task_ob = progress.add_task("  [bold]Objects + Layers[/]", total=834)
    obj_script = _p("config", "upscale", "upscale_objects.sh")
    if os.path.exists(obj_script):
        subprocess.run(["bash", obj_script], cwd=ROOT, capture_output=True, timeout=600)
        for d in ("objects", "objects_layers"):
            p = _p("assets", "upscaled", d)
            if os.path.isdir(p):
                progress.update(task_ob, advance=len(os.listdir(p)))
    else:
        progress.update(task_ob, completed=834)

    # ── Costumes (batch RealESRGAN) ──
    task_co = progress.add_task("  [bold]Costumes[/]", total=25_304)
    esrgan = _p("tools", "realesrgan-ncnn-vulkan-v0.2.0-windows", "realesrgan-ncnn-vulkan.exe")
    task_co = progress.add_task("  [bold]Costumes[/]", total=25304)
    src = _p("assets", "extracted", "COMI", "costumes")
    dst = _p("assets", "upscaled", "costumes")

    if os.path.exists(esrgan) and os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        ui.info("Batch upscaling costumes — this will take a while...")
        result = subprocess.run(
            [esrgan, "-i", src, "-o", dst, "-m", models_dir,
             "-n", cfg["upscale"]["model"], "-g", cfg["upscale"]["gpu"]],
            cwd=ROOT, capture_output=True, timeout=86400  # 24h
        )
        done_co = len([f for f in os.listdir(dst) if f.endswith(".png")])
        progress.update(task_co, completed=done_co)
        if result.returncode == 0:
            ui.success(f"Costumes: {done_co} upscaled")
        else:
            ui.warn(f"Costume upscale may have errors (exit {result.returncode})")
    else:
        ui.warn("Costume upscale skipped — missing tools or source")
        progress.update(task_co, completed=0)

    return True


def step_alpha(cfg, progress):
    """Apply alpha transparency masks to upscaled sprites."""
    if not cfg["alpha"]["enabled"]:
        ui.info("Alpha fixup disabled — skipping")
        return False

    task = progress.add_task("  Alpha transparency fixup...", total=1)

    alpha_script = _p("scripts", "add_costume_alpha.py")
    if os.path.exists(alpha_script):
        ui.info("Applying alpha masks (costumes)...")
        subprocess.run([_py(), alpha_script], cwd=ROOT, capture_output=True, timeout=3600)

    obj_v5 = _p("scripts", "add_object_alpha_v5.py")
    if os.path.exists(obj_v5):
        ui.info("Applying alpha masks (objects)...")
        subprocess.run([_py(), obj_v5], cwd=ROOT, capture_output=True, timeout=600)

    progress.update(task, completed=1)
    ui.success("Alpha fixup complete")
    return True


def step_deploy(cfg, progress):
    """Copy upscaled assets to the ScummVM HD directory."""
    task = progress.add_task("  Deploying HD assets...", total=1)

    deploy_script = _p("scripts", "deploy_hd.py")
    if os.path.exists(deploy_script):
        for label, src_dir, dst_dir in [
            ("Costumes", "assets/upscaled/costumes", "game/hd/costumes"),
            ("Fonts", "assets/upscaled/fonts", "game/hd/fonts"),
        ]:
            full_src = _p(src_dir)
            full_dst = _p(dst_dir)
            if os.path.isdir(full_src):
                os.makedirs(full_dst, exist_ok=True)
                subprocess.run(
                    [_py(), deploy_script, "--src", full_src, "--dst", full_dst],
                    cwd=ROOT, capture_output=True, timeout=600
                )
                ui.success(f"{label} deployed")

    # Also copy backgrounds if they exist at root level
    hd_root = _p("game", "hd")
    bg_src = _p("assets", "upscaled", "backgrounds")
    if os.path.isdir(bg_src):
        for f in os.listdir(bg_src):
            if f.endswith(".png") and not os.path.exists(os.path.join(hd_root, f"bg_{f}")):
                shutil.copy2(os.path.join(bg_src, f), os.path.join(hd_root, f"bg_{f}"))

    progress.update(task, completed=1)
    return True


def step_manifest(cfg, progress):
    """Generate hd_manifest.json."""
    task = progress.add_task("  Generating manifest...", total=1)
    manifest_script = _p("scripts", "hd_manifest_gen.py")
    if os.path.exists(manifest_script):
        subprocess.run([_py(), manifest_script], cwd=ROOT, capture_output=True, timeout=60)
    else:
        ui.warn("hd_manifest_gen.py not found")
    progress.update(task, completed=1)
    return True


def step_assets_download(cfg, progress):
    """Download pre-upscaled assets (express mode)."""
    if cfg["mode"] != "express":
        return False

    task = progress.add_task("  Downloading pre-upscaled assets...", total=1)
    url = cfg["assets"]["pre_upscaled_url"]
    vid_url = cfg["assets"]["cutscene_videos_url"]

    if not url and not vid_url:
        ui.warn("No download URLs configured")
        progress.update(task, completed=1)
        return False

    import urllib.request
    import hashlib
    import zipfile
    import tarfile

    if url:
        ui.info(f"Downloading: {url}")
        # TODO: implement download with progress
        ui.warn("Download not yet implemented — place assets manually")

    if vid_url:
        ui.info(f"Downloading videos: {vid_url}")

    progress.update(task, completed=1)
    return True


def step_videos(cfg, progress):
    """Handle cutscene videos."""
    task = progress.add_task("  Setting up videos...", total=1)
    video_dir = _p("ScummVM", "monkey3", "hd", "videos")
    existing = len([f for f in os.listdir(video_dir) if f.endswith(".mp4")]) if os.path.isdir(video_dir) else 0
    if existing >= 15:
        ui.success(f"Videos: {existing} already present")
    else:
        ui.info(f"Videos: {existing}/15 — download or extract needed")
    progress.update(task, completed=1)
    return True


def step_summary(cfg, progress):
    """Show final asset counts."""
    task = progress.add_task("  Final summary...", total=1)

    import os
    hd = _p("ScummVM", "monkey3", "hd")

    def count_png(d):
        p = os.path.join(hd, d)
        if not os.path.isdir(p):
            return 0
        with os.scandir(p) as it:
            return sum(1 for e in it if e.name.endswith(".png"))

    def count_mp4(d):
        p = os.path.join(hd, d)
        if not os.path.isdir(p):
            return 0
        with os.scandir(p) as it:
            return sum(1 for e in it if e.name.endswith(".mp4"))

    bg = len([f for f in os.listdir(hd) if f.startswith("bg_") and f.endswith(".png")]) if os.path.isdir(hd) else 0

    counts = {
        "Backgrounds": bg,
        "Objects": count_png("objects"),
        "Object layers": count_png("objects_layers"),
        "Cutscene videos": count_mp4("videos"),
        "Costumes": count_png("costumes"),
        "Fonts": count_png("fonts"),
    }
    total_assets = sum(counts.values())

    ui.success("All done! HD asset summary:")
    ui.summary_table(counts)
    ui.info(f"Total: {total_assets} HD assets ready")

    progress.update(task, completed=1)
    return True


# ── Pipeline ─────────────────────────────────────────

PIPELINE_STEPS = [
    ("⚓  System Detection",       step_detect),
    ("🏴  Game Files",             step_find_game),
    ("📦  Pre-upscaled Download",  step_assets_download),
    ("🔧  Extraction",             step_extract),
    ("🎨  Upscaling",              step_upscale),
    ("🎬  Videos",                 step_videos),
    ("✨  Alpha Fixup",            step_alpha),
    ("📋  Deploy",                 step_deploy),
    ("📝  Manifest",               step_manifest),
    ("📊  Summary",                step_summary),
]


def run(cfg):
    """Run the full pipeline. Each step is optional and gracefully skipped."""
    ui.title_screen()
    ui.panel(
        "Ship's Log",
        f"Mode: {cfg['mode']}\\n{__import__('setup_wizard.config').fmt(cfg)}",
        border_style=ui.WOOD,
    )

    if not cfg["game"]["path"] and cfg["mode"] != "express":
        cfg["game"]["path"] = ui.ask("Path to Monkey Island 3 game folder")

    with ui.progress_bar("Pipeline", total=len(PIPELINE_STEPS)) as progress:
        for step_idx, (name, func) in enumerate(PIPELINE_STEPS):
            step_task = progress.add_task(f"  {name}", total=1)
            try:
                func(cfg, progress)
            except Exception as e:
                ui.error(f"Step '{name}' failed: {e}")
                ui.insult()
                if not ui.confirm("Continue with remaining steps?", default=True):
                    raise
            progress.update(step_task, completed=1)

    ui.done_message()
    ui.show_monkey()
