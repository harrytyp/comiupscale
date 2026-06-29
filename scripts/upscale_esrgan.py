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
print("Loading RealESRGAN x4plus_anime_6B...")
model = RRDBNet(num_in_ch=3, num_out_ch=3, scale=4, num_feat=64, num_block=6, num_grow_ch=32)
state = torch.load('/tmp/RealESRGAN_x4plus_anime_6B.pth', map_location='cpu', weights_only=True)
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


def upscale_image(input_path, output_path):
    """Upscale a PNG image 4x with vector-contour alpha smoothing."""
    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)

    if img.shape[2] == 4:
        rgb = img[:, :, :3]
        alpha = img[:, :, 3]
    else:
        rgb = img
        alpha = np.full((img.shape[0], img.shape[1]), 255, dtype=np.uint8)

    h, w = rgb.shape[:2]

    # Step 1: Upscale RGB with RealESRGAN (no border fill — keeps textures sharp)
    rgb_up = rgb[:, :, ::-1].copy()  # BGR → RGB
    rgb_t = torch.from_numpy(rgb_up.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        out = model(rgb_t).squeeze(0).clamp(0, 1)
    out_np = (out.numpy().transpose(1, 2, 0) * 255).astype(np.uint8)

    # Step 2: Vector-contour alpha with Chaikin smoothing + inner holes
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
