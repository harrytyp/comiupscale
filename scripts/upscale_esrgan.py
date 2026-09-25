#!/usr/bin/env python3
"""
RealESRGAN x4plus_anime_6B — standalone, no basicsr dependency.
Alpha handling: Chaikin vector contour smoothing with inner holes.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ResidualDenseBlock(nn.Module):
    def __init__(self, num_feat=64, num_grow_ch=32):
        super().__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, num_feat, num_grow_ch=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x):
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, num_in_ch=3, num_out_ch=3, scale=4, num_feat=64, num_block=6, num_grow_ch=32):
        super().__init__()
        self.scale = scale
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        out = self.conv_last(self.lrelu(self.conv_hr(feat)))
        return out


# ── Load model ──
# Der Modellpfad lag frueher in /tmp und war damit nicht reproduzierbar: nach einem Neustart war
# er weg, und aus den fertigen PNGs laesst sich nicht ablesen, womit sie erzeugt wurden. Jetzt
# kommt der Pfad aus dem Projekt, und jeder Lauf schreibt Herkunft und Hash in ein Manifest.
MODELS_DIR = os.environ.get("COMI_MODELS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models"))
MODEL_NAME = os.environ.get("COMI_UPSCALE_MODEL", "RealESRGAN_x4plus_anime_6B")
MODEL_PATH = os.environ.get("COMI_MODEL_PATH", os.path.join(MODELS_DIR, MODEL_NAME + ".pth"))
if not os.path.isfile(MODEL_PATH):
    raise SystemExit(
        "Modell nicht gefunden: %s\n"
        "Erwartet wird die Gewichtsdatei des dokumentierten Modells (%s).\n"
        "Download: https://github.com/xinntao/Real-ESRGAN/releases  (Ordner models/ im Projekt)\n"
        "Alternativ COMI_MODEL_PATH setzen." % (MODEL_PATH, MODEL_NAME))
print("Loading RealESRGAN %s from %s" % (MODEL_NAME, MODEL_PATH))
model = RRDBNet(num_in_ch=3, num_out_ch=3, scale=4, num_feat=64, num_block=6, num_grow_ch=32)
state = torch.load(MODEL_PATH, map_location='cpu', weights_only=True)
if 'params_ema' in state:
    state = state['params_ema']
elif 'params' in state:
    state = state['params']
state = {k.replace('module.', ''): v for k, v in state.items()}
state = {k.replace('trunk.', 'body.'): v for k, v in state.items()}
for old, new in {'conv_trunk': 'conv_body', 'trunk_conv': 'conv_body',
                  'conv_up1': 'conv_up1', 'conv_up2': 'conv_up2',
                  'conv_hr': 'conv_hr', 'conv_last': 'conv_last',
                  'final_conv': 'conv_last'}.items():
    state = {k.replace(old, new, 1) if old in k else k: v for k, v in state.items()}
model.load_state_dict(state, strict=True)
model.eval()
print(f"Model loaded! {sum(p.numel() for p in model.parameters())/1e6:.1f}M params")


def chaikin_smooth(pts, iterations=3):
    """Chaikin corner cutting: each iteration doubles points and smooths corners."""
    for _ in range(iterations):
        new_pts = []
        n = len(pts)
        for i in range(n):
            p1, p2 = pts[i], pts[(i + 1) % n]
            new_pts.append(0.25 * p1 + 0.75 * p2)
            new_pts.append(0.75 * p1 + 0.25 * p2)
        pts = np.array(new_pts)
    return pts


def read_with_mask(input_path, forced_mask_index=None):
    """Bild plus Alpha lesen. Die Maske steht als tRNS im Paletten-PNG; cv2 liefert sie als
    vierten Kanal, PIL nur ueber den Palettenindex. Beide Wege werden unterstuetzt, damit die
    Stufe unabhaengig davon funktioniert, welcher Leser die Transparenz durchreicht."""
    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise SystemExit("cannot read " + input_path)
    if img.ndim == 3 and img.shape[2] == 4:
        return img[:, :, :3], img[:, :, 3], True
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    # Fallback: tRNS ueber PIL lesen und den Maskenindex als Alpha setzen
    try:
        from PIL import Image as _PILImage
        pil = _PILImage.open(input_path)
        trans = pil.info.get("transparency")
        if pil.mode == "P" and trans is not None:
            idx = trans[0] if isinstance(trans, (tuple, list)) else trans
            arr = np.array(pil)
            alpha = np.where(arr == int(idx), 0, 255).astype(np.uint8)
            return img, alpha, True
    except Exception:
        pass
    # Erzwungener Index (Objektebenen: 39 ist die Leinwandmaske, ihre Palettenfarbe ist beliebig
    # und wuerde die Farbpruefung der Regel nicht bestehen).
    if forced_mask_index is not None:
        try:
            from PIL import Image as _PILf
            pilf = _PILf.open(input_path)
            if pilf.mode == "P":
                arrf = np.array(pilf)
                if (arrf == int(forced_mask_index)).any():
                    return img, np.where(arrf == int(forced_mask_index), 0, 255).astype(np.uint8), True
        except Exception as exc:
            print("erzwungener Maskenindex fehlgeschlagen:", exc)

    # Kein tRNS im Bild: Maske ueber dieselbe gemessene Regel bestimmen wie die Extraktion.
    # Damit werden alte Rohbilder (Maske nur als Palettenindex) und neue (mit tRNS) gleich
    # behandelt. Die Flaechenschwelle ist hier niedriger als bei der Raum-Mehrheit, weil einzelne
    # Motive wie der Inventarhintergrund nur rund 14 Prozent Maskenflaeche haben.
    try:
        from PIL import Image as _PIL
        from mask_detect import dominant_border_index, colour_is_mask_like
        pil = _PIL.open(input_path)
        if pil.mode == "P":
            arr = np.array(pil)
            found = dominant_border_index(arr, border_min=0.5, area_min=0.05)
            if found:
                idx = found[0]
                palette = pil.getpalette() or []
                colour = tuple(int(v) for v in palette[idx * 3:idx * 3 + 3]) if len(palette) >= idx * 3 + 3 else None
                if colour_is_mask_like(colour):
                    alpha = np.where(arr == idx, 0, 255).astype(np.uint8)
                    return img, alpha, True
    except Exception as exc:
        print("Maskenerkennung uebersprungen:", exc)
    alpha = np.full((img.shape[0], img.shape[1]), 255, dtype=np.uint8)
    return img, alpha, False


def inpaint_mask_colour(rgb, mask_binary):
    """Die Maskenfarbe vor dem Skalieren entfernen: sonst zieht der Upscaler sie als Saum ins
    Motiv hinein, genau der Magenta- und Gruensaum, der bisher von Hand nachgefuellt wurde.

    Gefuellt wird mit dem *naechsten Randpixel* des Motivs, nicht mit einem Mittelwert:
    cv2.inpaint mittelt die Nachbarschaft und erzeugt damit einen fremden hellen Saum, den der
    Upscaler anschliessend als Heiligenschein ins Motiv zieht (im Vergleich sichtbar).
    """
    holes = (mask_binary > 0)
    if not holes.any() or holes.all():
        return rgb
    dist, labels = cv2.distanceTransformWithLabels(
        (holes * 255).astype(np.uint8), cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(~holes)
    if len(ys) == 0:
        return rgb
    lookup = np.zeros(int(labels.max()) + 1, dtype=np.int64)
    lookup[labels[ys, xs]] = np.arange(len(ys))
    out = rgb.copy()
    my, mx = np.nonzero(holes)
    src = lookup[labels[my, mx]]
    out[my, mx] = rgb[ys[src], xs[src]]
    return out


def model_forward(bgr):
    """RRDBNet auf einem BGR-Bild, Ergebnis als BGR float 0..255."""
    rgb = bgr[:, :, ::-1].copy()
    t = torch.from_numpy(rgb.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        out = model(t).squeeze(0).clamp(0, 1)
    return (out.numpy().transpose(1, 2, 0) * 255)


def upscale_bgr(bgr, tile=256, overlap=32):
    """4x Skalierung, bei grossen Bildern gekachelt.

    Ein 640x472-Bild in einem Zug durch das Netz sprengt den Speicher (gemessen: der Lauf starb
    genau dort bei 3 GB freiem RAM). Kacheln mit 32 px Ueberlappung und weicher Gewichtung an den
    Raendern loesen das, ohne dass Kanten doppelt erscheinen.
    """
    h, w = bgr.shape[:2]
    if max(h, w) <= tile:
        return model_forward(bgr)
    out = np.zeros((h * 4, w * 4, 3), dtype=np.float64)
    weight = np.zeros((h * 4, w * 4, 1), dtype=np.float64)
    step = max(1, tile - overlap)
    for y0 in range(0, h, step):
        for x0 in range(0, w, step):
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            up = model_forward(bgr[y0:y1, x0:x1])
            ph, pw = up.shape[:2]
            oy, ox = y0 * 4, x0 * 4
            ov = overlap * 4
            wy = np.ones(ph); wx = np.ones(pw)
            if y0 > 0 and ov < ph:
                wy[:ov] = np.linspace(0, 1, ov)
            if y1 < h and ov < ph:
                wy[-ov:] = np.linspace(1, 0, ov)
            if x0 > 0 and ov < pw:
                wx[:ov] = np.linspace(0, 1, ov)
            if x1 < w and ov < pw:
                wx[-ov:] = np.linspace(1, 0, ov)
            wgt = (wy[:, None] * wx[None, :])[:, :, None]
            out[oy:oy + ph, ox:ox + pw] += up * wgt
            weight[oy:oy + ph, ox:ox + pw] += wgt
    return np.clip(out / np.maximum(weight, 1e-6), 0, 255)


def upscale_image(input_path, output_path, forced_mask_index=None):
    """Upscale a PNG image 4x. Maskierte Quellen bekommen eine binaere Maske, wie das Spiel sie
    fuehrt; die Maskenfarbe wird vorher aus der Nachbarschaft ergaenzt."""
    rgb, alpha, has_mask = read_with_mask(input_path, forced_mask_index)
    mask_binary = (alpha < 128).astype(np.uint8) if has_mask else np.zeros(alpha.shape, dtype=np.uint8)
    if has_mask and mask_binary.max() > 0:
        rgb = inpaint_mask_colour(rgb, mask_binary)

    h, w = rgb.shape[:2]

    # Step 1: Upscale RGB with RealESRGAN, gekachelt bei grossen Bildern
    out_np = upscale_bgr(rgb).astype(np.uint8)

    # Step 2: Alpha. Mit Maske binaer und kantentreu uebernommen (das Spiel kennt nur harte
    # Masken), ohne Maske weiterhin der weiche Vektorumriss fuer Kanten.
    if has_mask and mask_binary.max() > 0:
        # mask_binary markiert die Maske, also die *unsichtbare* Flaeche. Im Ergebnis muss sie
        # transparent sein, deshalb invertiert. Vorher stand hier mask_binary * 255, damit wurde
        # die Maskenfarbe deckend und das Motiv unsichtbar.
        alpha_4x = cv2.resize(np.where(mask_binary > 0, 0, 255).astype(np.uint8),
                              (w * 4, h * 4), interpolation=cv2.INTER_NEAREST)
        out_np[alpha_4x < 128] = 0
        result = np.dstack([out_np[:, :, ::-1], alpha_4x])
        cv2.imwrite(output_path, result)
        size_kb = os.path.getsize(output_path) // 1024
        print(f"  {os.path.basename(input_path)}: {w}x{h} -> {w*4}x{h*4} ({size_kb}KB, Maske binaer)")
        return

    mask = (alpha > 127).astype(np.uint8) * 255
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

    alpha_4x = np.zeros((h * 4, w * 4), dtype=np.uint8)
    if hierarchy is not None:
        hierarchy = hierarchy[0]
        for i, cnt in enumerate(contours):
            pts = cnt.reshape(-1, 2).astype(np.float64)
            if len(pts) < 4:
                continue
            smoothed = chaikin_smooth(pts, iterations=3)
            pts_4x = (smoothed * 4).astype(np.int32)
            # Outer contour → opaque, inner hole → transparent
            if hierarchy[i][3] == -1:
                cv2.fillPoly(alpha_4x, [pts_4x], 255)
            else:
                cv2.fillPoly(alpha_4x, [pts_4x], 0)

    # Preserve original SD transparency (fill pixels index 255)
    orig_up = cv2.resize(alpha, (alpha_4x.shape[1], alpha_4x.shape[0]),
                         interpolation=cv2.INTER_NEAREST)
    alpha_4x[orig_up < 128] = 0

    # Clean RGB in fully transparent areas (white fill pixels → black)
    out_np[alpha_4x < 128] = 0

    # Step 3: Composite (model outputs RGB, cv2 needs BGR for imwrite)
    result = np.dstack([out_np[:, :, ::-1], alpha_4x])  # RGB → BGR
    cv2.imwrite(output_path, result)

    size_kb = os.path.getsize(output_path) // 1024
    print(f"  {os.path.basename(input_path)}: {w}x{h} → {w*4}x{h*4} ({size_kb}KB)")

def model_digest(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    import argparse, json, time, glob
    ap = argparse.ArgumentParser(description="RealESRGAN 4x upscale fuer COMI HD-Texturen")
    ap.add_argument("--input", required=True, help="Ordner oder einzelne PNG-Datei")
    ap.add_argument("--output", required=True, help="Zielordner oder Zieldatei")
    ap.add_argument("--pattern", default="*.png")
    ap.add_argument("--limit", type=int, default=0, help="nur die ersten N Dateien (Testlauf)")
    ap.add_argument("--mask-index", type=int, default=None,
                    help="Maskenindex erzwingen, z.B. 39 fuer Objektebenen")
    ap.add_argument("--manifest", default=None, help="Pfad des Herkunfts-Manifests")
    args = ap.parse_args()

    if os.path.isdir(args.input):
        inputs = sorted(glob.glob(os.path.join(args.input, args.pattern)))
    else:
        inputs = [args.input]
    if args.limit:
        inputs = inputs[:args.limit]
    if not inputs:
        raise SystemExit("keine Eingabedateien in " + args.input)

    os.makedirs(args.output if os.path.isdir(args.output) or not os.path.splitext(args.output)[1] else os.path.dirname(args.output), exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    done = []
    for path in inputs:
        target = os.path.join(args.output, os.path.basename(path)) if (os.path.isdir(args.output) or not os.path.splitext(args.output)[1]) else args.output
        upscale_image(path, target, args.mask_index)
        done.append(os.path.basename(target))

    manifest_path = args.manifest or os.path.join(args.output if os.path.isdir(args.output) else os.path.dirname(args.output), "upscale_manifest.json")
    manifest = {
        "model": MODEL_NAME,
        "model_path": os.path.abspath(MODEL_PATH),
        "model_sha256": model_digest(MODEL_PATH),
        "model_params": {"num_feat": 64, "num_block": 6, "num_grow_ch": 32, "scale": 4},
        "mask_handling": "Maskenfarbe vor dem Skalieren aus der Nachbarschaft ergaenzt (cv2.inpaint), "
                         "Alpha binaer und kantentreu uebernommen; ohne Maske weicher Vektorumriss",
        "started": started,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "input": os.path.abspath(args.input),
        "files": len(done),
        "outputs": done if len(done) <= 200 else done[:200] + ["... %d weitere" % (len(done) - 200)],
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("Herkunft geschrieben: %s (%d Dateien, Modell %s)" % (manifest_path, len(done), MODEL_NAME))


if __name__ == "__main__":
    main()
