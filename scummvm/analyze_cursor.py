import struct
import os

dump_dir = "C:/Users/go75bel/scummvm-fork"

# Virtscr dump: 640x480, 1 byte per pixel (CLUT8 index)
with open(dump_dir + "/hd_dump_4_virtscr.raw", "rb") as f:
    virtscr = f.read()

# Composite dump: 2560x1920 RGBA (4 bytes per pixel)
with open(dump_dir + "/hd_dump_4_composite.raw", "rb") as f:
    composite = f.read()

# Check if composite vs hdcomposite differ
with open(dump_dir + "/hd_dump_4_hdcomposite.raw", "rb") as f:
    hdcomposite = f.read()

mouse_x = 273
mouse_y = 80
hd_mouse_x = mouse_x * 4
hd_mouse_y = mouse_y * 4

print("=== Analysis of room 87 (main menu) at frame 4 ===")
print(f"Mouse at game ({mouse_x},{mouse_y}) -> HD ({hd_mouse_x},{hd_mouse_y})")

# Virtscr check: what pixels are at mouse position?
virtscr_w = 640
print("\n--- Virtscr: pixel values in 16x16 around mouse ---")
for y in range(max(0,mouse_y-4), min(480,mouse_y+12)):
    row = y * virtscr_w
    px = [f"{virtscr[row + x]:02x}" for x in range(max(0,mouse_x-4), min(640,mouse_x+12))]
    print(f"  y={y:3d}: {' '.join(px)}")

# Check for unique non-zero values in virtscr (things that are foreground)
print("\n--- Unique non-zero pixel values in virtscr ---")
unique_vals = set()
for i in range(len(virtscr)):
    if virtscr[i] != 0:
        unique_vals.add(virtscr[i])
print(f"  Values: {sorted(unique_vals)[:30]}")

# Compare composite vs hdcomposite (should differ if any compositing happened)
print("\n--- Composite vs HDComposite diff check ---")
hd_w = 2560
hd_h = 1920
diff_count = 0
pixel_diff_count = 0
for i in range(0, len(composite), 4):
    if composite[i:i+4] != hdcomposite[i:i+4]:
        pixel_diff_count += 1
        if diff_count < 3:
            pixel_idx = i // 4
            ox = pixel_idx % hd_w
            oy = pixel_idx // hd_w
            c_px = tuple(composite[i:i+4])
            h_px = tuple(hdcomposite[i:i+4])
            print(f"  Diff at ({ox},{oy}): comp={c_px} hd={h_px}")
            diff_count += 1
print(f"  Total pixel diffs: {pixel_diff_count}/{hd_w*hd_h}")

# Check pixels around HD mouse position in composite
print(f"\n--- HD Composite RGBA at mouse HD ({hd_mouse_x},{hd_mouse_y}) ---")
for y in range(max(0,hd_mouse_y-12), min(hd_h,hd_mouse_y+12)):
    row_offset = y * hd_w * 4
    px = []
    for x in range(max(0,hd_mouse_x-12), min(hd_w,hd_mouse_x+12)):
        offset = row_offset + x * 4
        r,g,b,a = composite[offset:offset+4]
        px.append(f"{r:02x}{g:02x}{b:02x}")
    print(f"  y={y:4d}: {' '.join(px)}")

print("\nDone.")
