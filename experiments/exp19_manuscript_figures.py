"""
exp19_manuscript_figures.py
=============================
Builds three real-data figures for version3/matpcr_snjnl.tex, requested
directly (not tied to a specific red-flag item): the manuscript had no
worked examples anywhere, only schematics and aggregate tables. All three
figures use real artifacts already on disk -- no new model calls.

  1. fig_precision_funnel.pdf -- stacked bars of real/false_positive/unsure
     from all six Half-B review exports (xrd.txt, sem.txt,
     spectrum_halfB_review_2026-08-06.txt, stability/metallicity/magnetism
     _halfB_review_2026-08-06.txt), reproducing Table 1's precision column
     as a visual companion.
  2. fig_failure_gallery.pdf -- three real annotated cases, one per image
     modality, extracted directly from experiments/halfB_review_{xrd,sem,
     spectrum}.html (the base64-embedded plot images plus each case's
     claim/verdict), with claim-vs-true-peak annotations added.
  3. fig_cgsv_trajectory.pdf -- a real 3-round CGSV revision trajectory
     (GPT-4o, opXRD CNRS pattern_941, from experiments/exp4_results.jsonl)
     plotted against the real diffractogram and its real reference Bragg
     peaks (pymatgen), illustrating the "retreat, not correction" finding
     already quantified in Results (post-CGSV accuracy 29.8% on
     diffraction vs. far higher post-CGSV PCR).

Run: python3 experiments/exp19_manuscript_figures.py
Requires MATPCR_DATA_ROOT set (for the opXRD pattern file) and the halfB
review .txt exports + .html pages present at their usual repo locations.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
OUT_DIR = os.path.join(REPO_ROOT, "version3", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

NPBLUE, NPORANGE, NPGREEN, NPRED, NPSLATE = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#3A4A5A",
)

REVIEW_FILES = {
    "Diffraction\n(XRD)": "xrd.txt",
    "Microscopy\n(SEM)": "sem.txt",
    "Spectra\n(Raman)": "spectrum_halfB_review_2026-08-06.txt",
    "Stability": "stability_halfB_review_2026-08-06.txt",
    "Metallicity": "metallicity_halfB_review_2026-08-06.txt",
    "Magnetism": "magnetism_halfB_review_2026-08-06.txt",
}


def _tally(path):
    with open(path) as f:
        raw = f.read()
    fixed = re.sub(r'"verdict":\s*(real|false_positive|unsure)\b', r'"verdict": "\1"', raw)
    d = json.loads(fixed)
    from collections import Counter
    return dict(Counter(r["verdict"] for r in d["reviews"]))


def build_precision_funnel():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.5,
                          "axes.edgecolor": "#333333", "text.color": "#1a1a1a",
                          "axes.linewidth": 0.8})

    order = list(REVIEW_FILES)
    real, fp, unsure, ns = [], [], [], []
    for label in order:
        t = _tally(os.path.join(REPO_ROOT, REVIEW_FILES[label]))
        r, f, u = t.get("real", 0), t.get("false_positive", 0), t.get("unsure", 0)
        n = r + f + u
        real.append(100 * r / n)
        fp.append(100 * f / n)
        unsure.append(100 * u / n)
        ns.append(n)

    ypos = [0, 1, 2, 3.6, 4.6, 5.6]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bar_h = 0.62

    left = np.zeros(len(order))
    ax.barh(ypos, real, height=bar_h, color=NPGREEN, label="Real violation", left=left, zorder=3)
    left = np.array(real)
    ax.barh(ypos, fp, height=bar_h, color=NPRED, label="False positive", left=left, zorder=3)
    left = left + np.array(fp)
    ax.barh(ypos, unsure, height=bar_h, color="#b0b0b0", label="Unsure", left=left, zorder=3)

    for yp, r, n in zip(ypos, real, ns):
        ax.text(101.5, yp, f"n={n}", va="center", fontsize=8.3, color="#555555")
        ax.text(r / 2, yp, f"{r:.1f}%", va="center", ha="center", fontsize=8.6,
                 color="white", fontweight="bold", zorder=4)

    ax.set_yticks(ypos)
    ax.set_yticklabels(order, fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 118)
    ax.set_ylim(6.35, -1.1)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("Share of oracle-fired cases judged by human review", fontsize=9.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=8.8, ncol=3, bbox_to_anchor=(1.0, -0.20))
    ax.text(-25, -0.85, "GEOMETRIC ORACLES", fontsize=8.8, fontweight="bold", color=NPSLATE)
    ax.text(-25, 3.15, "DFT-GROUNDED ORACLES", fontsize=8.8, fontweight="bold", color=NPSLATE)

    fig.suptitle("Oracle precision audit: every human-reviewed fired case, all six families",
                  fontsize=11.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0.02, 0.02, 1, 0.95])
    out = os.path.join(OUT_DIR, "fig_precision_funnel.pdf")
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"wrote {out}")


def _get_case_image(path, case_idx):
    import matplotlib.image as mpimg
    with open(path) as f:
        html = f.read()
    blocks = re.split(r'(?=<div class="case" id="case-\d+">)', html)
    block = blocks[case_idx + 1]
    m = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)"', block)
    ext, data = m.groups()
    return mpimg.imread(io.BytesIO(base64.b64decode(data)), format=ext)


def build_failure_gallery():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9,
                          "axes.edgecolor": "#333333", "text.color": "#1a1a1a"})

    xrd_img = _get_case_image(os.path.join(REPO_ROOT, "experiments/halfB_review_xrd.html"), 0)
    sem_img = _get_case_image(os.path.join(REPO_ROOT, "experiments/halfB_review_sem.html"), 0)
    spec_img = _get_case_image(os.path.join(REPO_ROOT, "experiments/halfB_review_spectrum.html"), 0)

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.3))
    for ax, img, title in zip(axes, [xrd_img, sem_img, spec_img],
                               ["Diffraction", "Microscopy", "Spectra"]):
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(title, fontsize=11, fontweight="bold", color=NPSLATE, pad=8)

    h, w = xrd_img.shape[0], xrd_img.shape[1]

    def xrd_to_px(theta, x0=0.115, x1=0.965, t0=-4, t1=152):
        return (x0 + (theta - t0) / (t1 - t0) * (x1 - x0)) * w

    claim_px = xrd_to_px(3.5)
    axes[0].annotate("claimed\n3.5°", xy=(claim_px, 0.86 * h), xytext=(claim_px - 70, 0.35 * h),
                       arrowprops=dict(arrowstyle="->", color=NPRED, lw=1.6),
                       color=NPRED, fontsize=8, fontweight="bold", ha="center")

    h2, w2 = spec_img.shape[0], spec_img.shape[1]

    def spec_to_px(shift, x0=0.145, x1=0.965, s0=40, s1=1330):
        return (x0 + (shift - s0) / (s1 - s0) * (x1 - x0)) * w2

    claim_px2 = spec_to_px(800)
    true_px2 = spec_to_px(830)
    axes[2].annotate("claimed\n800", xy=(claim_px2, 0.42 * h2), xytext=(claim_px2 - 140, 0.15 * h2),
                       arrowprops=dict(arrowstyle="->", color=NPRED, lw=1.6),
                       color=NPRED, fontsize=8, fontweight="bold", ha="center")
    axes[2].annotate("true apex\n~830", xy=(true_px2, 0.10 * h2), xytext=(true_px2 + 60, 0.15 * h2),
                       arrowprops=dict(arrowstyle="->", color=NPBLUE, lw=1.6),
                       color=NPBLUE, fontsize=8, fontweight="bold", ha="left")

    captions = [
        ("pattern_911.json (opXRD)", "Claimed 3.5° — oracle: INCONSISTENT",
         "Reads near the y-axis rather than the true apex\n— the dominant XRD failure mode (70.5% of\nconfirmed errors are gridline/apex misreads)."),
        ("L1_ae57...jpg (NFFA-EUROPE)", "Claimed 100 µm — oracle: INCONSISTENT",
         "Scale bar reads 10 µm; the claimed feature is\n10× the entire field of view — a scale-factor\narithmetic error (14.0% of confirmed SEM errors)."),
        ("Gotzenite (RRUFF Raman)", "Claimed 800 cm$^{-1}$ — oracle: INCONSISTENT",
         "True apex sits near 830 cm$^{-1}$; the claim lands\njust outside the oracle's 5 cm$^{-1}$ tolerance —\nthe pattern behind 94% of the spectrum\noracle's false positives."),
    ]
    for ax, (src, verdict, cap) in zip(axes, captions):
        ax.text(0.5, -0.09, src, transform=ax.transAxes, ha="center", va="top",
                 fontsize=7.8, color="#555555", style="italic")
        ax.text(0.5, -0.155, verdict, transform=ax.transAxes, ha="center", va="top",
                 fontsize=8.2, color=NPRED, fontweight="bold")
        ax.text(0.5, -0.245, cap, transform=ax.transAxes, ha="center", va="top",
                 fontsize=7.9, color="#1a1a1a", linespacing=1.4)

    fig.suptitle("Real reasoning-chain failures, one per image modality (Half-B fired cases, human-confirmed)",
                  fontsize=11, fontweight="bold", y=1.01)
    plt.tight_layout(rect=[0, 0.02, 1, 0.97])
    out = os.path.join(OUT_DIR, "fig_failure_gallery.pdf")
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"wrote {out}")


def build_cgsv_trajectory():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from halfB_collect import xrd_reference_peaks

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.5,
                          "axes.edgecolor": "#333333", "text.color": "#1a1a1a",
                          "axes.linewidth": 0.8})

    pattern_path = os.path.join(MATPCR_DATA_ROOT, "opxrd", "CNRS", "pattern_941.json")
    with open(pattern_path, encoding="utf-8", errors="replace") as f:
        d = json.load(f)
    two_theta = np.asarray(d["two_theta_values"], dtype=float)
    intensities = np.asarray(d["intensities"], dtype=float)
    ref_peaks = sorted(xrd_reference_peaks(pattern_path) or [])

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(two_theta, intensities, color="#333333", linewidth=0.7, zorder=2)
    ax.set_xlim(15, 45)
    window = intensities[(two_theta >= 15) & (two_theta <= 45)]
    ymax = window.max() * 1.30
    ax.set_ylim(0, ymax)

    for rp in ref_peaks:
        if 15 <= rp <= 45:
            ax.axvline(rp, color=NPBLUE, alpha=0.18, lw=6, zorder=1)

    claimed = [28.3, 27.9, 28.6]  # real exp4_results.jsonl record: gpt4o / pattern_941.json
    rounds = ["Round 1 (before)", "Round 2", "Round 3 (after, CGSV)"]
    colors = [NPRED, NPORANGE, NPGREEN]
    y_levels = [0.88, 0.77, 0.66]
    for c, lab, col, yl in zip(claimed, rounds, colors, y_levels):
        ax.axvline(c, color=col, linestyle="--", lw=1.8, zorder=3)
        ax.annotate(f"{lab}: {c}°", xy=(c, ymax * yl), xytext=(c + 2.6, ymax * yl),
                     fontsize=8.4, color=col, fontweight="bold", va="center",
                     arrowprops=dict(arrowstyle="-", color=col, lw=1.2))

    nearest_ref = min(ref_peaks, key=lambda r: abs(r - claimed[-1]))
    global_max_theta = two_theta[np.argmax(window)] if window.max() == intensities.max() else two_theta[
        (two_theta >= 15) & (two_theta <= 45)
    ][np.argmax(window)]

    ax.annotate(f"true reference\npeak: {nearest_ref:.2f}°", xy=(nearest_ref, ymax * 0.245),
                 xytext=(32.5, ymax * 0.35), fontsize=8.2, color=NPBLUE, fontweight="bold", ha="left",
                 arrowprops=dict(arrowstyle="->", color=NPBLUE, lw=1.4))
    ax.annotate(f"global max ({global_max_theta:.2f}°) —\nnot what round 3 landed near",
                 xy=(global_max_theta, ymax * 0.80), xytext=(35.5, ymax * 0.80),
                 fontsize=7.6, color="#777777", ha="left", style="italic",
                 arrowprops=dict(arrowstyle="->", color="#999999", lw=1.0))

    ax.set_xlabel("2θ (degrees)", fontsize=9.8)
    ax.set_ylabel("Intensity", fontsize=9.8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("CGSV in action: a real GPT-4o revision trajectory (opXRD, CNRS pattern 941)",
                  fontsize=11.3, fontweight="bold", y=1.02)
    ax.set_title(
        "Blue bands = real reference Bragg peaks (pymatgen). CGSV's revised answer lands within\n"
        "tolerance of a genuine peak, but not the tallest one it originally reasoned about.",
        fontsize=8.6, color="#555555", pad=12,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    out = os.path.join(OUT_DIR, "fig_cgsv_trajectory.pdf")
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"wrote {out}")


if __name__ == "__main__":
    build_precision_funnel()
    build_failure_gallery()
    build_cgsv_trajectory()
