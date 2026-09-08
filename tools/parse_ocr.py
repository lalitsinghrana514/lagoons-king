import json, re, math
from collections import defaultdict

W, H = 8334, 5894
regions = json.load(open("prefix_regions.json"))
raw = json.load(open("ocr_raw.json"))

# valid unit number ranges per prefix (from units.json membership, computed separately)
units_global = json.load(open("/Users/lalitsinghrana/Desktop/LAGOONS KING/units.json"))
valid_nums = defaultdict(set)
for k in units_global:
    m = re.match(r'^([A-H])(\d+)$', k)
    if m:
        valid_nums[m.group(1)].add(int(m.group(2)))

def region_contains(p, x, y, pad=3.0):
    r = regions[p]
    return (r[0]-pad) <= x <= (r[2]+pad) and (r[1]-pad) <= y <= (r[3]+pad)

LETTER_FROM_DIGIT = {'8':'B','3':'B','0':'D','6':'G','9':'G','5':'S'}  # heuristic fallback

candidates = []  # (prefix, num, x_pct, y_pct, conf, source_text)
unresolved = []

for cx, cy, text, conf in raw:
    x_pct = cx / W * 100
    y_pct = cy / H * 100
    t = text.strip()

    m = re.match(r'^([A-H])(\d{3})$', t)
    if m:
        p, num = m.group(1), int(m.group(2))
        if num in valid_nums[p] and region_contains(p, x_pct, y_pct):
            candidates.append((p, num, x_pct, y_pct, conf, t))
            continue

    m = re.match(r'^(\d)(\d{3})$', t)
    if m:
        num = int(m.group(2))
        # figure out which prefix this belongs to: region + valid number range
        options = [p for p in regions if num in valid_nums[p] and region_contains(p, x_pct, y_pct)]
        if len(options) == 1:
            candidates.append((options[0], num, x_pct, y_pct, conf, t))
            continue
        elif len(options) > 1:
            unresolved.append((x_pct,y_pct,t,conf,options))
            continue

    m = re.match(r'^(\d{3})$', t)
    if m:
        num = int(m.group(1))
        options = [p for p in regions if num in valid_nums[p] and region_contains(p, x_pct, y_pct)]
        if len(options) == 1:
            candidates.append((options[0], num, x_pct, y_pct, conf, t))
            continue
        elif len(options) > 1:
            unresolved.append((x_pct,y_pct,t,conf,options))
            continue

    unresolved.append((x_pct,y_pct,t,conf,None))

print("resolved candidates:", len(candidates))
print("unresolved:", len(unresolved))
json.dump(candidates, open("candidates.json","w"))
json.dump(unresolved, open("unresolved.json","w"))
