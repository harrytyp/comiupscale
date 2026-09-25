#!/usr/bin/env python3
"""Test der Wurzelreparatur aus Issue #23.

Prueft, was ohne GPU-Stack pruefbar ist:
  1. Maskenerkennung je Raum an den Rohbildern (comi-original-assets.zip)
  2. tRNS-Rundlauf: Maske als Transparenz schreiben und wieder lesen
  3. Uebereinstimmung der so gewonnenen Maske mit den freigegebenen HD-Texturen
  4. Fuellroutine als Referenz ohne cv2, damit die Maskenfarbe nicht ins Motiv gezogen wird

Aufruf: python3 scripts/test_root_fix.py [--sheet /pfad/blatt.png]
"""
import io
import os
import sys
import zipfile
import argparse

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mask_detect import (dominant_border_index, room_mask_index, save_with_mask,
                         mask_from_transparency, fill_masked_area)

RAW = "/opt/data/dist/comi-original-assets.zip"
HD = "/opt/data/local/comi-hd-repo/release/linux/hd"


def load_raws(limit_per_room=60):
    rooms = {}
    with zipfile.ZipFile(RAW) as z:
        for n in z.namelist():
            if not n.startswith("objects/") or not n.endswith(".png"):
                continue
            base = os.path.basename(n)
            room = base.split("_")[0]
            rooms.setdefault(room, []).append((base, z.read(n)))
    return rooms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default="/opt/data/projects/comi-hd/reports/rootfix-mask.png")
    args = ap.parse_args()

    rooms = load_raws()
    print("=== 1. Maskenerkennung je Raum (Mehrheit der Objektbilder) ===")
    detections = {}
    for room in sorted(rooms):
        files = rooms[room][:60]
        images = [Image.open(io.BytesIO(b)) for _n, b in files]
        idx, votes, total = room_mask_index(images)
        colour = "-"
        if idx is not None and images[0].mode == "P":
            pal = images[0].getpalette() or []
            colour = tuple(int(v) for v in pal[idx * 3:idx * 3 + 3]) if len(pal) >= idx * 3 + 3 else "-"
        detections[room] = idx
        print("  Raum %-4s Index %-5s Farbe %-16s Stimmen %d/%d" % (room, idx, colour, votes, total))

    print("\n=== 2. tRNS-Rundlauf ===")
    base = Image.new("P", (16, 16))
    base.putpalette([0, 0, 0, 227, 0, 195] + [0] * 762)
    arr = np.zeros((16, 16), dtype=np.uint8)
    arr[4:12, 4:12] = 1
    base.putdata(arr.ravel().tolist())
    tmp = "/tmp/rootfix_trns.png"
    save_with_mask(base, tmp, 0)
    back = Image.open(tmp)
    m = mask_from_transparency(back)
    ok_read = back.info.get("transparency") == 0
    ok_mask = m is not None and int(m[8, 8]) == 0 and int(m[0, 0]) == 255
    print("  transparency gelesen: %s | Maske korrekt: %s (Mitte %s, Ecke %s)"
          % (ok_read, ok_mask, m[8, 8] if m is not None else "-", m[0, 0] if m is not None else "-"))

    print("\n=== 3. Maske gegen die freigegebenen HD-Texturen, je Raum ===")
    samples = []
    for room in sorted(rooms):
        idx = detections[room]
        if idx is None:
            continue
        checked_room = 0
        worst_room = 0.0
        worst_name = "-"
        for base_name, blob in rooms[room][:60]:
            hd_path = os.path.join(HD, "objects", base_name)
            if not os.path.exists(hd_path):
                continue
            raw = Image.open(io.BytesIO(blob))
            mask = (np.array(raw) == idx).astype(np.uint8) * 255
            hd = np.array(Image.open(hd_path).convert("RGBA"))
            if hd.shape[0] != mask.shape[0] * 4 or hd.shape[1] != mask.shape[1] * 4:
                continue
            hd_small = np.array(Image.fromarray(hd[:, :, 3]).resize(
                (mask.shape[1], mask.shape[0]), Image.Resampling.NEAREST))
            # Die Maske der Quelle ist im HD-Bild die *transparente* Flaeche, also das Gegenteil
            # des sichtbaren Bereichs.
            expected_visible = np.where(mask > 127, 0, 255).astype(np.uint8)
            hd_visible = np.where(hd_small > 127, 255, 0).astype(np.uint8)
            mismatch = float((hd_visible != expected_visible).mean())
            checked_room += 1
            if mismatch > worst_room:
                worst_room, worst_name = mismatch, base_name
            if len(samples) < 4:
                rgb = np.array(raw.convert("RGB"))
                mag = int(((rgb[:, :, 0] > 200) & (rgb[:, :, 2] > 150) & (rgb[:, :, 1] < 60)).sum())
                if mag > 500:
                    samples.append((base_name, blob, mask))
        if checked_room:
            note = "  (vom Reparaturschritt gesetzt)" if room == "0003" else ""
            print("  Raum %-4s Dateien %-3d groesste Abweichung %7.3f %%  %s%s"
                  % (room, checked_room, worst_room * 100, worst_name[:34], note))

    print("\n=== 4. Fuellroutine (Referenz ohne cv2) ===")
    if not samples:
        print("  keine Abweichung gefunden, nichts zu fuellen")
    for base_name, blob, mask in samples[:2]:
        raw = Image.open(io.BytesIO(blob)).convert("RGB")
        rgb = np.array(raw)
        magenta_before = int(((rgb[:, :, 0] > 200) & (rgb[:, :, 2] > 150) & (rgb[:, :, 1] < 60)).sum())
        filled = fill_masked_area(rgb, mask)
        magenta_after = int(((filled[:, :, 0] > 200) & (filled[:, :, 2] > 150) & (filled[:, :, 1] < 60)).sum())
        print("  %-40s Magenta vorher %6d  nachher %6d" % (base_name[:40], magenta_before, magenta_after))

    # Blatt: roh, gefuellt, mit binaerer Maske
    rows = samples[:4]
    if rows:
        CELL = 240
        sheet = Image.new("RGB", (CELL * 3 + 40, 30 + len(rows) * (CELL + 22)), (18, 18, 18))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), "Wurzelfix (Issue #23): links roh mit Maske | Mitte Maskenfarbe entfernt (wird unsichtbar) | rechts Endergebnis, binaere Maske wie im Spiel", fill=(255, 255, 255))
        y = 28
        for base_name, blob, mask in rows:
            raw = Image.open(io.BytesIO(blob)).convert("RGB")
            rgb = np.array(raw)
            filled = fill_masked_area(rgb, mask)
            tiles = [raw, Image.fromarray(filled)]
            # rechts das gefuellte Motiv mit der binaeren Maske auf neutralem Grund
            mimg = Image.new("RGBA", raw.size, (40, 50, 72, 255))
            mimg.alpha_composite(Image.fromarray(np.dstack([filled, 255 - mask])).convert("RGBA"))
            tiles.append(mimg.convert("RGB"))
            for i, t in enumerate(tiles):
                t = t.copy(); t.thumbnail((CELL, CELL), Image.Resampling.LANCZOS)
                sheet.paste(t, (10 + i * (CELL + 10), y))
            d.text((10, y + CELL + 2), base_name[:44], fill=(220, 220, 220))
            y += CELL + 22
        os.makedirs(os.path.dirname(args.sheet), exist_ok=True)
        sheet.save(args.sheet)
        print("\nPruefblatt: %s" % args.sheet)


if __name__ == "__main__":
    main()
