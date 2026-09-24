#!/usr/bin/env python3
"""Pipeline-Schritt: HD-Texturen aus der Quellmaske ableiten (ersetzt Farbraten).

Warum: die Quellbilder der Pipeline sind 8-Bit-Palettenbilder ohne Alpha, die
Maske steckt in einem Paletteneintrag. Ein farbbasiertes Entfernen hat bei Logo
und Raumobjekten echtes Violett mitgenommen. Diese Stufe fragt stattdessen die
Quelle: mask_index() prueft Palettenfarbe UND Randberuehrung. Faellt die Pruefung
durch, bleibt die Textur unveraendert.

Was die Stufe tut, wenn eine Maske gefunden ist:
  1. Maske auf HD-Groesse skalieren (bilinear, weiche Kante)
  2. Alpha der HD-Textur darauf setzen (Alpha wird nur verkleinert, nie erhoeht)
  3. RGB der Maskenflaeche aus der Nachbarschaft auffuellen, damit kein
     Magenta- oder Pinkstich in den weichen Kanten stehen bleibt

Pruefregel fuer jeden Lauf: geaenderte Pixel muessen innerhalb der auf 1 px
gedilateten Maskenflaeche liegen. Sonst bricht die Datei ab.

Aufruf:
    python3 scripts/fix_mask_alpha.py --hd release/linux/hd/objects --src-zip /opt/data/dist/comi-original-assets.zip --dry-run
    python3 scripts/fix_mask_alpha.py --hd release/linux/hd/objects --src-zip /opt/data/dist/comi-original-assets.zip --apply --backup DIR
Optionen:
    --src DIR        Ordner mit den extrahierten 1x-Quellen (statt ZIP)
    --prefix objects|objects_layers   Ordnerpraefix in der Quelle (Standard: objects)
    --file NAME      nur diese Datei(en) verarbeiten
"""
import argparse
import glob
import io
import os
import shutil
import sys
import zipfile

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mask_index import mask_index  # noqa: E402

MAX_REPORT = 12


def _strip_room(name):
    parts = name.split("_", 1)
    return parts[1] if len(parts) == 2 and len(parts[0]) == 4 and parts[0].isdigit() else name


def source_bytes(src_zip, src_dir, prefix, name):
    """Quellbild zur HD-Textur finden. Die Paketnamen tragen teils ein anderes
    Raumprefix (0000_) als die Texturen (z.B. 0022_), daher ueber den Namen
    ohne fuehrende vierstellige Zahl suchen."""
    wanted = _strip_room(name)
    if src_zip:
        with zipfile.ZipFile(src_zip) as z:
            candidates = ["%s/%s" % (prefix, name), "%s/0000_%s" % (prefix, name),
                          "%s/%s" % (prefix, wanted), "%s/0000_%s" % (prefix, wanted)]
            for cand in candidates:
                try:
                    return z.read(cand)
                except KeyError:
                    continue
            for entry in z.namelist():
                if entry.startswith(prefix + "/") and _strip_room(os.path.basename(entry)) == wanted:
                    return z.read(entry)
            return None
    if src_dir:
        for cand in (name, "0000_" + name, wanted, "0000_" + wanted):
            p = os.path.join(src_dir, cand)
            if os.path.exists(p):
                return open(p, "rb").read()
    return None


def dilate(mask, radius=1):
    out = mask.copy()
    for _ in range(radius):
        out = (out | np.roll(out, 1, 0) | np.roll(out, -1, 0)
                   | np.roll(out, 1, 1) | np.roll(out, -1, 1))
    return out


def fill_from_neighbours(rgb, hole, radius=3):
    """Farben in `hole` durch Mittelwerte der umliegenden Nicht-Loch-Pixel ersetzen."""
    out = rgb.copy()
    known = ~hole
    acc = np.zeros_like(rgb, dtype=float)
    cnt = np.zeros(hole.shape, dtype=float)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            shifted = np.roll(np.roll(known, dy, 0), dx, 1)
            vals = np.roll(np.roll(rgb, dy, 0), dx, 1).astype(float)
            w = shifted & hole
            acc[w] += vals[w]
            cnt[w] += 1
    use = hole & (cnt > 0)
    out[use] = (acc[use] / cnt[use][:, None]).astype(np.uint8)
    return out


def process(hd_path, src_zip, src_dir, prefix):
    name = os.path.basename(hd_path)
    raw = source_bytes(src_zip, src_dir, prefix, name)
    if raw is None:
        return {"file": name, "status": "keine Quelle"}
    src = Image.open(io.BytesIO(raw))
    info = mask_index(src)
    if info is None:
        return {"file": name, "status": "keine Maske in der Quelle, unveraendert"}
    src_arr = np.array(src)
    m = (src_arr == info["index"]).astype(np.uint8) * 255

    hd = Image.open(hd_path)
    rgb = np.array(hd.convert("RGB"))
    alpha_old = np.array(hd.convert("RGBA"))[:, :, 3]
    h, w = alpha_old.shape

    # Maske mit NEAREST, weil die Spielmaske binaer ist. Mit einer weichen Kante
    # bleiben halbtransparente Pixel mit Magentastich stehen (Restfahne).
    mask_hd = np.array(Image.fromarray(m, mode="L").resize((w, h), Image.Resampling.NEAREST))
    alpha_new = np.minimum(alpha_old, 255 - mask_hd)         # Alpha nur verkleinern

    hole = alpha_new == 0
    # Randstreifen innen: Pixel direkt neben der Maske, deren Farbe noch in der
    # Magentafamilie liegt, werden aus der Nachbarschaft gefuellt. Andere Farben
    # bleiben unberuehrt, das ist Grafik.
    band = dilate(hole, 2) & ~hole
    r, g, b = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
    magentaish = ((r > 140) & (b > 120) & (g < 100)) | ((r > g + 30) & (b > g + 30) & (r > 120) & (b > 100) & (g < 160))
    to_fill = band & magentaish
    rgb_new = fill_from_neighbours(rgb, hole | to_fill)

    changed = (alpha_new != alpha_old) | (rgb_new != rgb).any(axis=2)
    allowed = dilate(mask_hd > 0, 2) | dilate(hole, 2)
    outside = int((changed & ~allowed).sum())

    rep = {
        "file": name,
        "maskenindex": info["index"],
        "randanteil": round(info["border_share"], 2),
        "pixel_geaendert": int(changed.sum()),
        "randstreifen_gefuellt": int(to_fill.sum()),
        "ausserhalb_maske": outside,
        "opak_vorher": int((alpha_old > 128).sum()),
        "opak_nachher": int((alpha_new > 128).sum()),
    }
    if outside:
        rep["status"] = "ABBRUCH: Pixel ausserhalb der Maske betroffen"
        return rep
    rep["_data"] = np.dstack([rgb_new, alpha_new]).astype(np.uint8)
    rep["status"] = "ok"
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hd", required=True)
    ap.add_argument("--src-zip", default=None)
    ap.add_argument("--src", default=None)
    ap.add_argument("--prefix", default="objects")
    ap.add_argument("--file", action="append", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup", default=None)
    args = ap.parse_args()

    names = args.file or sorted(os.path.basename(p) for p in glob.glob(os.path.join(args.hd, "*.png")))
    if args.apply and args.backup:
        os.makedirs(args.backup, exist_ok=True)
        for n in names:
            shutil.copy2(os.path.join(args.hd, n), os.path.join(args.backup, n))
        print("Sicherung nach", args.backup)

    stats = {"ok": 0, "keine Maske": 0, "keine Quelle": 0, "abgebrochen": 0}
    changed_total = 0
    shown = 0
    for n in names:
        p = os.path.join(args.hd, n)
        if not os.path.exists(p):
            continue
        rep = process(p, args.src_zip, args.src, args.prefix)
        st = rep["status"]
        if st == "ok":
            stats["ok"] += 1
            changed_total += rep["pixel_geaendert"]
            if args.apply and not args.dry_run:
                Image.fromarray(rep["_data"], "RGBA").save(p)
        elif st.startswith("keine Maske"):
            stats["keine Maske"] += 1
        elif st == "keine Quelle":
            stats["keine Quelle"] += 1
        else:
            stats["abgebrochen"] += 1
            print("ABBRUCH", rep)
        if st == "ok" and shown < MAX_REPORT:
            shown += 1
            print("  %-46s Index %3d (Rand %.2f) geaendert %6d opak %d -> %d" %
                  (rep["file"], rep["maskenindex"], rep["randanteil"], rep["pixel_geaendert"],
                   rep["opak_vorher"], rep["opak_nachher"]))
    print("-" * 78)
    print("Dateien: %d | mit Maske bearbeitet: %d | ohne Maskenindex uebersprungen: %d | ohne Quelle: %d | Abbrueche: %d"
          % (len(names), stats["ok"], stats["keine Maske"], stats["keine Quelle"], stats["abgebrochen"]))
    print("geaenderte Pixel gesamt:", changed_total, "| Modus:", "apply" if args.apply and not args.dry_run else "dry-run")


if __name__ == "__main__":
    main()
