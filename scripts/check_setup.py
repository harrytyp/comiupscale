#!/usr/bin/env python3
"""
Setup validation & path debugging for COMI Upscaled.

Usage:
    python scripts/check_setup.py              # Full check
    python scripts/check_setup.py --verbose    # Show all paths, even OK ones
    python scripts/check_setup.py --debug      # Path resolution trace

Exit code: 0 if all good, 1 if warnings, 2 if errors.
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import paths


# ── ANSI helpers ─────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}OK{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}WARN{RESET} {msg}")
def err(msg):   print(f"  {RED}MISS{RESET} {msg}")
def info(msg):  print(f"  {CYAN}i{RESET} {msg}")


# ── Check groups ─────────────────────────────────────
ERRORS = 0
WARNINGS = 0
VERBOSE = False


def check(label, required, optional=None):
    """Run a group of path checks.
    
    required: list of (name, path) — must exist or → error
    optional: list of (name, path) — nice to have, → warning if missing
    """
    global ERRORS, WARNINGS
    required = required or []
    optional = optional or []
    total = len(required) + len(optional)
    passed = 0

    print(f"\n{BOLD}{label}{RESET}")
    for group, is_required in [(required, True), (optional, False)]:
        for name, path in group:
            if not path:
                info(f"{name}: not set")
                continue
            if not os.path.exists(path):
                if is_required:
                    err(f"{name}: {path}")
                    ERRORS += 1
                else:
                    warn(f"{name}: {path} (will be generated)")
                    WARNINGS += 1
            else:
                passed += 1
                if VERBOSE:
                    ok(f"{name}: {path}")

    if passed == total and not VERBOSE:
        print(f"  {GREEN}OK{RESET} {passed}/{total} ok")


def check_python():
    """Check that key Python packages are importable."""
    global ERRORS
    print(f"\n{BOLD}Python Packages{RESET}")
    ok_count = 0
    for mod in ("PIL", "numpy", "yaml"):
        try:
            __import__(mod)
            ok_count += 1
            if VERBOSE:
                ok(f"{mod}")
        except ImportError:
            err(f"{mod} — not found, run: pip install {mod}")
            ERRORS += 1
    if ok_count == 3 and not VERBOSE:
        print(f"  {GREEN}OK{RESET} 3/3 ok")


# ── Main ─────────────────────────────────────────────
def main():
    global VERBOSE
    ap = argparse.ArgumentParser(description="Validate COMI Upscaled setup")
    ap.add_argument("--verbose", "-v", action="store_true", help="Show all paths")
    ap.add_argument("--debug", action="store_true", help="Path resolution trace")
    args = ap.parse_args()
    VERBOSE = args.verbose or args.debug

    if args.debug:
        print(f"{BOLD}Path Registry (scripts/paths.py){RESET}")
        for attr in dir(paths):
            if attr.isupper() and not attr.startswith("_"):
                val = getattr(paths, attr)
                if isinstance(val, str) and val:
                    exists = "OK" if os.path.exists(val) else "MISS"
                    print(f"  {exists} {attr:<30s} {val}")

    # ── Project root ──
    print(f"\n{BOLD}Project Root{RESET}")
    ok(f"{paths.PROJECT_ROOT}")
    info(f"config: scripts/paths.py")

    # ── Game files ──
    check("Game Files", [
        ("COMI.LA0", os.path.join(paths.GAME_DIR, "COMI.LA0")),
        ("COMI.LA1", os.path.join(paths.GAME_DIR, "COMI.LA1")),
        ("COMI.LA2", os.path.join(paths.GAME_DIR, "COMI.LA2")),
    ])

    # ── Extracted assets ──
    check("Extracted Assets", [
        ("Backgrounds",  paths.EXTRACTED_BACKGROUNDS),
        ("Objects",      paths.EXTRACTED_OBJECTS),
        ("Object Layers", paths.EXTRACTED_OBJECTS_LAYERS),
        ("Costumes",     paths.EXTRACTED_COSTUMES),
        ("Fonts",        paths.EXTRACTED_FONTS),
    ])

    # ── Upscaled assets ──
    check("Upscaled Assets", [
        ("Backgrounds",     paths.UPSCALED_BACKGROUNDS),
        ("Objects",         paths.UPSCALED_OBJECTS),
        ("Object Layers",   paths.UPSCALED_OBJECTS_LAYERS),
        ("Costumes",        paths.UPSCALED_COSTUMES),
        ("Fonts",           paths.UPSCALED_FONTS),
        ("Cutscenes",       paths.UPSCALED_CUTSCENES),
    ])

    # ── Configuration ──
    check("Configuration", [
        ("HD Manifest",  paths.HD_MANIFEST),
        ("Object Map",   paths.OBJECT_MAP),
    ])

    # ── Tools ──
    check("Tools", [
        ("NUTcracker (Python)", paths.NUTCRACKER_SRC),
        ("NUTcracker (binary)", paths.NUTCRACKER_BIN),
        ("RealESRGAN",          paths.REALESRGAN_DIR),
    ])

    # ── Fork source ──
    fork_root = os.path.join(paths.PROJECT_ROOT, "scummvm", "fork")
    check("ScummVM Fork", [
        ("Source root", fork_root),
        ("config.h",    os.path.join(fork_root, "config.h")),
        ("config.mk",   os.path.join(fork_root, "config.mk")),
    ])

    # ── HD deploy target (optional — generated by deploy scripts) ──
    check("HD Deploy Target (game/hd/)",
        required=[],
        optional=[
            ("Backgrounds",  paths.GAME_HD_DIR),
            ("Costumes",     paths.HD_COSTUMES),
            ("Object Map",   os.path.join(paths.GAME_HD_DIR, "object_map.json")),
            ("Videos",       paths.GAME_VIDEOS_DIR),
        ])

    # ── Python packages ──
    check_python()

    # ── Summary ──
    print()
    if ERRORS > 0:
        print(f"{RED}{ERRORS} error(s) found.{RESET}")
        print(f"  Fix the paths above, then re-run this check.")
        sys.exit(2)
    elif WARNINGS > 0:
        print(f"{YELLOW}{WARNINGS} warning(s) — non-critical.{RESET}")
        print(f"  Missing optional paths (will be created during deploy).")
        sys.exit(1)
    else:
        print(f"{GREEN}All checks passed!{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
