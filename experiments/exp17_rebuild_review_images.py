"""
exp17_rebuild_review_images.py
=================================
Resolves the blocker found while attempting matpcr_REDFLAGS.txt item A1:
halfB_report.py's review-page generation failed because every fired case's
image_path pointed at a rendered plot PNG (XRD, spectrum) or raw JPEG (SEM)
that only existed on the old, now-wiped host. This script regenerates the
missing images so halfB_report.py can run.

- XRD/spectrum: image_path was always <SCRATCH_IMG_DIR>/{xrd,raman}_<basename
  of source_file>.png -- a rendered plot, not raw data. Re-render it from
  source_file (resolved against the currently-staged opXRD/RRUFF copies)
  using the EXACT same matplotlib recipe as pilot.py's build_xrd_items /
  build_spectrum_items, so the regenerated plot is pixel-equivalent to what
  the model actually saw.
- SEM: image_path pointed directly at the raw NFFA-EUROPE JPEG (no
  rendering involved) at an /ephemeral/matpcr/... path that no longer
  exists; only the root prefix changed since staging, so this is a path
  rewrite, not a re-render.

Run: python3 experiments/exp17_rebuild_review_images.py
Rewrites experiments/halfB_fired_cases.jsonl's image_path fields in place
(a .bak backup of the original is written first) and creates any missing
PNG file under $MATPCR_SCRATCH_IMG_DIR.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

import numpy as np

MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRED_CASES_PATH = os.path.join(REPO_ROOT, "experiments", "halfB_fired_cases.jsonl")
SCRATCH_IMG_DIR = os.environ.get(
    "MATPCR_SCRATCH_IMG_DIR", os.path.join(MATPCR_DATA_ROOT, "pilot_images")
)
os.makedirs(SCRATCH_IMG_DIR, exist_ok=True)


def resolve_source(old_path: str) -> "str | None":
    if "opxrd/" in old_path or "opXRD/" in old_path:
        rel = old_path.split("opxrd/")[-1] if "opxrd/" in old_path else old_path.split("opXRD/")[-1]
        p = os.path.join(REPO_ROOT, "opxrd", rel)
        return p if os.path.exists(p) else None
    if "rruff" in old_path:
        rel = old_path.split("rruff/")[-1]
        p = os.path.join(MATPCR_DATA_ROOT, "rruff", rel)
        return p if os.path.exists(p) else None
    if "nffa/" in old_path:
        rel = old_path.split("nffa/")[-1]
        p = os.path.join(MATPCR_DATA_ROOT, "nffa", rel)
        return p if os.path.exists(p) else None
    return old_path if os.path.exists(old_path) else None


def render_xrd(source_file: str, out_path: str) -> bool:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        with open(source_file, encoding="utf-8", errors="replace") as f:
            d = json.load(f)
        two_theta = np.asarray(d["two_theta_values"], dtype=float)
        intensities = np.asarray(d["intensities"], dtype=float)
    except Exception:
        return False
    if two_theta.size < 10:
        return False

    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    ax.plot(two_theta, intensities, linewidth=0.8, color="black")
    ax.set_xlabel("2theta (degrees)")
    ax.set_ylabel("Intensity")
    ax.set_title("XRD pattern")
    ax.set_xticks(np.arange(0, two_theta.max() + 10, 10))
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def render_spectrum(source_file: str, out_path: str) -> bool:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs, ys = [], []
    try:
        with open(source_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("##"):
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    continue
                xs.append(float(parts[0]))
                ys.append(float(parts[1]))
    except Exception:
        return False
    if len(xs) < 10:
        return False

    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    ax.plot(xs, ys, linewidth=0.8, color="black")
    ax.set_xlabel("Raman shift (cm-1)")
    ax.set_ylabel("Intensity")
    ax.set_title("Raman spectrum")
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    with open(FIRED_CASES_PATH) as f:
        recs = [json.loads(l) for l in f]

    shutil.copy(FIRED_CASES_PATH, FIRED_CASES_PATH + ".bak")

    counts = {"xrd_rendered": 0, "spectrum_rendered": 0, "sem_rewritten": 0,
              "already_ok": 0, "failed": 0}

    for r in recs:
        if not r.get("fired"):
            continue
        modality = r["modality"]
        old_img = r["image_path"]

        if os.path.exists(old_img):
            counts["already_ok"] += 1
            continue

        if modality == "sem":
            resolved = resolve_source(old_img)
            if resolved is None:
                counts["failed"] += 1
                print(f"FAILED (sem path): {old_img}")
                continue
            r["image_path"] = resolved
            counts["sem_rewritten"] += 1
            continue

        source_file = resolve_source(r["source_file"])
        if source_file is None:
            counts["failed"] += 1
            print(f"FAILED (source not found): {r['source_file']}")
            continue

        out_path = os.path.join(SCRATCH_IMG_DIR, os.path.basename(old_img))
        if modality == "xrd":
            ok = render_xrd(source_file, out_path)
            key = "xrd_rendered"
        elif modality == "spectrum":
            ok = render_spectrum(source_file, out_path)
            key = "spectrum_rendered"
        else:
            ok = False
            key = None

        if ok:
            r["image_path"] = out_path
            counts[key] += 1
        else:
            counts["failed"] += 1
            print(f"FAILED (render): {source_file}")

    with open(FIRED_CASES_PATH, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")

    print(counts)


if __name__ == "__main__":
    main()
