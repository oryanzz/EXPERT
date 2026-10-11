"""Probe: what does OCR see in the minimap header (top-left) of a game screenshot?"""
import sys
import time

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

img = Image.open(sys.argv[1]).convert("RGB")
region = img.crop((0, 0, min(520, img.width), min(140, img.height)))
engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
engine(np.array(region), use_cls=False)
t = time.perf_counter()
boxes, _ = engine(np.array(region), use_cls=False)
print(f"{(time.perf_counter() - t) * 1000:.0f} ms")
for box, text, conf in boxes or []:
    xs, ys = [p[0] for p in box], [p[1] for p in box]
    print(f"  x={min(xs):4.0f}-{max(xs):4.0f} y={min(ys):4.0f}-{max(ys):4.0f} conf={conf:.2f} {text!r}")
