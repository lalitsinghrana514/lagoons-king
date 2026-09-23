#!/usr/bin/env python3
"""Re-derive positions for every unit whose current x/y is a product of the
old "snap to nearer anchor" fallback (identifiable because that fallback
produces IDENTICAL coordinates for every unit in a run that snapped to the
same anchor -- a real OCR read never coincides pixel-for-pixel with another).

Treats every UNIQUELY-positioned unit in a prefix as a trustworthy anchor
(these are the direct OCR reads -- collisions only ever come from the old
fallback) and re-derives every colliding unit's position using a direction-
consistency-checked multi-point fit per prefix, so a gap that straddles a
90-degree column turn is recognised and handled properly instead of being
bridged with a straight line or collapsed onto one anchor.

Usage: fix_gapfill.py <clusters/<name>_units.json> [--write]
Without --write, only prints a before/after audit; add --write to save.
"""
import json, re, sys, math
import numpy as np
from collections import defaultdict

def prefix_number(v):
    m = re.match(r'^([A-Z]+)(\d+)$', v)
    return (m.group(1), int(m.group(2))) if m else (None, None)


def fit_line(pts):
    idx = np.array([p[0] for p in pts], dtype=float)
    xs = np.array([p[1] for p in pts], dtype=float)
    ys = np.array([p[2] for p in pts], dtype=float)
    A = np.vstack([idx, np.ones_like(idx)]).T
    mx, cx = np.linalg.lstsq(A, xs, rcond=None)[0]
    my, cy = np.linalg.lstsq(A, ys, rcond=None)[0]
    return (mx, cx, my, cy)


def own_direction(conf, ckset, anchor, direction, reach=6):
    step = -direction
    v = anchor + step
    steps = 0
    while steps < reach:
        if v in ckset:
            dx = conf[anchor][0] - conf[v][0]
            dy = conf[anchor][1] - conf[v][1]
            d = math.hypot(dx, dy)
            return (dx / d, dy / d) if d > 1e-9 else None
        v += step
        steps += 1
    return None


def gather_side(conf, ckset, anchor, direction, window=20, need=5):
    ref_dir = own_direction(conf, ckset, anchor, direction)
    pts = [(anchor, conf[anchor][0], conf[anchor][1])]
    v = anchor
    steps = 0
    while len(pts) < need and steps < window:
        v += direction
        steps += 1
        if v not in ckset:
            continue
        cand = (v, conf[v][0], conf[v][1])
        p1 = pts[-1]
        cx_, cy_ = cand[1] - p1[1], cand[2] - p1[2]
        cd = math.hypot(cx_, cy_)
        if len(pts) == 1 and ref_dir is not None and cd > 1e-6:
            cos = (cx_ * ref_dir[0] + cy_ * ref_dir[1]) / cd
            if cos < 0.5:
                break
        if len(pts) >= 2:
            p0 = pts[-2]
            hx, hy = p1[1] - p0[1], p1[2] - p0[2]
            hd = math.hypot(hx, hy)
            if hd > 1e-6 and cd > 1e-6:
                cos = (hx * cx_ + hy * cy_) / (hd * cd)
                if cos < 0.82:
                    break
        pts.append(cand)
    return pts


def fill_prefix(conf, nmax):
    """conf: {num: (x,y)} of TRUSTED anchors for one prefix. Returns
    {num: (x,y)} for every num in 1..nmax (only called with the actual
    valid-number set by the caller, this just needs an iterable)."""
    ck = sorted(conf)
    ckset = set(ck)
    if not ck:
        return {}

    gdiffs = []
    for i in range(len(ck) - 1):
        a, b = ck[i], ck[i + 1]
        if b - a == 1:
            gdiffs.append(math.hypot(conf[b][0] - conf[a][0], conf[b][1] - conf[a][1]))
    gdiffs.sort()
    g_step = gdiffs[len(gdiffs) // 2] if gdiffs else 1.0

    out = {u: conf[u] for u in conf}

    def eval_at(line, idx):
        mx, cx, my, cy = line
        return (mx * idx + cx, my * idx + cy)

    i = 0
    while i < len(ck) - 1:
        lo, hi = ck[i], ck[i + 1]
        i += 1
        if hi - lo <= 1:
            continue
        missing = list(range(lo + 1, hi))
        gap_dist = math.hypot(conf[hi][0] - conf[lo][0], conf[hi][1] - conf[lo][1])
        expected = g_step * (hi - lo)
        # a straight chord between the two real anchors is always bounded
        # (can never shoot off-canvas); use it as the fallback ceiling for
        # any line-extrapolated candidate that strays implausibly far --
        # a 2-3 point local fit's slope error compounds fast over a long
        # gap, and a wrong-but-plausible position beats a wrong-and-absurd one
        chord_cap = max(gap_dist, expected) * 1.6

        def chord(v):
            t = (v - lo) / (hi - lo)
            return (conf[lo][0] + t * (conf[hi][0] - conf[lo][0]),
                    conf[lo][1] + t * (conf[hi][1] - conf[lo][1]))

        def place(v, candidate):
            nearer = conf[lo] if (v - lo) <= (hi - v) else conf[hi]
            if math.hypot(candidate[0] - nearer[0], candidate[1] - nearer[1]) > chord_cap:
                return chord(v)
            return candidate

        lo_pts = gather_side(conf, ckset, lo, -1)
        hi_pts = gather_side(conf, ckset, hi, +1)
        lo_line = fit_line(lo_pts) if len(lo_pts) >= 2 else None
        hi_line = fit_line(hi_pts) if len(hi_pts) >= 2 else None

        if hi - lo > 15 and not (lo_line and hi_line):
            # this sparse a gap (>15 missing numbers between the nearest real
            # anchors) has too little nearby evidence for a direction fit on
            # AT LEAST one side -- these are exactly the low-confidence zones
            # the source docs call out (e.g. Nice's M-prefix). A plain
            # bounded chord between the two real points is the most
            # defensible fallback absent better data. But when BOTH sides
            # have enough nearby confirmed points to fit a real local
            # direction, don't throw that away just because the gap is wide
            # -- the split-by-nearer-side logic below (each half hugging its
            # own side's real heading) is strictly more informed than a
            # blind chord, and a wide gap is exactly where a blind chord is
            # most likely to compress dozens of units into a meaningless
            # sliver (confirmed on Nice's L406-480 and L513-539 runs: the
            # two bounding anchors were pixel-close by coincidence despite
            # being on unrelated legs of the serpentine, and a 74- and
            # 26-unit run collapsed to ~3-5px/step instead of the ~40-80px/
            # step every neighbouring run on the same prefix actually used).
            for v in missing:
                out[v] = chord(v)
            continue

        def unit_dir(line):
            mx, cx, my, cy = line
            d = math.hypot(mx, my)
            return (mx / d, my / d) if d > 1e-9 else None

        lo_dir = unit_dir(lo_line) if lo_line else None
        hi_dir = unit_dir(hi_line) if hi_line else None
        same_row = None
        if lo_dir and hi_dir:
            same_row = bool((lo_dir[0] * hi_dir[0] + lo_dir[1] * hi_dir[1]) >= -0.6)

        if gap_dist <= expected * 1.35 and (same_row is not False):
            for v in missing:
                out[v] = chord(v)
            continue

        if same_row is False:
            mx, cx, my, cy = hi_line
            for v in missing:
                out[v] = place(v, (mx * v + cx, my * v + cy))
            continue

        lo_err = math.hypot(*[a - b for a, b in zip(eval_at(lo_line, hi), conf[hi])]) if lo_line else None
        hi_err = math.hypot(*[a - b for a, b in zip(eval_at(hi_line, lo), conf[lo])]) if hi_line else None
        use = 'lo' if (lo_err is not None and (hi_err is None or lo_err <= hi_err)) else ('hi' if hi_line else None)
        line = lo_line if use == 'lo' else hi_line if use == 'hi' else None

        if line and (lo_err if use == 'lo' else hi_err) is not None and \
           (lo_err if use == 'lo' else hi_err) < g_step * 3.0:
            mx, cx, my, cy = line
            for v in missing:
                out[v] = place(v, (mx * v + cx, my * v + cy))
        else:
            for v in missing:
                d_lo, d_hi = v - lo, hi - v
                pick = lo_line if (d_lo <= d_hi and lo_line) else (hi_line if hi_line else lo_line)
                if pick:
                    mx, cx, my, cy = pick
                    out[v] = place(v, (mx * v + cx, my * v + cy))
                else:
                    out[v] = chord(v)

    first, last = ck[0], ck[-1]

    # extrapolate for numbers below the first / above the last confirmed
    # anchor, using that end's own established local direction
    lo_pts = gather_side(conf, ckset, first, -1)
    lo_line = fit_line(lo_pts) if len(lo_pts) >= 2 else None
    hi_pts = gather_side(conf, ckset, last, +1)
    hi_line = fit_line(hi_pts) if len(hi_pts) >= 2 else None

    def extrap(line, v):
        mx, cx, my, cy = line
        return (mx * v + cx, my * v + cy)

    return out, first, last, lo_line, hi_line


def run(path, write):
    d = json.load(open(path))
    by_prefix = defaultdict(dict)  # prefix -> {num: villa_key}
    for k in d:
        p, n = prefix_number(k)
        if p is None:
            continue
        by_prefix[p][n] = k

    # find collision groups on CURRENT data
    by_xy = defaultdict(list)
    for k, u in d.items():
        by_xy[(round(u['x'], 3), round(u['y'], 3))].append(k)
    collided_keys = set()
    for xy, ks in by_xy.items():
        if len(ks) > 1:
            collided_keys.update(ks)

    print(f"{path}: {len(d)} units, {len(collided_keys)} currently on a collided coordinate")

    fixed = 0
    still_bad = []
    for p, nummap in by_prefix.items():
        conf = {}
        for n, k in nummap.items():
            if k not in collided_keys:
                conf[n] = (d[k]['x'], d[k]['y'])
        if not conf:
            still_bad.extend(nummap.values())
            continue
        result = fill_prefix(conf, max(nummap))
        out, first, last, lo_line, hi_line = result
        EXTRAP_STEP_CAP = 8  # a 2-3 point local fit's slope error compounds
        # too fast to trust much further out than this; beyond it, holding
        # at the real anchor is safer than a runaway straight-line guess
        for n, k in nummap.items():
            if n not in out:
                if n < first and lo_line and (first - n) <= EXTRAP_STEP_CAP:
                    mx, cx, my, cy = lo_line
                    out[n] = (mx * n + cx, my * n + cy)
                elif n > last and hi_line and (n - last) <= EXTRAP_STEP_CAP:
                    mx, cx, my, cy = hi_line
                    out[n] = (mx * n + cx, my * n + cy)
                elif n < first:
                    out[n] = conf[first]
                elif n > last:
                    out[n] = conf[last]
            if k in collided_keys:
                if n in out:
                    x, y = out[n]
                    # absolute last-resort safety net: never write a position
                    # off the image regardless of how it was derived
                    x = min(max(x, 0.0), 100.0)
                    y = min(max(y, 0.0), 100.0)
                    d[k]['x'], d[k]['y'] = round(x, 3), round(y, 3)
                    fixed += 1
                else:
                    still_bad.append(k)

    # re-check collisions after fix
    by_xy2 = defaultdict(list)
    for k, u in d.items():
        by_xy2[(round(u['x'], 3), round(u['y'], 3))].append(k)
    remaining = sum(len(ks) for ks in by_xy2.values() if len(ks) > 1)
    print(f"  re-derived {fixed} units; {remaining} units still on a collided coordinate after fix"
          f" (no confirmed same-prefix anchor at all: {len(still_bad)})")

    if write:
        json.dump(d, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
        print("  wrote", path)
    return remaining, still_bad


if __name__ == '__main__':
    write = '--write' in sys.argv
    paths = [a for a in sys.argv[1:] if a != '--write']
    for p in paths:
        run(p, write)
