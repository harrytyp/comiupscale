#!/usr/bin/env python3
"""
HD Asset Diagnose — parse ScummVM HD debug logs and show what works/what doesn't.
No screenshots needed. Just reads the warning() output.
"""

import re
import sys
from collections import defaultdict

def diagnose(logfile):
    with open(logfile) as f:
        lines = f.readlines()

    # Collect per-frame data
    frames = []
    current = {}
    costume_hits = []
    costume_misses = []
    offscreen = []

    for line in lines:
        line = line.strip()

        # Room/frame summary
        m = re.search(r'HDDBG room=(\d+) hdRoom=(\d+) bg=(\d+) objMgr=(\d+)/(\d+) costMgr=(\d+)/(\d+) fontMgr=(\d+)/(\d+) fontChars=(\d+)', line)
        if m:
            if current:
                frames.append(current)
            current = {
                'room': int(m.group(1)),
                'hdRoom': int(m.group(2)),
                'bg': int(m.group(3)),
                'objMgr': int(m.group(4)),
                'objEnabled': int(m.group(5)),
                'costMgr': int(m.group(6)),
                'costEnabled': int(m.group(7)),
                'fontMgr': int(m.group(8)),
                'fontEnabled': int(m.group(9)),
                'fontChars': int(m.group(10)),
            }
            continue

        # Step 2 foreground
        m = re.search(r'step2: fgPixels=(\d+)/(\d+) \(([0-9.]+)%\)', line)
        if m:
            current['fg_pct'] = float(m.group(3))
            continue

        # Step 2.5 objects
        m = re.search(r'step2\.5 objects: loaded=(\d+) skipped=(\d+) culled=(\d+)', line)
        if m:
            current['obj_loaded'] = int(m.group(1))
            current['obj_skipped'] = int(m.group(2))
            current['obj_culled'] = int(m.group(3))
            continue

        # Step 2.6 costumes
        m = re.search(r'step2\.6 costumes: loaded=(\d+) skipped=(\d+) \(noCostume=(\d+) noCel=(\d+) noHdCostume=(\d+) loadFail=(\d+)\)', line)
        if m:
            current['cost_loaded'] = int(m.group(1))
            current['cost_skipped'] = int(m.group(2))
            current['cost_noCostume'] = int(m.group(3))
            current['cost_noCel'] = int(m.group(4))
            current['cost_noHdCostume'] = int(m.group(5))
            current['cost_loadFail'] = int(m.group(6))
            continue

        # Step 2.7 fonts
        m = re.search(r'step2\.7 fonts: chars=(\d+) drawn=(\d+)', line)
        if m:
            current['font_chars'] = int(m.group(1))
            current['font_drawn'] = int(m.group(2))
            continue

        # Costume HIT
        m = re.search(r'HDDBG costume HIT: actor=(\d+) costume=(\d+) cel=(\d+) pos=\((\d+),(\d+)\) surf=(\d+)x(\d+)', line)
        if m:
            costume_hits.append({
                'actor': int(m.group(1)),
                'costume': int(m.group(2)),
                'cel': int(m.group(3)),
                'pos': (int(m.group(4)), int(m.group(5))),
                'surf': (int(m.group(6)), int(m.group(7))),
            })
            continue

        # Costume MISS
        m = re.search(r'HDDBG costume MISS: actor=(\d+) costume=(\d+) cel=(\d+)', line)
        if m:
            costume_misses.append({
                'actor': int(m.group(1)),
                'costume': int(m.group(2)),
                'cel': int(m.group(3)),
            })
            continue

        # Off-screen
        if 'off-screen' in line:
            offscreen.append(line)

    if current:
        frames.append(current)

    # ── Report ──
    print(f"{'='*60}")
    print(f"  HD ASSET DIAGNOSE: {logfile}")
    print(f"{'='*60}")
    print()

    # Unique rooms
    rooms = set(f['room'] for f in frames)
    print(f"Räume besucht:     {rooms}")
    print(f"Frames analysiert: {len(frames)}")
    print()

    if not frames:
        print("Keine HDDBG-Zeilen im Log gefunden!")
        return

    # Last frame has the final state
    last = frames[-1]

    # Background
    bg_ok = last.get('bg', 0)
    print("── Step 1: HD Background ──")
    print(f"  Status:       {'✅ geladen' if bg_ok else '❌ nicht geladen'}")
    if 'fg_pct' in last:
        print(f"  fgPixel %:    {last['fg_pct']:.1f}%")
    print()

    # Objects
    print("── Step 2.5: HD Objects ──")
    print(f"  Geladen:      {last.get('obj_loaded', '?')}")
    print(f"  Skipped:      {last.get('obj_skipped', '?')} (kein HD-Asset)")
    print(f"  Culled:       {last.get('obj_culled', '?')} (unsichtbar)")
    print()

    # Costumes
    print("── Step 2.6: HD Costumes ──")
    print(f"  Geladen:      {last.get('cost_loaded', '?')}")
    print(f"  Skipped:      {last.get('cost_skipped', '?')}")
    print(f"  Kein Kostüm:  {last.get('cost_noCostume', '?')} (Actor nicht aktiv)")
    print(f"  Kein Cel:     {last.get('cost_noCel', '?')}")
    print(f"  Kein HD-File: {last.get('cost_noHdCostume', '?')} (HD-Datei fehlt)")
    print(f"  Load Failed:  {last.get('cost_loadFail', '?')}")
    print()

    # Unique costume hits (group by actor+costume)
    if costume_hits:
        seen = set()
        print("  HD-Costume TREFFER:")
        for h in costume_hits:
            key = (h['actor'], h['costume'])
            if key not in seen:
                seen.add(key)
                print(f"    Actor {h['actor']:2d}: costume {h['costume']:04d} → cel {h['cel']:3d} "
                      f"pos={h['pos']} surf={h['surf'][0]}x{h['surf'][1]}")
        print()

    # Unique costume misses
    if costume_misses:
        seen = set()
        print("  FEHLENDE HD-ASSETS:")
        for m in costume_misses:
            key = (m['actor'], m['costume'])
            if key not in seen:
                seen.add(key)
                print(f"    Actor {m['actor']:2d}: costume {m['costume']:04d} → keine HD-Datei")
        print()

    # Off-screen
    if offscreen:
        print("── Off-Screen ──")
        for o in offscreen[:5]:
            print(f"  {o}")
        print()

    # Fonts
    print("── Step 2.7: HD Fonts ──")
    print(f"  Font Manager: {'✅' if last.get('fontMgr') else '❌'}")
    print(f"  Chars recorded: {last.get('fontChars', 0)}")
    if 'font_chars' in last:
        print(f"  Chars drawn:  {last.get('font_drawn', 0)}")
    print()

    # Summary
    print("── ZUSAMMENFASSUNG ──")
    problems = []
    if not bg_ok:
        problems.append("Kein HD-Background → nur SD-Skalierung")
    if last.get('cost_noHdCostume', 0) > 0:
        problems.append(f"{last['cost_noHdCostume']} Actors ohne HD-Costume-Assets")
    if last.get('cost_loadFail', 0) > 0:
        problems.append(f"{last['cost_loadFail']} HD-Costume-Ladevorgänge fehlgeschlagen")
    if last.get('fontChars', 0) == 0 and last.get('fontMgr') == 0:
        problems.append("HD Font Manager nicht aktiv!")
    if offscreen:
        problems.append(f"{len(offscreen)} Off-Screen-Warnungen")

    if problems:
        print("  ❌ PROBLEME:")
        for p in problems:
            print(f"    - {p}")
    else:
        print("  ✅ Alles OK — HD-Assets werden korrekt geladen/gerendert")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 diagnose.py <logfile>")
        print("       python3 diagnose.py logs/hd_debug_boot200_v3.log")
        sys.exit(1)
    diagnose(sys.argv[1])
