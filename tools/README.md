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
7. **Gap-fill — the step that actually matters most, read this twice.**
   These site plans are laid out as a *snake of short straight columns*
   (typically 7–24 units each), turning ~90° at every column boundary.
   That structure repeats for literally every prefix, including ones
   that look like one long diagonal at a glance (E, F) — they're just a
   tilted version of the same snake-of-columns, not one continuous run.

   **The trap:** two OCR-confirmed points that are numerically close
   (even a single missing unit in between, gap=2) can still sit on
   *different* physical columns, if the missing unit happens to be
   exactly the one at the column's corner. A plain "bracket the gap
   between its nearest confirmed neighbors and interpolate" will silently
   draw a straight line across the gap between two unrelated columns —
   this produced real, visible bugs in the first pass of this cluster
   (a 22-unit streak cutting across three rows of buildings; several
   single-unit dots landing in the street). **Do not exempt small gaps
   from the direction check.** A gap of 1 is just as capable of
   straddling a column corner as a gap of 8.

   The fix, built as `ocr_runs_v2` in the Santorini session (not checked
   in as a standalone script — rebuild it the same way for the next
   cluster): walk each prefix's OCR-confirmed points in number order,
   growing a "run" one point at a time. Before appending a new point to
   the current run, compare the direction from the run's last two points
   to the direction from (last point → new point); if the turn exceeds
   ~35°, the new point starts a fresh run instead. This has to run on
   *every* addition regardless of how small the number-gap is — do not
   pre-merge close-together points before checking direction, that's
   exactly what let the small-gap bugs through the first time.

   Once you have clean runs: gaps strictly *inside* one run interpolate
   safely between its confirmed points. Gaps *between* two different
   runs are genuinely ambiguous — do not guess which run "owns" the gap
   by numeric midpoint or by which run is closer. In this pass roughly
   half of these went to the earlier run, half to the later one, and
   one even went to the earlier run when the later run was numerically
   closer — there is no reliable shortcut. **Crop-and-view every one of
   these by hand** (that's what `crop.py` is for) and extrapolate from
   whichever side the label positions actually confirm.
8. **Final visual QA — layer these three checks, not just one:**
   - Overlay all final dot positions on the clean map render and
     eyeball the full image, then zoom into ≥4 spread-out regions.
   - A **neighbor-distance ratio check**: for every non-OCR unit,
     distance to its nearest *directly-confirmed* same-prefix neighbor
     (n±1), divided by that prefix's median same-prefix per-unit step.
     Flag anything > ~1.5–1.8×. This is what actually caught the
     mis-bracketed small gaps (e.g. one flagged unit sitting 2.7x the
     normal per-unit distance from its neighbor, at the tail of a
     wrongly-bridged run) — the building-color check alone missed
     several of these because the wrong position still happened to
     land inside *some* building, just not its own.
   - A **building-color proximity check**: sample pixel colors in a
     radius around each dot, flag any with no saturated
     (non-gray/green/blue) color nearby. Useful, but note it has a
     real false-negative rate on this map style (a wrong position can
     land inside a *neighboring* building and pass) — it's a
     complement to the distance check, not a replacement. Also don't
     tighten the radius too far chasing zero flags: at radius=3px even
     a directly OCR-confirmed, visually-verified-correct unit failed
     it (anti-aliased edges / off-center-but-still-on-roof placement)
     — that's noise, not signal. Radius ~15-18px was the useful range
     here.
   - Every unit either check flags gets an individual crop-and-view,
     not a second heuristic. Re-run both checks after each fix — fixing
     one mis-bracketed run can occasionally reveal another (the
     generic "nearest run by number" fallback silently overwrote a
     couple of already-hand-verified fixes in this session; the lesson
     was to apply hand-verified overrides *last*, on top of whatever
     the automated pass produces, and re-check after, not before).

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
