#!/usr/bin/env python3
"""Analyze HD debug dumps from ScummVM fork."""
import sys, struct, os

def read_raw(path, w, h, bpp=4):
    """Read a raw RGBA or 8-bit file."""
    with open(path, 'rb') as f:
        data = f.read()
    expected = w * h * bpp
    if len(data) < expected:
        print(f"  WARNING: {path}: expected {expected}B, got {len(data)}B")
        data = data + b'\x00' * (expected - len(data))
    if bpp == 4:
        pixels = []
        for y in range(h):
            row = []
            for x in range(w):
                off = (y * w + x) * 4
                r, g, b, a = data[off], data[off+1], data[off+2], data[off+3]
                row.append((r, g, b, a))
            pixels.append(row)
        return pixels
    else:
        pixels = []
        for y in range(h):
            row = []
            for x in range(w):
                row.append(data[y * w + x])
            pixels.append(row)
        return pixels

def read_palette(path):
    """Read palette text file."""
    pal = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 4:
                pal.append((int(parts[1]), int(parts[2]), int(parts[3])))
    return pal

def check_cursor(composite, state_path, mouse_x, mouse_y):
    """Check if cursor is visible at mouse position."""
    hdW, hdH = 2560, 1920
    gameW, gameH = 640, 480
    
    # Scale mouse to HD coords (assumes 4x)
    mx = mouse_x * 4
    my = mouse_y * 4
    
    # Look for non-HD-bg pixels around the cursor position
    # Sample a small area around the cursor
    found_cluster = 0
    total_pixels = 0
    for dy in range(-16, 16):
        for dx in range(-16, 16):
            px, py = mx + dx, my + dy
            if 0 <= px < hdW and 0 <= py < hdH:
                total_pixels += 1
                r, g, b, a = composite[py][px]
                # Check if pixel is not the typical HD bg teal/gradient
                # HD bg at center tends to have g around 128-200, b around 128-200
                # A cursor (cyan) would have r=0, g=255, b=255
                # But first, let's just check for any pixel that's "unusual"
                if g > 200 and b > 200 and r < 50:
                    found_cluster += 1
    
    coverage = found_cluster / max(1, total_pixels) * 100
    return found_cluster, coverage

def check_foreground_pixels(composite, hd_composite, threshold=10):
    """Check how many pixels differ between composite (HD bg+game) and hd_composite (just HD bg).
    Actually they should be the same since composite = hd_composite + game overlay.
    Compare composite vs a "clean" reference.
    """
    # For now, just check how many non-background pixels exist
    # Sample at regular intervals
    hdW, hdH = 2560, 1920
    foreground_count = 0
    total = 0
    
    # Check around center of screen where actors should be
    for y in range(hdH//4, 3*hdH//4, 8):
        for x in range(hdW//4, 3*hdW//4, 8):
            total += 1
            r, g, b, a = composite[y][x]
            # HD bg at center: g is typically 80-180, b 128-200
            # Foreground should have different colors
            # Check if it's NOT a typical HD bg gradient color
            is_gradient = (abs(g - b) < 40 and r < 100 and g > 60)
            if not is_gradient:
                foreground_count += 1
    
    return foreground_count, total

def main():
    dump_dir = "."
    frame = 90
    
    hdW, hdH = 2560, 1920
    gW, gH = 640, 480
    
    print(f"=== Analyzing HD Debug Dump (frame {frame}) ===\n")
    
    # Load files
    composite_path = os.path.join(dump_dir, f"hd_dump_{frame}_composite.raw")
    hdcomp_path = os.path.join(dump_dir, f"hd_dump_{frame}_hdcomposite.raw")
    clean_path = os.path.join(dump_dir, f"hd_dump_{frame}_clean.raw")
    valid_path = os.path.join(dump_dir, f"hd_dump_{frame}_valid.raw")
    virtscr_path = os.path.join(dump_dir, f"hd_dump_{frame}_virtscr.raw")
    palette_path = os.path.join(dump_dir, f"hd_dump_{frame}_palette.txt")
    state_path = os.path.join(dump_dir, f"hd_dump_{frame}_state.txt")
    
    # Read state
    with open(state_path) as f:
        print("=== Engine State ===")
        for line in f:
            print(f"  {line.strip()}")
    
    # Read palette
    palette = read_palette(palette_path)
    print(f"\n=== Palette: {len(palette)} entries loaded ===")
    
    # Check specific cursor palette index
    # In COMI, cursor typically uses palette indices near 255
    for i in [252, 253, 254, 255]:
        if i < len(palette):
            r, g, b = palette[i]
            print(f"  Palette[{i}]: RGB({r},{g},{b})")
    
    # Read composite (OGL framebuffer, has cursor)
    print(f"\n=== Analyzing Composite (2560x1920 RGBA) ===")
    composite = read_raw(composite_path, hdW, hdH, 4)
    
    # Sample corners to verify HD background
    print("Corner samples (should be HD bg):")
    corners = [(0,0), (hdW-1,0), (0,hdH-1), (hdW-1,hdH-1), (hdW//2, hdH//2)]
    for cx, cy in corners:
        r, g, b, a = composite[cy][cx]
        print(f"  ({cx},{cy}): RGBA({r},{g},{b},{a})")
    
    # Sample mouse position 
    mouse_x, mouse_y = 639, 479  # from state
    mx, my = mouse_x * 4, mouse_y * 4
    print(f"\n=== Cursor Check ===")
    print(f"Mouse at game coords ({mouse_x},{mouse_y}) -> HD ({mx},{my})")
    
    # Sample around mouse
    print(f"Pixels around cursor position:")
    for dy in [-16, -8, -4, -2, 0, 2, 4, 8, 16]:
        for dx in [-16, -8, -4, -2, 0, 2, 4, 8, 16]:
            px, py = mx + dx, my + dy
            if 0 <= px < hdW and 0 <= py < hdH:
                r, g, b, a = composite[py][px]
                print(f"    ({px},{py}) ({dx:+d},{dy:+d}): RGBA({r},{g},{b},{a})", end="")
                # Check if this looks like a cursor pixel (cyan or distinct from surroundings)
                if g > 200 and b > 200 and r < 50:
                    print(" <-- CYAN (cursor?)", end="")
                print()
        break  # just first row for now
    
    # Check for cyan pixels anywhere (cursor)
    print(f"\nSearching for cyan cursor pixels (R<50, G>200, B>200):")
    cyan_pixels = []
    for y in range(0, hdH, 4):
        for x in range(0, hdW, 4):
            r, g, b, a = composite[y][x]
            if g > 200 and b > 200 and r < 50:
                cyan_pixels.append((x, y, r, g, b))
                if len(cyan_pixels) >= 10:
                    break
        if len(cyan_pixels) >= 10:
            break
    print(f"  Found {len(cyan_pixels)} cyan-ish pixels (first 10):")
    for x, y, r, g, b in cyan_pixels[:10]:
        print(f"    ({x},{y}): RGBA({r},{g},{b})")
    
    # Check for any non-HD-bg pixels in the center area
    print(f"\n=== Foreground Content Check ===")
    fg_count, total_px = check_foreground_pixels(composite, composite)
    print(f"  Non-gradient pixels in center: {fg_count}/{total_px} ({fg_count/max(1,total_px)*100:.1f}%)")
    
    # Load virtscr and check what's there
    print(f"\n=== Virtual Screen (640x480 8-bit) ===")
    vs = read_raw(virtscr_path, gW, gH, 1)
    
    # Sample center of screen
    print(f"Center pixel values (8-bit indices):")
    for y in range(gH//2 - 10, gH//2 + 10, 4):
        for x in range(gW//2 - 10, gW//2 + 10, 4):
            idx = vs[y][x]
            r, g, b = palette[idx]
            if idx != 0x10 and idx != 0:  # Not default bg
                print(f"    ({x},{y}): idx={idx:#04x} RGB({r},{g},{b})")
        break
    
    # Check clean background diff
    print(f"\n=== Clean Background vs Virstscr Diff ===")
    clean_bg = read_raw(clean_path, gW, gH, 1)
    valid = read_raw(valid_path, gW, gH, 1)
    
    diff_count = 0
    total_valid = 0
    for y in range(gH):
        for x in range(gW):
            if valid[y][x]:
                total_valid += 1
                if vs[y][x] != clean_bg[y][x]:
                    diff_count += 1
    print(f"  Clean Valid pixels: {total_valid}/{gW*gH}")
    print(f"  Pixels that DIFFER from clean: {diff_count}/{total_valid} ({diff_count/max(1,total_valid)*100:.1f}%)")
    
    if diff_count > 0:
        print(f"  Sample differing pixels:")
        found = 0
        for y in range(gH):
            for x in range(gW):
                if valid[y][x] and vs[y][x] != clean_bg[y][x]:
                    found += 1
                    if found <= 5:
                        print(f"    ({x},{y}): vs={vs[y][x]:#04x} clean={clean_bg[y][x]:#04x} pal={palette[vs[y][x]]}")
    
    print(f"\n=== Summary ===")
    print(f"  HD composite written: YES ({hdW}x{hdH})")
    print(f"  FPS: {'OK' if total_valid > 0 else 'PROBLEM'}")
    print(f"  Foreground detected: {'YES' if fg_count > 10 else 'NO - empty screen!'}")
    print(f"  Diff against clean: {'YES - compositing works' if diff_count > 0 else 'NO - no foreground!'}")

if __name__ == '__main__':
    main()
