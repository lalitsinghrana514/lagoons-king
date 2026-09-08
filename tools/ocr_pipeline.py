import json, re, math
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

SRC = "ocr_source.png"
TILE = 1400
OVERLAP = 150

def run_tiled_ocr():
    engine = RapidOCR()
    im = Image.open(SRC).convert("RGB")
    W, H = im.size
    print("source size", W, H)
    detections = []  # (cx, cy, text, conf)
    ys = list(range(0, H, TILE - OVERLAP))
    xs = list(range(0, W, TILE - OVERLAP))
    total = len(xs) * len(ys)
    done = 0
    for ty in ys:
        for tx in xs:
            box = (tx, ty, min(tx+TILE, W), min(ty+TILE, H))
            crop = im.crop(box)
            arr = np.array(crop)
            result, _ = engine(arr)
            done += 1
            if result:
                for r in result:
                    poly, text, conf = r
                    cx = tx + sum(p[0] for p in poly)/4
                    cy = ty + sum(p[1] for p in poly)/4
                    detections.append((cx, cy, text, conf))
            if done % 10 == 0:
                print(f"{done}/{total} tiles, {len(detections)} detections so far")
    json.dump(detections, open("ocr_raw.json","w"))
    print("saved", len(detections), "raw detections")

if __name__ == "__main__":
    run_tiled_ocr()
