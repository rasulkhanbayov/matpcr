"""
sem_scalebar_extractor.py
==========================
Scale-bar extractor for the NFFA-EUROPE SEM dataset (real_scale, materials
micrographs downloaded to $MATPCR_DATA_ROOT/nffa/extracted/, default
/ephemeral/matpcr/nffa/extracted/).

Real, confirmed-by-direct-inspection fact this is built around (see CLAUDE.md
section 9, "NFFA-EUROPE SEM dataset"): the scale bar is NEVER structured
metadata, only visually burned into the image, and the instrument info-bar
that carries it comes in at least 3 forms:
  1. A dominant near-white "Zeiss-style" band (red text, green marker line).
  2. A rarer band with different text/marker color (other instruments/software).
  3. NO info bar at all for some images (must be detected and SKIPPED, not
     treated as an extraction failure to retry).

This is why a fixed-template / fixed-pixel-crop extractor was explicitly
rejected in favor of the pipeline below:

  1. LOCATE the info-bar band by scanning row-wise brightness/std near the
     bottom of the image for a sustained, near-uniform band that contrasts
     with the micrograph above it (works whether the band is bright or dark,
     colored text or not -- it is a property of the BAND, not the text color).
  2. If no such band is found, mark the image UNUSABE (skip; real case, not
     a bug) -- this is what happens for images with no info bar burned in.
  3. OCR the located band (Tesseract) to read the numeric scale value + unit
     (e.g. "10 µm", "2um", "500 nm") -- regex-tolerant of OCR noise (µ/u/microns,
     nm, spacing).
  4. Independently, detect the scale-bar MARKER itself inside the band: a thin
     horizontal line segment (any color) with a well-defined pixel length --
     via row-wise run-length of non-background pixels in a colored/high-contrast
     row within the band. This gives pixel length independent of OCR.
  5. Combine: scale_value_real_units + scale_bar_pixel_length ->
     nm_per_pixel, feeding directly into sem_feature_size_consistent() from
     matpcr_metrics.py (which needs scale_bar_nm, scale_bar_px, image_px_long_edge).

Run: python3 experiments/sem_scalebar_extractor.py --sample 200
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import cv2
import numpy as np
import pytesseract

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
NFFA_ROOT = os.path.join(MATPCR_DATA_ROOT, "nffa", "extracted")

# unit -> nanometers, for normalizing whatever unit OCR reads
UNIT_TO_NM = {
    "nm": 1.0,
    "um": 1000.0,
    "µm": 1000.0,
    "mm": 1_000_000.0,
    "pm": 0.001,
}

# Tolerant of OCR noise: "microns"/"um"/"µm"/"pm" confusions, stray spaces,
# comma-as-decimal-point.
SCALE_TEXT_RE = re.compile(
    r"(\d+[.,]?\d*)\s*(nm|[uµ]m|mm|pm)\b",
    re.IGNORECASE,
)


def locate_info_bar(gray: np.ndarray, min_band_frac: float = 0.03):
    """Scan bottom 40% of the image for the instrument info-bar band.

    Key insight (found by direct row-profile inspection, see CLAUDE.md):
    the band is a near-uniform BACKGROUND (usually near-white ~254, sometimes
    near-black) that contains sparse colored/dark text. Text rows spike in
    row-std (high local contrast) while pure background rows have near-zero
    std -- so the band as a WHOLE is not low-std; individual rows alternate.
    The reliable per-row signal is instead the ROW MODE / dominant background
    level: for a background-dominated row, the most common pixel value is
    either near-255 (white bar) or a fixed dark level (black bar), and that
    dominant level is STABLE across the whole band and DIFFERENT from the
    micrograph texture above it (which has no single dominant level -- it's
    genuinely textured). So: for each row, compute the modal pixel value's
    share of that row; a background-dominated row has a high modal share
    (>40% of pixels within +-3 of the mode), a micrograph texture row does not.
    """
    h, w = gray.shape
    search_zone_start = int(h * 0.55)
    zone = gray[search_zone_start:, :]
    n = zone.shape[0]
    if n < 10:
        return None

    modal_share = np.empty(n, dtype=float)
    modal_level = np.empty(n, dtype=float)
    for i in range(n):
        row = zone[i, :]
        hist, _ = np.histogram(row, bins=64, range=(0, 255))
        peak_bin = int(np.argmax(hist))
        level = peak_bin * (255.0 / 64) + (255.0 / 128)
        share = float(np.sum(np.abs(row.astype(int) - int(level)) <= 10)) / w
        modal_share[i] = share
        modal_level[i] = level

    # A genuine info-bar row is DOMINATED by a single flat background level
    # (share > 0.65) -- text/marker pixels are always a minority of the row.
    # Micrograph texture rows, even visually "flat" ones, still have a modal
    # bin capturing well under 65% of pixels because real texture varies
    # continuously; 0.4 (tried earlier) was too permissive and caught texture.
    # Text-heavy rows within a real bar can transiently dip just under this
    # (e.g. a row that's mostly bold glyph strokes) -- tolerate gaps up to 3
    # rows so one dense text line doesn't fracture an otherwise-solid band.
    #
    # CRITICAL: background-row rows can ALSO fire on a large uniform void
    # region of the micrograph itself (e.g. black empty space around a thin
    # SEM tip) sitting directly adjacent to the real white info bar -- both
    # independently have high modal-share, just at very different levels, so
    # they must NOT be allowed to merge into one run (confirmed directly:
    # Tips/L5_005e08...jpg has a black void merging with the white bar into
    # one 346-row false run -- see CLAUDE.md changelog). Track a per-segment
    # REFERENCE level (median of the segment so far) and cut the run the
    # moment a background row's level departs from that reference by more
    # than a small tolerance, rather than only checking adjacent-row deltas
    # (which drift) or nothing at all (which merges unrelated flat zones).
    is_background_row = modal_share > 0.65

    all_runs = []
    run_start = None
    run_levels = []
    gap = 0
    max_gap = 3
    level_tol = 20

    def close_run(end):
        if run_start is not None and (end - run_start) >= 1:
            all_runs.append((run_start, end))

    for i in range(n):
        if is_background_row[i]:
            ref = np.median(run_levels) if run_levels else None
            same_level = ref is None or abs(modal_level[i] - ref) <= level_tol
            if run_start is None:
                run_start = i
                run_levels = [modal_level[i]]
            elif same_level:
                run_levels.append(modal_level[i])
            else:
                close_run(i - gap)
                run_start = i
                run_levels = [modal_level[i]]
            gap = 0
        elif run_start is not None and gap < max_gap:
            gap += 1
        else:
            close_run(i - gap)
            run_start = None
            run_levels = []
            gap = 0
    if run_start is not None:
        close_run(n - gap)

    # Among all flat/uniform segments found, pick by fit to a real info bar,
    # NOT by raw length or bottom-proximity -- a large uniform micrograph
    # void (e.g. black empty space framing a thin SEM tip) can be the LONGEST
    # flat run, and there can even be a second flat void BELOW the real bar
    # (confirmed directly on Tips/L5_005e08...jpg: length-only picked a
    # 215-row void; length+bottom-proximity picked a DIFFERENT dark strip
    # below the real 60-row white bar). A genuine info bar's defining trait
    # is that its background level is an OUTLIER relative to the typical
    # micrograph gray levels in the rest of the image (usually near-white,
    # occasionally near-black against a bright micrograph) -- score each
    # candidate by how far its level departs from the image's own median
    # gray level (outside the search zone, i.e. the actual micrograph
    # content), and prefer the strongest outlier; break ties by length.
    candidates = [r for r in all_runs if (r[1] - r[0]) >= h * min_band_frac]
    if not candidates:
        return None
    micrograph_level = float(np.median(gray[: int(h * 0.55), :]))
    best_run = max(
        candidates,
        key=lambda r: (
            abs(float(np.median(modal_level[r[0]:r[1]])) - micrograph_level),
            r[1] - r[0],
        ),
    )

    band_top = search_zone_start + best_run[0]
    band_bottom = search_zone_start + best_run[1]

    # Confirm this band's background level actually contrasts with the
    # texture directly above it (rules out a flat micrograph region, e.g. a
    # dark background particle image, being mistaken for the info bar).
    above_start = max(0, band_top - 20)
    if band_top <= above_start:
        return None
    above_mean = gray[above_start:band_top, :].mean()
    band_bg_level = float(np.median(modal_level[best_run[0]:best_run[1]]))
    if abs(band_bg_level - above_mean) < 15:
        return None

    return band_top, band_bottom


def ocr_scale_text(bar_bgr: np.ndarray):
    """OCR ONLY the left third of the info-bar crop for the scale label, and
    return the first (value_nm, raw_match_text) found, or None.

    Restricting to the left third is deliberate, not incidental: every layout
    inspected puts the scale label + marker on the left, with unrelated
    fields (WD, EHT, Mag, Stage, ...) filling the rest of the bar -- several
    of those ALSO contain a bare number + "mm" (e.g. "WD = 4 mm"), so OCR-ing
    the full bar width lets those unrelated fields falsely satisfy the regex
    (confirmed directly: a Biological sample's real "2 um" scale label was
    missed by OCR noise, but "WD = 4 mm" elsewhere in the bar matched instead
    and was silently returned as if it were the scale -- see CLAUDE.md
    changelog). Restricting the OCR crop to the left third removes that
    ambiguity structurally instead of trying to out-clever it with regex.
    """
    h, w = bar_bgr.shape[:2]
    left = bar_bgr[:, : max(1, w // 3)]
    gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)

    # NFFA text is small and low-res at native crop resolution -- a single
    # upscale/psm combo (originally 3x + psm 6) missed real labels (e.g. a
    # genuine "2 um" OCR'd as "2yum"/"24m"). Empirically, higher upscale (8x)
    # + psm 11 (sparse text, no layout assumption) resolved that specific
    # case cleanly to "2um" where 3x/psm 6 could not -- so try several
    # upscale/psm combinations, most-successful-first, instead of one config.
    for fx in (8.0, 6.0, 4.0, 3.0):
        scaled = cv2.resize(gray, None, fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for psm in (11, 6, 7):
            for candidate in (thresh, scaled):
                text = pytesseract.image_to_string(candidate, config=f"--psm {psm}")
                m = SCALE_TEXT_RE.search(text)
                if not m:
                    continue
                value = float(m.group(1).replace(",", "."))
                unit = m.group(2).lower().replace("µ", "u")
                unit_norm = "um" if unit in ("um", "µm") else unit
                nm = value * UNIT_TO_NM.get(unit_norm)
                if nm is None:
                    continue
                return nm, m.group(0)
    return None


def _longest_run(mask_1d: np.ndarray) -> int:
    best = 0
    run = 0
    for v in mask_1d:
        if v:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def find_scale_marker_pixel_length(bar_bgr: np.ndarray):
    """Detect the scale-bar marker line's pixel length inside the info-bar
    crop. The marker is a single solid horizontal line segment (colored, e.g.
    green, or dark/black depending on layout). Text glyphs in the same region
    can have a HIGHER total pixel count (summed across fragmented letters)
    but a much SHORTER longest contiguous run than the marker's one solid
    line -- so select by longest contiguous run per row, not by total count
    per row (an earlier version of this function picked the text row by
    mistake for exactly this reason -- see CLAUDE.md changelog).
    Returns pixel length (float) or None.
    """
    h, w = bar_bgr.shape[:2]
    # restrict to the left third of the band, where the marker consistently
    # appears in every layout inspected (right side holds the field readouts).
    left = bar_bgr[:, : max(1, w // 3)]
    b, g, r = left[:, :, 0].astype(int), left[:, :, 1].astype(int), left[:, :, 2].astype(int)
    # colorfulness: how far a pixel is from gray (equal R=G=B)
    colorfulness = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
    gray_left = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)

    # candidate marker pixels: either colorful (green/red marker) or strongly
    # dark/light against the background (black- or white-marker layouts).
    bg_level = np.median(gray_left)
    intensity_mask = (
        gray_left < (bg_level - 40) if bg_level > 128 else gray_left > (bg_level + 40)
    )
    color_mask = colorfulness > 60
    marker_mask = intensity_mask | color_mask

    # Exclude the crop's own top/bottom edge rows: the info-bar boundary
    # detection in locate_info_bar can include a thin dark border line right
    # at row 0 / row h-1 of this crop, which reads as a full-width "marker"
    # and swamps the real (much shorter) scale-bar line -- confirmed by
    # direct inspection (see CLAUDE.md changelog: marker_px=341 bug).
    margin = max(2, h // 15)
    usable_rows = range(margin, h - margin)

    run_lengths = np.array([_longest_run(marker_mask[i, :]) for i in usable_rows])
    if run_lengths.size == 0 or run_lengths.max() < 5:
        return None
    best_idx = int(np.argmax(run_lengths))
    # A genuine marker run should be well short of the full crop width --
    # if the "best" row is still suspiciously close to full width, it's
    # another border/edge artifact, not a real short marker line.
    if run_lengths[best_idx] > 0.8 * w:
        return None
    return float(run_lengths[best_idx])


def process_image(path: str):
    img = cv2.imread(path)
    if img is None:
        return {"path": path, "status": "unreadable"}
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    band = locate_info_bar(gray)
    if band is None:
        return {"path": path, "status": "no_info_bar", "image_w": w, "image_h": h}

    top, bottom = band
    bar = img[top:bottom, :]

    scale_result = ocr_scale_text(bar)
    marker_px = find_scale_marker_pixel_length(bar)

    if scale_result is None:
        return {
            "path": path, "status": "ocr_failed", "image_w": w, "image_h": h,
            "bar_top": top, "bar_bottom": bottom, "marker_px": marker_px,
        }
    scale_nm, raw_text = scale_result
    if marker_px is None:
        return {
            "path": path, "status": "marker_not_found", "image_w": w, "image_h": h,
            "bar_top": top, "bar_bottom": bottom, "scale_nm": scale_nm, "raw_text": raw_text,
        }

    return {
        "path": path, "status": "ok", "image_w": w, "image_h": h,
        "bar_top": top, "bar_bottom": bottom,
        "scale_nm": scale_nm, "raw_text": raw_text, "marker_px": marker_px,
        "nm_per_px": scale_nm / marker_px,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=100, help="images per category")
    ap.add_argument("--categories", nargs="*", default=None)
    ap.add_argument("--out", default="experiments/sem_scalebar_results.jsonl")
    args = ap.parse_args()

    categories = args.categories or sorted(os.listdir(NFFA_ROOT))
    results = []
    with open(args.out, "w") as out_f:
        for cat in categories:
            cat_dir = os.path.join(NFFA_ROOT, cat)
            if not os.path.isdir(cat_dir):
                continue
            files = sorted(glob.glob(os.path.join(cat_dir, "*.jpg")))[: args.sample]
            for fp in files:
                r = process_image(fp)
                r["category"] = cat
                results.append(r)
                out_f.write(json.dumps(r) + "\n")
            print(f"{cat}: processed {len(files)}")

    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    print("\n" + "=" * 60)
    print("Status breakdown across all sampled images:")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(results):.1f}%)")
    print(f"\nTotal sampled: {len(results)}")
    print(f"Results written to: {args.out}")


if __name__ == "__main__":
    main()
