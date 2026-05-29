from PIL import Image, ImageFilter
import os

src = "assets/extracted/COMI/IMAGES/backgrounds/0015_town.png"
out = "assets/demo"
os.makedirs(out, exist_ok=True)

im = Image.open(src)
w, h = im.size
print(f"Original: {w}x{h}")

im.save(os.path.join(out, "original.png"))

im_4x = im.resize((w * 4, h * 4), Image.LANCZOS)
im_4x.save(os.path.join(out, "upscaled_4x.png"))
print(f"4x upscaled: {w*4}x{h*4}")

im_down = im_4x.resize((w, h), Image.LANCZOS)
if im_down.mode == "P":
    im_down = im_down.convert("RGB")
im_sharp = im_down.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=3))
im_sharp.save(os.path.join(out, "enhanced.png"))

for f in sorted(os.listdir(out)):
    fp = os.path.join(out, f)
    print(f"  {f}: {os.path.getsize(fp)//1024}KB")
