# DAMAC Lagoons — Owner Directory Map

Context handoff for whoever (human or Claude Code) picks this project up next.
Written after the initial build; read this before touching the code or data.

## 1. What this project is

An interactive, clickable map of the DAMAC Lagoons community (Dubai) covering
all 11 named clusters. Every villa/townhouse (6,606 units total) is plotted
at its real position on the master plan. Clicking a unit shows its owner
name(s) and phone number(s), pulled from the developer's owner-registry
spreadsheet. There's also a plain sortable/searchable list view, a per-cluster
filter, and full pan/zoom on the map.

It is a **static, dependency-free site**: one HTML file, one image, one JSON
file. No build step, no server, no framework. Open `index.html` in a browser
and it works (it does `fetch('units.json')` and `fetch('map.jpg')` via
relative paths, so it needs to be served over `http://`, not opened as a bare
`file://` — a `python3 -m http.server` or any static host is enough).

## 2. Deliverable files (must stay together in one folder)

| File | What it is | Notes |
|---|---|---|
| `index.html` | The whole app — HTML/CSS/JS, no external dependencies | Self-contained, ~25KB |
| `map.jpg` | The master plan render, resized for web | **4000 × 2829 px**, JPEG q85. This exact pixel size is hardcoded in the JS as `IMG_W`/`IMG_H` — if you ever swap in a different image, update those two constants to match its real pixel dimensions or all markers will misplace. |
| `units.json` | All unit + owner data, keyed by villa number | ~800KB, see schema below |

If you're handed this repo without those three files, ask for them — this
document alone can't regenerate the map positions (see §5).

## 3. Source data (developer-provided, not included in this repo)

Two spreadsheets were provided:

- **`LATEST_LAGOONS_2026.xlsx`** — the one actually used. Columns: `Cluster,
  PREFIX, NUMBER, VILLA NUMBER, OWNER NAME, MOBILE, EMAIL, SECONDARY MOBILE`.
  6,687 rows → 6,606 unique villas after de-duplication. This is the sole
  source of truth for owner names/phones and for which villa numbers exist.
- **`Damac_Lagoons__2025.xlsx`** — DLD (Dubai Land Department) transaction
  registry. **Deliberately not merged.** It's keyed by land parcel number
  (`LandNumber`/`LandSubNumber`/`Plot Pre Reg No`, e.g. `DL-K406`), not by
  villa number, and there's no reliable join key between the two files. Do
  not attempt to merge it in without a verified crosswalk — a wrong guess
  here means a wrong phone number attached to a wrong villa, which is worse
  than a gap.
- A master-plan **PDF** (`Damac_Lagoons_Master_Plan_copy.pdf`, single page,
  A0 size, Adobe-exported, no embedded text layer — confirmed via
  `pdftotext -bbox`, it returned nothing). This is the only source for *where*
  each unit sits; the spreadsheet has no coordinates.

If the developer sends a refreshed owner spreadsheet later, regenerating
`units.json`'s **owner data** (names/phones) is fully mechanical — see the
script in §6. Regenerating **positions** is not mechanical; see §5.

## 4. `units.json` schema

```json
{
  "BL360": {
    "v": "BL360",
    "c": "PORTOFINO",
    "x": 71.2,
    "y": 78.4,
    "o": [
      { "n": "MAHMOUD ALI",      "m": "0565729680",   "s": null, "x2": null },
      { "n": "DMITRY TRUKHACHEV","m": "79035890987",  "s": null, "x2": null }
    ]
  }
}
```

- Top-level key = villa number, exactly as it appears in the spreadsheet's
  `VILLA NUMBER` column (prefix letters + digits, e.g. `BL360`, `U119`).
- `x`, `y` = position as a **percentage of `map.jpg`'s width/height**
  (0–100, floats). To place a marker in pixels: `px = x/100 * IMG_W`,
  `py = y/100 * IMG_H`.
- `c` = normalized cluster name, one of the 11 below (sub-phases collapsed).
- `o` = array of owner records (almost always length 1; **22 units have
  length 2** — genuine joint ownership, both owners kept). Each owner has:
  - `n` — name
  - `m` — mobile
  - `s` — secondary mobile (from the spreadsheet's own `SECONDARY MOBILE`
    column)
  - `x2` — array of any *additional* numbers found on duplicate rows for the
    same owner+villa (rare; null when empty)
- No unit has an empty `o` array — every villa in the spreadsheet had at
  least an owner name.

## 5. How unit positions were derived (methodology, for reference/repair)

This was the hard part and is worth understanding before "fixing" anything.

1. Rendered the master-plan PDF at 200 DPI **with anti-aliasing disabled**
   (`pdftoppm -png -r 200 -aa no -aaVector no`) — this was the key step that
   made the colored building fills render as flat, clean color instead of
   dithered noise.
2. **OCR (Tesseract) does not work on this map's font.** Extensively tested:
   rotation correction, binarization, multiple PSM modes, isolated
   single-word crops — all failed, even on crops a human reads instantly.
   Do not re-attempt OCR as a shortcut; it was a dead end.
3. Instead, the full map was cut into ~50 overlapping 1100×1100 px tiles
   (150 px overlap, tiles skipped where empty), each with a coordinate grid
   overlay burned in. Every tile was **read visually** (not OCR'd): unit
   number ranges per visible row/column, plus the pixel coordinate of the
   first and last unit in each run.
4. Those (start-unit, end-unit, pixel-A, pixel-B) triples were expanded by
   linear interpolation along each run, then matched against the actual
   villa numbers that exist in the spreadsheet for that prefix (this is how
   gaps/skips in numbering get handled correctly — only real villa numbers
   get a marker).
5. Any spreadsheet villa not covered by a tile read got a position via
   nearest same-prefix-number interpolation, with a safety rule: if the
   pixel-distance-per-number-step between two known anchors is implausibly
   large (>~55px/step), the code snaps to the nearer anchor instead of
   drawing a straight line between them — long straight "streaks" across
   unrelated columns are exactly the failure mode this guards against.
6. Iterative visual QA: every unit plotted as a dot on the full map image,
   eyeballed cluster-by-cluster, obvious errors traced back to their source
   tile and re-read. One real mislabeling was caught and fixed this way — a
   block originally read as Portofino's `BL101–BL114` was actually
   Santorini's own `B101–B114` (confirmed against the spreadsheet's real
   B-range, 101–228).

**Known confidence gap:** even after several correction passes, parts of the
**Nice cluster's `M`-prefix zone** (a tight diagonal serpentine layout,
small font, ~600 units) still have a handful of units placed by
interpolation rather than a confident direct read, and a small number of
those may sit slightly off from their true building. Everywhere else, the
large majority of units (≈78% of all 6,606) have a directly-read position;
the rest are interpolated from confirmed same-prefix neighbors.

**If you need to fix a specific unit's position:** just edit its `x`/`y` in
`units.json` directly — no need to touch anything else. To find where it
*should* be, you'd need to go back to the master-plan PDF/image and locate
the label yourself; there's no shortcut for that part.

**If you need to re-run the tiling process from scratch** (e.g. a new phase
gets built and the map is reissued): re-render the PDF as in step 1, re-tile,
and repeat the manual reading. There is no saved script that reproduces the
manual reading step, because that step *was* a human/Claude visually reading
labels off images — the interpolation and merging steps below are the only
parts that are scripted and reusable.

## 6. Reusable data-pipeline logic (owner-merge + interpolation)

The following reproduces the **owner-data merge** exactly (fully mechanical,
safe to re-run any time the spreadsheet is refreshed), and the
**interpolation/snap** logic used to fill gaps once you have raw tile
readings in the same shape as before. Keep this if you rebuild `units.json`.

```python
# --- 1. Owner merge (fully mechanical, re-run anytime the spreadsheet updates) ---
import re, json
import openpyxl
from collections import defaultdict

wb = openpyxl.load_workbook('LATEST_LAGOONS_2026.xlsx', read_only=True, data_only=True)
ws = wb['Sheet1']
rows = list(ws.iter_rows(values_only=True))[1:]  # header: Cluster,PREFIX,NUMBER,VILLA NUMBER,OWNER NAME,MOBILE,EMAIL,SECONDARY MOBILE

def norm_cluster(c):
    c = (c or '').strip().upper()
    for base in ['NICE','SANTORINI','COSTA BRAVA','MOROCCO','MALTA']:
        if c.startswith(base): return base
    return 'MONTECARLO' if c == 'MONTE CARLO' else c

owners_by_villa = defaultdict(list)
cluster_by_villa = {}
for r in rows:
    cluster, prefix, number, villa, owner, mobile, email, sec_mobile = r[:8]
    if not villa: continue
    villa = str(villa).strip()
    if not re.match(r'^[A-Z]+\d+$', villa): continue
    cluster_by_villa[villa] = norm_cluster(cluster)
    name = str(owner).strip() if owner else None
    mob  = str(mobile).strip() if mobile else None
    sec  = str(sec_mobile).strip() if sec_mobile else None
    existing = next((o for o in owners_by_villa[villa] if o['n']==name), None)
    if existing:
        # duplicate row for same owner -> fold any extra number in, don't duplicate the owner
        if mob and mob != existing.get('m'):
            existing.setdefault('x2', []); existing['x2'].append(mob)
        if sec and sec != existing.get('s'):
            existing.setdefault('x2', []); existing['x2'].append(sec)
    else:
        owners_by_villa[villa].append({'n': name, 'm': mob, 's': sec})
# owners_by_villa now mirrors units.json's "o" field per villa; merge with
# positions (keyed the same way) to produce the final units.json.

# --- 2. Interpolation + "snap instead of streak" safety net ---
# Given `positions`: dict[(prefix:str, number:int)] -> (x_px, y_px) for every
# DIRECTLY-read unit, and `all_valid_units`: set of (prefix, number) for
# every villa that actually exists in the spreadsheet:
import math
from collections import defaultdict

MAX_PER_STEP = 55  # px per unit-number step; beyond this, snap don't interpolate

def fill_gaps(positions, all_valid_units):
    by_prefix = defaultdict(list)
    for (p, n) in all_valid_units:
        by_prefix[p].append(n)
    final = dict(positions)
    for p, nums in by_prefix.items():
        nums.sort()
        known = sorted((n, positions[(p, n)]) for n in nums if (p, n) in positions)
        if not known: continue
        for n in nums:
            if (p, n) in final: continue
            prev = max((k for k in known if k[0] < n), default=None)
            nxt  = min((k for k in known if k[0] > n), default=None)
            if prev and nxt:
                span = nxt[0] - prev[0]
                dist = math.hypot(nxt[1][0]-prev[1][0], nxt[1][1]-prev[1][1])
                if dist/span <= MAX_PER_STEP:
                    t = (n - prev[0]) / span
                    final[(p, n)] = (prev[1][0] + t*(nxt[1][0]-prev[1][0]),
                                      prev[1][1] + t*(nxt[1][1]-prev[1][1]))
                else:
                    final[(p, n)] = prev[1] if (n-prev[0]) <= (nxt[0]-n) else nxt[1]
            elif prev: final[(p, n)] = prev[1]
            elif nxt:  final[(p, n)] = nxt[1]
    return final
```

## 7. Cluster / prefix reference table

The spreadsheet splits some clusters into numbered sub-phases (e.g.
`SANTORINI 1/2/3`); the site normalizes these down to the 11 clusters shown
on the physical map legend. Villa-number prefix tells you the cluster
unambiguously — use this table for any lookup or validation logic:

| Prefix | Cluster (normalized) | Count | Number range seen |
|---|---|---|---|
| A | SANTORINI | 116 | 101–216 |
| B | SANTORINI | 128 | 101–228 |
| C | SANTORINI | 207 | 101–307 |
| D | SANTORINI | 96 | 101–196 |
| E | SANTORINI | 161 | 101–262 |
| F | SANTORINI | 126 | 101–226 |
| G | SANTORINI | 43 | 101–143 |
| H | SANTORINI | 53 | 101–153 |
| J | COSTA BRAVA | 288 | 101–645 |
| K | COSTA BRAVA | 67 | 123–571 |
| BL | PORTOFINO | 506 | 101–977 |
| L | NICE | 440 | 101–556 |
| M | NICE | 543 | 101–708 |
| P | MALTA | 230 | 100–466 |
| Q | MALTA | 407 | 103–856 |
| R | MARBELLA | 481 | 127–735 |
| S | MONTECARLO | 327 | 125–544 |
| T | IBIZA | 784 | 119–951 |
| U | MYKONOS | 519 | 119–730 |
| V | VENICE | 54 | 103–310 |
| W | VENICE | 97 | 101–313 |
| X | MOROCCO | 411 | 100–580 |
| Y | MOROCCO | 522 | 100–664 |

Note the ranges have gaps (e.g. not every number between 101 and 977 exists
for BL) — never assume a contiguous range, always check against
`units.json`'s actual keys or the spreadsheet.

Per-cluster totals (matches the site's filter-dropdown counts):
NICE 983 · MOROCCO 933 · SANTORINI 930 · IBIZA 784 · MALTA 637 · MYKONOS 519 ·
PORTOFINO 506 · MARBELLA 481 · COSTA BRAVA 355 · MONTECARLO 327 · VENICE 151.
(Total 6,606.)

## 8. Site architecture (`index.html`)

Single file, vanilla JS (IIFE, no modules/build step), inline `<style>`.
No external requests except the two `fetch()`s for `map.jpg`/`units.json`.

**Layout (top to bottom in the DOM):**
- `#topbar` — brand, `#searchBox` (+ `#searchResults` dropdown),
  `#clusterFilter` `<select>`, Map/List `.toggle-group`, `#stats` counter.
- `#main` — holds either the map or the list, plus the floating `#panel`.
  - `#mapViewport` → `#mapWorld` (the CSS-transformed pan/zoom layer) →
    `#mapImg` + `#markerLayer` (absolutely-positioned `.marker` divs, one
    per unit, positioned via inline `left`/`top` percentages).
  - `#zoomCtl` (+/reset/− buttons), `#legend` (cluster color key).
  - `#listView` — sortable `<table>`, built/re-rendered by
    `renderListRows()`.
  - `#panel` — slide-in detail panel (`.open` class toggles the `right`
    CSS property), populated by `openPanel(unit)`.

**Key JS, all inside one `(function(){ ... })()` at the bottom of the file:**
- `CLUSTER_COLORS` / `CLUSTER_ORDER` — the 11-cluster color map and legend
  order. Edit here to change cluster colors.
- `IMG_W = 4000, IMG_H = 2829` — **must match `map.jpg`'s actual pixel
  size.** Change this if you ever swap the image.
- `state` — single mutable object: pan/zoom (`scale`, `tx`, `ty`),
  `activeCluster` filter, `selectedId`, `view` ('map'|'list').
- `fitToScreen()` — computes scale/translate to fit the whole map in the
  viewport; called on load, on window resize, and on switching back to map
  view. Called three times on init (`requestAnimationFrame` + a 250ms
  timeout) to paper over a mobile layout-settling race condition — don't
  remove those without re-testing mobile.
- `zoomAt(clientX, clientY, factor)` — zoom anchored at a screen point;
  used by both wheel and +/− buttons.
- Pan: plain mousedown/mousemove/mouseup on `#mapViewport`. Touch: basic
  one-finger pan + two-finger pinch in the `touchstart`/`touchmove`
  handlers.
- `renderMarkers()` — one-time DOM build of all 6,606 `.marker` divs.
  Click handling is **delegated** on `#markerLayer` (one listener, checks
  `e.target`) rather than 6,606 individual listeners, for performance.
- `selectUnit(id, doFocus)` / `openPanel(unit)` — selection highlight +
  panel population; `focusUnit()` re-centers/zooms the map on a unit.
- Search: simple substring match on villa number (prefix match) or owner
  name (contains), capped at 40 results, rendered into `#searchResults`.
- `buildListView()` / `renderListRows()` — the list table; `listSort`
  tracks current sort column/direction; re-sorts and re-renders on header
  click or on cluster-filter change.
- `switchView('map'|'list')` — toggles the two view containers and their
  chrome (zoom controls/legend only show in map view).

**Performance note:** 6,606 real DOM elements as markers was tested and
works fine (see §9). If the unit count grows meaningfully beyond this (e.g.
several more clusters added), consider moving markers to a `<canvas>`
overlay instead of one div each — DOM node count is the first thing that
would need to change.

## 9. What's been tested

Verified with Playwright (headless Chromium) during the build:
map renders correctly at initial load, wheel-zoom works, marker click opens
the panel with correct owner(s)/phone(s) (including the 2-owner case,
`BL360`), search-then-click navigates and opens the right unit, list view
renders all columns and sorts, cluster filter correctly narrows both map dots
and list rows and updates the counter, mobile viewport (390×800) renders
without layout breakage (the apparent "gap" on mobile is correct
behavior — a landscape map fitted by width into a portrait screen naturally
leaves vertical margin).

Not yet tested: real touch devices (only simulated pinch/pan), very old
browsers, screen readers/accessibility pass.

## 10. Sensible next steps, if asked to improve this

- Tighten up the `M`-prefix (Nice) position confidence gap (§5).
- Add a lightweight "flag this unit" affordance so end users can report a
  wrong owner/position without needing dev access.
- If the owner spreadsheet gets refreshed, re-run §6 part 1 against the new
  file and re-merge with the *existing* `x`/`y` values from the current
  `units.json` (positions don't change just because owner data refreshed —
  only re-derive positions if the physical map itself changes).
- Consider an accessibility pass (keyboard navigation for markers, ARIA
  labels, focus states) if this needs to meet a compliance bar.
- If this needs to go multi-tenant/live (rather than a static snapshot),
  the natural next step is moving `units.json` behind a small API so owner
  data can be updated without re-shipping the whole file.
