import pymupdf, os, numpy as np
from PIL import Image, ImageChops
R="/Users/AKRA/Desktop/Damac lagoons/"
OUT="/private/tmp/claude-501/-Users-AKRA-visionary/41b522ce-2559-46be-b093-9a66b7fff379/scratchpad/lk/floorplans/"
CB=R+"Costa Brava/Costa_Brava_FloorPlan.pdf"; VE=R+"Venice/VENICE FLOOR PLANS.pdf"; NI=R+"Nice/NICE- DAMAC LAGOON.pdf"
SA=R+"Santorini /damac_properties-santorini_1-damac_lagoons-floor-plan-001.pdf"; MC=R+"Monte Carlo/Monte Carlo - Floor Plans (EN).pdf"
IB=R+"Ibiza/IBIZA - Digital Brochure (EN).pdf"; MB=R+"Marbella/MARBELLA Brochure EN 2.pdf"; MY=R+"Mykonos/MYKONS.pdf"
MA=R+"Malta/MALTA BROCHURE EN HT V2.pdf"; PO=R+"Portofino /PORTOFINO-Damac.pdf"; MO=R+"Morocco/LAGOONS - MOROCCO - DIGITAL BROCHURE (EN).pdf"
# cluster, type, pdf, page, box(x0,y0,x1,y1 fractions), trim
S=[
("costabrava","LVD-1B",CB,2,None),("costabrava","LV-3B",CB,4,None),("costabrava","LTH-5B-E",CB,6,None),
("costabrava","LTH-5B-EM",CB,8,None),("costabrava","LTH-4B-M",CB,10,None),("costabrava","LTH-3B-M",CB,12,None),
("venice","LV-1000E",VE,5,None),("venice","LV-75E",VE,8,None),("venice","LV-55E",VE,11,None),("venice","LVD-1E",VE,14,None),
("venice","LV-3E",VE,16,None),("venice","LV-4E",VE,18,None),
("nice","LV-3C",NI,7,(.13,.34,.835,1)),("nice","LTH-5C-E",NI,9,(.2,.1,.835,1)),("nice","LTH-5C-M",NI,11,(.2,.1,.835,1)),("nice","LTH-4C-M",NI,13,(.2,.05,.835,1)),
("santorini","LV3",SA,1,(.5,0,1,1)),("santorini","LV4",SA,2,(.5,0,1,1)),("santorini","LTH-5A-E",SA,3,(.5,0,1,1)),
("santorini","LTH-5A-M",SA,4,(.5,0,1,1)),("santorini","LTH-4A-M",SA,5,(.5,0,1,1)),("santorini","LTH-3A-M",SA,6,(.5,0,1,1)),
("montecarlo","LTH-5G-E",MC,3,None),("montecarlo","LTH-4G-M",MC,4,None),
("ibiza","LTH-5H-E",IB,30,None),("ibiza","LTH-4H-M",IB,31,None),
("marbella","LTH-5F-E",MB,25,None),("marbella","LTH-4F-M",MB,27,None),
("mykonos","LTH-5J-E",MY,17,(0,0,.5,1)),("mykonos","LTH-4J-M",MY,17,(.5,0,1,1)),
("malta","LVD-1D",MA,13,(.5,0,1,1)),("malta","LTH-5D-E",MA,14,(.5,0,1,1)),("malta","LTH-4D-M",MA,15,(.5,0,1,1)),
("portofino","BL-V75",PO,24,(.5,0,1,1)),("portofino","BL-VD1",PO,25,(.5,0,1,1)),("portofino","BL-5-E",PO,26,(.5,0,1,1)),
("portofino","BL-3-M",PO,27,(.5,0,.74,1)),("portofino","BL-4-M",PO,27,(.74,0,1,1)),
("morocco","LV-1000K",MO,21,None),("morocco","LV-75K",MO,23,None),("morocco","LV-55K",MO,25,None),
("morocco","LTH-5K-E",MO,27,(0,0,.5,1)),("morocco","LTH-5K-M",MO,27,(.5,0,1,1)),("morocco","LTH-4K-M",MO,28,(0,0,.5,1)),
]
def trim(im,thr=238,pad=30):
    a=np.array(im.convert('L')); m=a<thr
    ys,xs=np.where(m)
    if len(xs)==0: return im
    x0,x1=max(xs.min()-pad,0),min(xs.max()+pad,im.width); y0,y1=max(ys.min()-pad,0),min(ys.max()+pad,im.height)
    return im.crop((x0,y0,x1,y1))
cache={}
for c,t,f,p,box in S:
    d=cache.setdefault(f,pymupdf.open(f)); pg=d[p]
    z=min(2400/pg.rect.width/((box[2]-box[0]) if box else 1),4200/pg.rect.width)
    pix=pg.get_pixmap(matrix=pymupdf.Matrix(z,z)); im=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    if box:
        W,H=im.size; im=im.crop((int(box[0]*W),int(box[1]*H),int(box[2]*W),int(box[3]*H)))
    if c=='nice':
        a=np.array(im).astype(int); mn=a.min(2); mx=a.max(2)
        m=(mn>218)&((mx-mn)<24); a[m]=255; im=Image.fromarray(a.astype('uint8')); im=trim(im,thr=236)
    else: im=trim(im)
    if im.width>1800: im=im.resize((1800,int(im.height*1800/im.width)),Image.LANCZOS)
    os.makedirs(OUT+c,exist_ok=True); im.save(OUT+f"{c}/{t}.jpg",quality=82,optimize=True)
    print(c,t,im.size,os.path.getsize(OUT+f"{c}/{t}.jpg")//1024,'KB')
