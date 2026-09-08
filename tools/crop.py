import fitz, sys
from PIL import Image, ImageDraw

PDF = "/Users/lalitsinghrana/Desktop/DAMAC LAGOONS/Santorini  cluster plan copy.pdf"
PAGE_W, PAGE_H = 1190.550048828125, 841.8900146484375

def crop_pct_grid(x0pct, y0pct, x1pct, y1pct, out_path, zoom=10, step=1.0, grid=True):
    doc = fitz.open(PDF)
    p = doc[0]
    rect = fitz.Rect(x0pct/100*PAGE_W, y0pct/100*PAGE_H, x1pct/100*PAGE_W, y1pct/100*PAGE_H)
    mat = fitz.Matrix(zoom, zoom)
    pix = p.get_pixmap(matrix=mat, clip=rect)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if grid:
        draw = ImageDraw.Draw(img)
        x = x0pct
        while x <= x1pct + 1e-9:
            px = (x - x0pct) / (x1pct - x0pct) * pix.width
            draw.line([(px,0),(px,pix.height)], fill=(0,120,255), width=1)
            draw.text((px+3, 3), f"{x:.1f}", fill=(0,120,255))
            x += step
        y = y0pct
        while y <= y1pct + 1e-9:
            py = (y - y0pct) / (y1pct - y0pct) * pix.height
            draw.line([(0,py),(pix.width,py)], fill=(255,0,180), width=1)
            draw.text((3, py+2), f"{y:.1f}", fill=(255,0,180))
            y += step
    img.save(out_path)
    print(out_path, img.size)

if __name__ == "__main__":
    x0,y0,x1,y1,out = sys.argv[1:6]
    zoom = float(sys.argv[6]) if len(sys.argv) > 6 else 10
    step = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
    grid = sys.argv[8] != "0" if len(sys.argv) > 8 else True
    crop_pct_grid(float(x0), float(y0), float(x1), float(y1), out, zoom, step, grid)
