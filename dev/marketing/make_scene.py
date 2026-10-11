"""Marketing scene: a real session screenshot with other players' names, chat and the
character name blurred out (coordinates are for the 1920x1200 client area)."""
from pathlib import Path

from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = ROOT / "shots" / "2026-10-11_02-30-49_end.jpg"

BLUR = [
    (338, 958, 1204, 1100),   # chat box: other players' names and messages
    (1586, 66, 1874, 172),    # party list
    (1590, 0, 1810, 30),      # name tag cut off at the top
    (1480, 228, 1640, 480),   # player shop sign + owner name
    (36, 450, 146, 492),      # other player's name tag (left)
    (24, 500, 146, 545),      # overlay icon under it
    (950, 896, 1106, 934),    # pet + character name tags
    (458, 1164, 556, 1200),   # character name in the status bar
]

img = Image.open(SRC).convert("RGB")
for box in BLUR:
    region = img.crop(box)
    img.paste(region.filter(ImageFilter.GaussianBlur(9)), box)
img.save(HERE / "scene_blurred.jpg", quality=92)
img.resize((960, 600), Image.LANCZOS).save(ROOT / "dev" / "out" / "scene_blurred_preview.png")
print("saved", HERE / "scene_blurred.jpg")
