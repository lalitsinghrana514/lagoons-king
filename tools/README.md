# Cluster position-extraction pipeline (OCR-based)

Used to derive `clusters/<name>_units.json` positions from a dedicated
per-cluster site-plan PDF. Reference implementation from the Santorini
pass — reuse the pattern for each new cluster PDF rather than
re-deriving it from scratch.

Requires `rapidocr-onnxruntime` (`pip install --user rapidocr-onnxruntime`,
no system tesseract/brew needed) plus `pymupdf`, `Pillow`, `numpy`.

## Steps

1. **Render the PDF at high res for OCR.** `fitz.Matrix(7,7)` off a
   single-page cluster plan gave clean digit shapes (~8300px wide from
   a 1190pt-wide page). Save as `ocr_source.png`.
2. **`ocr_pipeline.py`** — tiles the render (1400px tiles, 150px
   overlap so no label straddles a tile boundary undetected), runs
   RapidOCR per tile, collects `(cx, cy, text, conf)` in *global* pixel
   coords, dumps to `ocr_raw.json`. At 7x zoom RapidOCR reads full
   labels including the prefix letter (e.g. `"B211"`) with high
   confidence — no need for OpenCV connected-component digit isolation
   first, unlike a lower-res or noisier source.
3. **Build `prefix_regions.json`** — a rough bounding box per prefix,
   from whatever positions you already trust (manual reads, a prior
   pass, etc). Used only to disambiguate when OCR drops or misreads
   the leading letter (very common: `B`→`3`/`8`, `D`→`0`, `G`→`6`/`9`).
4. **`parse_ocr.py`** — regexes each detection into
   `(prefix, number, x_pct, y_pct)`:
   - `[A-H]\d{3}` direct match, validated against the real unit list
     (`units.json`) and the prefix's region.
   - `\d\d{3}` or `\d{3}` (letter dropped/misread as a digit) —
     resolved by finding which prefix's region+valid-number-range the
     point uniquely satisfies. Ambiguous ones go to `unresolved.json`,
     not guessed.
5. **Dedupe** multiple detections of the same unit (tile overlap) by
   averaging when they agree closely, else keep the higher-confidence
   one — log disagreements, don't silently pick.
6. **Outlier check** (neighbor-distance, same idea as the playbook):
   for each confirmed unit, distance to its nearest same-prefix
   numeric neighbor (±1, ±2, ±3) should be small. On the Santorini
   pass this came back with **zero** outliers — a good sign the OCR
   layer is clean; re-run this after any future cluster's OCR pass
   before trusting it.
7. **Gap-fill** whatever OCR didn't confirm (~7% of units on
   Santorini) via linear interpolation between the *nearest
   OCR-confirmed* same-prefix neighbors — not the older manual/coarse
   block estimates, which are visibly less precise even when
   "close enough".
8. **Final visual QA**: overlay all final dot positions on the clean
   map render, eyeball the full image, then also run a mechanical
   check — sample pixel colors in a small radius around each dot and
   flag any with no saturated (non-gray/green/blue) "building" color
   nearby. On Santorini this caught the last few units missed by the
   neighbor-distance check (interpolation across a bend can still land
   in a gap between buildings even with clean anchors on both ends).

## Files

- `crop.py` — percent-of-page cropping helper (optionally with a
  labeled coordinate grid burned in) for **manual** spot-checks and
  filling any prefix a pass like this leaves ambiguous. Still useful
  even in an OCR-first workflow.
- `ocr_pipeline.py` — tiled OCR pass, writes `ocr_raw.json`.
- `parse_ocr.py` — parses + resolves prefix/number, writes
  `candidates.json` / `unresolved.json`. Needs `prefix_regions.json`
  and `units.json` alongside it (paths are hardcoded per-cluster right
  now — update `SRC`/paths at the top for a new cluster rather than
  trying to make this fully generic on the first reuse).
