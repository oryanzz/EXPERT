"""Probe: print what OCR sees in the bottom status-bar strip of a screenshot."""
import sys

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
for path in sys.argv[1:]:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    boxes, _ = engine(np.array(img.crop((0, h - 80, w, h))), use_cls=False)
    print(path[-32:])
    for box, text, conf in sorted(boxes or [], key=lambda b: min(p[0] for p in b[0])):
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        print(f"  x={min(xs):5.0f}-{max(xs):5.0f} y={min(ys) + h - 80:5.0f}-{max(ys) + h - 80:5.0f} conf={conf:.2f} {text!r}")
