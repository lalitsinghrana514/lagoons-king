import json, numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
Image.MAX_IMAGE_PIXELS=None
eng = RapidOCR()
im = Image.open('../lagoons-king/clusters/morocco.jpg').convert('RGB')
W,H = im.size
TILE, OV, UP = 900, 120, 2
dets=[]
ys=list(range(0,H,TILE-OV)); xs=list(range(0,W,TILE-OV))
n=0
for ty in ys:
    for tx in xs:
        crop = im.crop((tx,ty,min(tx+TILE,W),min(ty+TILE,H)))
        crop = crop.resize((crop.width*UP, crop.height*UP), Image.LANCZOS)
        res,_ = eng(np.array(crop))
        n+=1
        if res:
            for poly,text,conf in res:
                cx = tx + sum(p[0] for p in poly)/4/UP
                cy = ty + sum(p[1] for p in poly)/4/UP
                dets.append((cx,cy,text,float(conf)))
    print(n, len(dets), flush=True)
json.dump(dets, open('moc_ocr_raw.json','w'))
print("done", len(dets))
