"""Draw the EXPERT stopwatch (same geometry as the SVG in ui/index.html) as a Windows .ico.

Pillow draws outlines inward from a shape's box while SVG centres strokes on the path, so
every stroked shape here is an outer shape in the stroke colour with the inner one on top.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

K = 8  # draw the 64-unit viewBox at 512px, then downsample for smooth edges
BROWN, GOLD, ORANGE, FACE, RIM = "#4a2306", "#ffd34d", "#f58a1f", "#fff8e1", "#c98a2a"
ARC_FROM, ARC_TO = (0xfb, 0xff, 0x9a), (0x8c, 0xc2, 0x1c)  # EXP-bar yellow -> green

img = Image.new("RGBA", (64 * K, 64 * K), (0, 0, 0, 0))
d = ImageDraw.Draw(img)


def disc(cx, cy, r, color):
    d.ellipse((K * (cx - r), K * (cy - r), K * (cx + r), K * (cy + r)), fill=color)


def stroked_circle(cx, cy, r, stroke_w, stroke, fill):
    disc(cx, cy, r + stroke_w / 2, stroke)
    disc(cx, cy, r - stroke_w / 2, fill)


def stroked_round_rect(x0, y0, x1, y1, radius, stroke_w, stroke, fill):
    h = stroke_w / 2
    d.rounded_rectangle([K * (x0 - h), K * (y0 - h), K * (x1 + h), K * (y1 + h)], radius=K * (radius + h), fill=stroke)
    d.rounded_rectangle([K * (x0 + h), K * (y0 + h), K * (x1 - h), K * (y1 - h)], radius=K * max(radius - h, 0), fill=fill)


def rotated_rect(cx, cy, hw, hh, deg, color):
    a = math.radians(deg)
    pts = [(K * (cx + x * math.cos(a) - y * math.sin(a)), K * (cy + x * math.sin(a) + y * math.cos(a)))
           for x, y in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
    d.polygon(pts, fill=color)


def arc(cx, cy, r, w, start, end, color):
    """Stroke of width w centred on radius r (Pillow's arc width grows inward from the box)."""
    R = r + w / 2
    d.arc((K * (cx - R), K * (cy - R), K * (cx + R), K * (cy + R)), start, end, fill=color, width=round(K * w))


def point_on(cx, cy, r, deg):
    t = math.radians(deg)
    return cx + r * math.cos(t), cy + r * math.sin(t)


# crown, stem, side button
stroked_round_rect(25, 2.5, 39, 10.5, 3, 3.5, BROWN, ORANGE)
d.rectangle([K * 29, K * 9, K * 35, K * 15], fill=BROWN)
rotated_rect(50.5, 14.5, 4.5 + 1.75, 3.5 + 1.75, 45, BROWN)
rotated_rect(50.5, 14.5, 4.5 - 1.75, 3.5 - 1.75, 45, ORANGE)

# body and face
stroked_circle(32, 37, 24, 4.5, BROWN, GOLD)
stroked_circle(32, 37, 18.5, 1.5, RIM, FACE)

# EXP progress arc: 70% of the dial from 12 o'clock - brown casing, then a yellow->green fill
r, sweep = 13, 360 * 57.2 / (2 * math.pi * 13)
start, end = -90, -90 + sweep
arc(32, 37, r, 8.5, start, end, BROWN)
for deg in (start, end):
    disc(*point_on(32, 37, r, deg), 4.25, BROWN)
steps = 60
for i in range(steps):
    f = i / (steps - 1)
    color = tuple(round(a + (b - a) * f) for a, b in zip(ARC_FROM, ARC_TO))
    s = start + sweep * i / steps
    arc(32, 37, r, 5, s, s + sweep / steps + 0.8, color)
disc(*point_on(32, 37, r, start), 2.5, ARC_FROM)
disc(*point_on(32, 37, r, end), 2.5, ARC_TO)

# hand + hub
d.line([K * 32, K * 37, K * 21.6, K * 44.6], fill=BROWN, width=round(K * 3.5))
disc(21.6, 44.6, 1.75, BROWN)
disc(32, 37, 3.6, BROWN)

out = Path(__file__).resolve().parent.parent / "ui" / "icon.ico"
small = img.resize((256, 256), Image.LANCZOS)
small.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
small.save(out.with_suffix(".png"))
print("wrote", out)
