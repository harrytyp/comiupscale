#!/usr/bin/env python3
"""
HD Texture Diagnose — automated log parser for COMI HD pipeline.

Parses ScummVM debug logs and produces a structured report:
- Which HD asset types are loaded vs missing
- Which actors have HD costumes and which don't
- Whether fonts are being recorded
- Any rendering issues (black blocks, off-screen, etc.)

Usage: python3 diagnose.py [logfile]
       python3 diagnose.py logs/hd_debug_boot200_v3.log
"""

import re
import sys
import os
import json
from collections import defaultdict


def parse_log(filepath):
    with open(filepath) as f:
        lines = f.readlines()

    result = {
        "file": filepath,
        "rooms": set(),
        "frames": 0,
        "background": {"loaded": False, "fg_pct": 0.0, "clean_valid": False},
        "objects": {"loaded": 0, "skipped": 0, "culled": 0},
        "costumes": {
            "loaded": 0, "skipped": 0,
            "noCostume": 0, "noCel": 0, "noHdCostume": 0, "loadFail": 0,
        },
        "costume_hits": [],
        "costume_misses": [],
        "fonts": {"chars_recorded": 0, "chars_drawn": 0, "fontMgr_enabled": False},
        "issues": [],
    }

    for line in lines:
        # HDDBG room summary (every 30 frames)
        m = re.search(
            r'HDDBG room=(\d+).*bg=(\d+).*objMgr=\d+/(\d+).*costMgr=\d+/(\d+).*fontMgr=(\d+)/(\d+).*fontChars=(\d+)',
            line
        )
        if m:
            result["rooms"].add(int(m.group(1)))
            result["background"]["loaded"] = bool(int(m.group(2)))
            result["fonts"]["fontMgr_enabled"] = bool(int(m.group(5)))
            result["fonts"]["chars_recorded"] = int(m.group(7))
            result["frames"] += 1

        # Step 2 foreground pixels
        m = re.search(r'step2: fgPixels=(\d+)/(\d+) \(([0-9.]+)%\).*cleanValid=(\d+)', line)
        if m:
            result["background"]["fg_pct"] = float(m.group(3))
            result["background"]["clean_valid"] = bool(int(m.group(4)))

        # Step 2.5 objects
        m = re.search(r'step2\.5 objects: loaded=(\d+) skipped=(\d+) culled=(\d+)', line)
        if m:
            result["objects"]["loaded"] = int(m.group(1))
            result["objects"]["skipped"] = int(m.group(2))
            result["objects"]["culled"] = int(m.group(3))

        # Step 2.6 costumes
        m = re.search(
            r'step2\.6 costumes: loaded=(\d+) skipped=(\d+) \(noCostume=(\d+) noCel=(\d+) noHdCostume=(\d+) loadFail=(\d+)\)',
            line
        )
        if m:
            c = result["costumes"]
            c["loaded"] = int(m.group(1))
            c["skipped"] = int(m.group(2))
            c["noCostume"] = int(m.group(3))
            c["noCel"] = int(m.group(4))
            c["noHdCostume"] = int(m.group(5))
            c["loadFail"] = int(m.group(6))

        # Individual costume HIT
        m = re.search(r'costume HIT: actor=(\d+) costume=(\d+) cel=(\d+) pos=\((\d+),(\d+)\) surf=(\d+)x(\d+)', line)
        if m:
            result["costume_hits"].append({
                "actor": int(m.group(1)),
                "costume": int(m.group(2)),
                "cel": int(m.group(3)),
                "pos": (int(m.group(4)), int(m.group(5))),
                "surf": (int(m.group(6)), int(m.group(7))),
            })

        # Individual costume MISS
        m = re.search(r'costume MISS: actor=(\d+) costume=(\d+) cel=(\d+)', line)
        if m:
            result["costume_misses"].append({
                "actor": int(m.group(1)),
                "costume": int(m.group(2)),
                "cel": int(m.group(3)),
            })

        # Step 2.7 fonts
        m = re.search(r'step2\.7 fonts: chars=(\d+) drawn=(\d+)', line)
        if m:
            result["fonts"]["chars_drawn"] = int(m.group(1))

        # Off-screen costumes
        if 'off-screen' in line:
            result["issues"].append(line.strip())

    return result


def diagnose(result):
    lines = []
    lines.append("=" * 60)
    lines.append(f"  HD TEXTURE DIAGNOSE: {result['file']}")
    lines.append("=" * 60)
    lines.append("")

    # Rooms
    lines.append(f"Räume besucht:     {result['rooms']}")
    lines.append(f"Frames analysiert: {result['frames']}")
    lines.append("")

    # Background
    bg = result["background"]
    status = "✅ HD" if bg["loaded"] else "❌ SD (skaliert)"
    lines.append("── Step 1: HD Background ──")
    lines.append(f"  Status:          {status}")
    lines.append(f"  fgPixel %:       {bg['fg_pct']:.1f}%")
    lines.append(f"  Clean Valid:     {'✅' if bg['clean_valid'] else '❌'}")
    lines.append("")

    # Objects
    obj = result["objects"]
    lines.append("── Step 2.5: HD Objects ──")
    lines.append(f"  Geladen:         {obj['loaded']}")
    lines.append(f"  Skipped (kein HD): {obj['skipped']}")
    lines.append(f"  Culled (unsichtbar): {obj['culled']}")
    lines.append("")

    # Costumes
    cost = result["costumes"]
    lines.append("── Step 2.6: HD Costumes ──")
    lines.append(f"  Geladen:         {cost['loaded']}")
    lines.append(f"  Kein Kostüm:     {cost['noCostume']}")
    lines.append(f"  Kein Cel:        {cost['noCel']}")
    lines.append(f"  Kein HD Asset:   {cost['noHdCostume']}")
    lines.append(f"  Load Failed:     {cost['loadFail']}")
    lines.append("")

    # Unique costume hits
    unique_hits = {}
    for h in result["costume_hits"]:
        key = (h["actor"], h["costume"])
        if key not in unique_hits:
            unique_hits[key] = h
    if unique_hits:
        lines.append("  HD-HITS (einzigartig):")
        for (actor, costume), h in sorted(unique_hits.items()):
            lines.append(f"    Actor {actor}: costume {costume:04d} → cel {h['cel']} pos={h['pos']} surf={h['surf'][0]}x{h['surf'][1]}")
        lines.append("")

    # Unique costume misses
    unique_misses = {}
    for m in result["costume_misses"]:
        key = (m["actor"], m["costume"])
        if key not in unique_misses:
            unique_misses[key] = m
    if unique_misses:
        lines.append("  FEHLENDE HD-ASSETS:")
        for (actor, costume), m in sorted(unique_misses.items()):
            lines.append(f"    Actor {actor}: costume {costume:04d} → keine HD-Datei")
        lines.append("")

    # Fonts
    font = result["fonts"]
    lines.append("── Step 2.7: HD Fonts ──")
    lines.append(f"  Font Manager:    {'✅' if font['fontMgr_enabled'] else '❌'}")
    lines.append(f"  Chars Recorded:  {font['chars_recorded']}")
    lines.append(f"  Chars Drawn:     {font['chars_drawn']}")
    lines.append("")

    # Issues
    if result["issues"]:
        lines.append("── ISSUES ──")
        for issue in result["issues"]:
            lines.append(f"  ⚠️  {issue}")
        lines.append("")

    # Summary
    lines.append("── ZUSAMMENFASSUNG ──")
    problems = []
    if not bg["loaded"]:
        problems.append("Kein HD-Background (nur SD-Skalierung)")
    if cost["noHdCostume"] > 0:
        problems.append(f"{cost['noHdCostume']} Actors haben keine HD-Costume-Assets")
    if cost["loadFail"] > 0:
        problems.append(f"{cost['loadFail']} HD-Costume-Loads fehlgeschlagen")
    if font["chars_recorded"] == 0:
        problems.append("Keine HD-Font-Chars aufgezeichnet (kein Text im Raum?)")
    if result["issues"]:
        problems.append(f"{len(result['issues'])} Rendering-Issues (off-screen)")

    if problems:
        lines.append("  ❌ PROBLEME:")
        for p in problems:
            lines.append(f"    - {p}")
    else:
        lines.append("  ✅ Alles OK — HD-Assets werden korrekt gerendert")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Auto-find latest log
        logdir = "logs"
        if os.path.isdir(logdir):
            logs = sorted([f for f in os.listdir(logdir) if f.startswith("hd_debug_") and f.endswith(".log")])
            if logs:
                filepath = os.path.join(logdir, logs[-1])
            else:
                print("Keine Logs gefunden in logs/")
                sys.exit(1)
        else:
            print(f"Verzeichnis {logdir} nicht gefunden")
            sys.exit(1)
    else:
        filepath = sys.argv[1]

    result = parse_log(filepath)
    print(diagnose(result))
