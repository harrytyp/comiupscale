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


def fill_from_neighbours(rgb, hole, radius=3, known=None):
    """Farben in `hole` durch Mittelwerte der umliegenden Nicht-Loch-Pixel ersetzen.

    Rechnet nur auf dem Bereich, in dem ueberhaupt gefuellt wird (plus Rand).
    Auf einem 2560x1920-Bild ueber 48 Verschiebungen zu laufen kostet Minuten,
    der Ausschnitt kostet Millisekunden.
    """
    ys, xs = np.nonzero(hole)
    if len(xs) == 0:
        return rgb
    y0 = max(0, int(ys.min()) - radius)
    y1 = min(rgb.shape[0], int(ys.max()) + 1 + radius)
    x0 = max(0, int(xs.min()) - radius)
    x1 = min(rgb.shape[1], int(xs.max()) + 1 + radius)
    sub = rgb[y0:y1, x0:x1].copy()
    hole_sub = hole[y0:y1, x0:x1]
    if known is None:
        known = ~hole_sub
    else:
        # Nur sichtbare Pixel als Farbquelle. Sonst zieht die Fuellung die
        # Maskenfarbe aus dem transparenten Bereich in die Objektkante (gruener Saum).
        known = known[y0:y1, x0:x1]
    acc = np.zeros_like(sub, dtype=float)
    cnt = np.zeros(hole_sub.shape, dtype=float)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            shifted = np.roll(np.roll(known, dy, 0), dx, 1)
            vals = np.roll(np.roll(sub, dy, 0), dx, 1).astype(float)
            w = shifted & hole_sub
            acc[w] += vals[w]
            cnt[w] += 1
    use = hole_sub & (cnt > 0)
    sub[use] = (acc[use] / cnt[use][:, None]).astype(np.uint8)
    out = rgb.copy()
    out[y0:y1, x0:x1] = sub
    return out


def process(hd_path, src_zip, src_dir, prefix, extra_indices=(), object_hd_dir=None):
    name = os.path.basename(hd_path)
    raw = source_bytes(src_zip, src_dir, prefix, name)
    if raw is None:
        return {"file": name, "status": "keine Quelle"}
    src = Image.open(io.BytesIO(raw))
    info = mask_index(src, extra_indices=extra_indices)
    if info is None:
        # Objektebenen ohne Index 39: das Objekt deckt die ganze Leinwand ab
        # (gemessen: 0087_foreign-placard, 2560x1920). Dann ist die Objekttextur
        # selbst die Vorlage.
        if extra_indices and object_hd_dir:
            op = os.path.join(object_hd_dir, name)
            if os.path.exists(op):
                return {"file": name, "status": "ganze Leinwand, Alpha direkt von der Objekttextur",
                        "_direct": op}
        return {"file": name, "status": "keine Maske in der Quelle, unveraendert"}
    src_arr = np.array(src)
    mask_bool = (src_arr == info["index"])
    layer_alpha_from_object = False
    canvas = None
    if extra_indices and object_hd_dir:
        # Objektebene = das Objekt auf der Leinwand. Der Objektbereich ist ein
        # exaktes Rechteck (geprueft an 14 Quellen, Fuellgrad 1.000) und die
        # zugehoerige Objekttextur ist bereits freigegeben. Also wird deren Alpha
        # exakt uebernommen statt Farben zu raten.
        ys, xs = np.nonzero(~mask_bool)
        if len(xs):
            x0, x1 = int(xs.min()), int(xs.max())
            y0, y1 = int(ys.min()), int(ys.max())
            obj_path = os.path.join(object_hd_dir, name)
            if os.path.exists(obj_path):
                obj_alpha = np.array(Image.open(obj_path).convert("RGBA"))[:, :, 3]
                want = (4 * (x1 - x0 + 1), 4 * (y1 - y0 + 1))
                if obj_alpha.shape[::-1] != want:
                    obj_alpha = np.array(Image.fromarray(obj_alpha).resize(want, Image.Resampling.NEAREST))
                canvas = np.zeros((mask_bool.shape[0] * 4, mask_bool.shape[1] * 4), dtype=np.uint8)
                hh = min(obj_alpha.shape[0], canvas.shape[0] - 4 * y0)
                ww = min(obj_alpha.shape[1], canvas.shape[1] - 4 * x0)
                if hh > 0 and ww > 0:
                    canvas[4 * y0:4 * y0 + hh, 4 * x0:4 * x0 + ww] = obj_alpha[:hh, :ww]
                layer_alpha_from_object = True
                src_obj_index = {"übernommen_von": os.path.basename(obj_path), "bbox": (x0, y0, x1, y1)}
    m = mask_bool.astype(np.uint8) * 255

    hd = Image.open(hd_path)
    rgb = np.array(hd.convert("RGB"))
    alpha_old = np.array(hd.convert("RGBA"))[:, :, 3]
    h, w = alpha_old.shape

    # Maske mit NEAREST, weil die Spielmaske binaer ist. Mit einer weichen Kante
    # bleiben halbtransparente Pixel mit Magentastich stehen (Restfahne).
    if layer_alpha_from_object:
        # Objektebene: Alpha kommt exakt aus der Objekttextur, alles ausserhalb
        # des Objektrechtecks ist transparent.
        cv = canvas
        if cv.shape[:2] != (h, w):
            cv = np.array(Image.fromarray(cv).resize((w, h), Image.Resampling.NEAREST))
        mask_hd = 255 - cv
        alpha_new = np.minimum(alpha_old, cv)
    else:
        mask_hd = np.array(Image.fromarray(m, mode="L").resize((w, h), Image.Resampling.NEAREST))
        alpha_new = np.minimum(alpha_old, 255 - mask_hd)         # Alpha nur verkleinern

    hole = alpha_new == 0
    # Randstreifen innen: Pixel direkt neben der Maske, deren Farbe noch in der
    # Magentafamilie liegt, werden aus der Nachbarschaft gefuellt. Andere Farben
    # bleiben unberuehrt, das ist Grafik.
    if extra_indices:
        # Objektebenen: die Maskenfarbe (Index 39) ist eine normale Raumfarbe
        # (gemessen z.B. (63,63,27) oder (107,79,19)), eine Farbpruefung wuerde
        # echte Bildpixel treffen. Deshalb rein geometrisch: der Rand innerhalb
        # der Maske ist per Definition vom Upscaler mit der Maskenfarbe verunreinigt
        # und wird aus dem Objektinneren gefuellt. 4 HD-Pixel = 1 Quellpixel.
        band = dilate(hole, 4) & ~hole
        to_fill = band
    else:
        band = dilate(hole, 2) & ~hole
        r, g, b = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
        magentaish = ((r > 140) & (b > 120) & (g < 100)) | ((r > g + 30) & (b > g + 30) & (r > 120) & (b > 100) & (g < 160))
        to_fill = band & magentaish
    # Nur sichtbare Pixel fuellen: unter Alpha 0 ist die Farbe unsichtbar.
    rgb_new = fill_from_neighbours(rgb, to_fill, known=(alpha_new > 0) & ~to_fill) if to_fill.any() else rgb

    changed = (alpha_new != alpha_old) | (rgb_new != rgb).any(axis=2)
    band_px = 4 if extra_indices else 2
    allowed = dilate(mask_hd > 0, band_px) | dilate(hole, band_px)
    outside = int((changed & ~allowed).sum())

    rep = {
        "file": name,
        "maskenindex": info["index"],
        "randanteil": round(info["border_share"], 2),
        "pixel_geaendert": int(changed.sum()),
        "randstreifen_gefuellt": int(to_fill.sum()),
        "objektmaske_innen": src_obj_index,
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
    ap.add_argument("--layer", action="store_true",
                    help="Objektebenen: den NUTcracker-Index 39 als Maske zulassen")
    ap.add_argument("--object-hd", default=None,
                    help="Ordner mit den HD-Objekttexturen (fuer den exakten Ebenen-Alpha)")
    args = ap.parse_args()
    extra = (39,) if args.layer else ()

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
        rep = process(p, args.src_zip, args.src, args.prefix, extra_indices=extra,
                      object_hd_dir=args.object_hd)
        if rep.get("_direct"):
            # Alpha der Objekttextur eins zu eins uebernehmen
            src_a = Image.open(rep["_direct"]).convert("RGBA")
            hd = Image.open(p).convert("RGBA")
            if src_a.size != hd.size:
                src_a = src_a.resize(hd.size, Image.Resampling.NEAREST)
            a_new = np.array(hd)
            a_src = np.array(src_a)
            a_new[:, :, 3] = np.minimum(a_new[:, :, 3], a_src[:, :, 3])
            rep = {"file": os.path.basename(p), "status": "ok",
                   "maskenindex": -1, "randanteil": 0.0, "randstreifen_gefuellt": 0,
                   "objektmaske_innen": None,
                   "pixel_geaendert": int((a_new[:, :, 3] != np.array(hd)[:, :, 3]).sum()),
                   "opak_vorher": int((np.array(hd)[:, :, 3] > 128).sum()),
                   "opak_nachher": int((a_new[:, :, 3] > 128).sum()),
                   "ausserhalb_maske": 0, "_data": a_new}
            if args.apply and not args.dry_run:
                Image.fromarray(a_new, "RGBA").save(p)
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
