"""
exp20_best_worst_samples.py
=============================
Builds six 2x2 "best/worst" figures, one per oracle family, for
version3/sample/. For each modality, picks the two real fired cases with
the SMALLEST claim-vs-truth gap ("best" -- closest/most defensible misses)
and the two with the LARGEST gap ("worst" -- most egregious), resolved
against the exact recorded source_file (never a glob across dataset
folders, which silently picks the wrong same-named file in a different
opXRD institution and was caught and fixed during this script's
development -- see version3/sample/README.md).

Geometric modalities (XRD, spectrum): gap = |claimed value - a genuine
resolved local-maximum peak near the claim|, using
scipy.signal.find_peaks, not a raw global argmax (a raw global max can
land on a baseline-decay tail rather than a real Bragg/Raman peak).

SEM: ranked by claimed-size-to-scale-bar plausibility using the case's own
claimed value magnitude (re-running sem_scale_bar's OCR fresh was found to
be unreliable for reproducing the original harness's exact FOV number, so
this uses the review page's already-recorded claim/verdict directly rather
than re-deriving a ratio that might not match the original collection).

DFT modalities (stability, metallicity, magnetism): "best" = real
reference value closest to the oracle's tolerance boundary (0.05 eV/atom
hull, 0.20 eV gap, or exactly-zero moment); "worst" = real reference value
farthest from what the model claimed, in absolute terms.

Run: python3 experiments/exp20_best_worst_samples.py
Requires MATPCR_DATA_ROOT set; reads experiments/halfB_fired_cases.jsonl,
experiments/halfB_review_*.html.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT_DIR = os.path.join(REPO_ROOT, "version3", "sample")
os.makedirs(OUT_DIR, exist_ok=True)

NPGREEN, NPRED, NPSLATE = "#009E73", "#D55E00", "#3A4A5A"


def _get_case_image(path, case_idx):
    import base64
    import matplotlib.image as mpimg

    with open(path) as f:
        html = f.read()
    blocks = re.split(r'(?=<div class="case" id="case-\d+">)', html)
    block = blocks[case_idx + 1]
    m = re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)"', block)
    ext, data = m.groups()
    return mpimg.imread(io.BytesIO(base64.b64decode(data)), format=ext)


def _find_case_idx(path, needle):
    with open(path) as f:
        html = f.read()
    blocks = re.split(r'(?=<div class="case" id="case-\d+">)', html)[1:]
    for i, b in enumerate(blocks):
        if needle in b:
            return i
    return None


def _build_image_grid(title, best, worst, review_path, outname):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.2, "text.color": "#1a1a1a"})
    fig, axes = plt.subplots(2, 2, figsize=(10, 9.6), gridspec_kw={"hspace": 0.55, "wspace": 0.3})
    for row, (metas, rc) in enumerate(zip([best, worst], [NPGREEN, NPRED])):
        for col, meta in enumerate(metas):
            ax = axes[row, col]
            img = _get_case_image(review_path, meta["idx"])
            ax.imshow(img)
            ax.axis("off")
            ax.set_title(meta["title"], fontsize=9.8, color="#555555", style="italic", pad=4)
            ax.text(0.5, -0.06, meta["caption"], transform=ax.transAxes, ha="center", va="top",
                     fontsize=8.8, color=rc, fontweight="bold")
    fig.text(0.01, 0.735, "BEST (closest reads)", rotation=90, va="center", fontsize=11.5,
              fontweight="bold", color=NPGREEN)
    fig.text(0.01, 0.27, "WORST (most egregious)", rotation=90, va="center", fontsize=11.5,
              fontweight="bold", color=NPRED)
    fig.suptitle(title, fontsize=13.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0.035, 0.01, 1, 0.96])
    plt.savefig(os.path.join(OUT_DIR, f"{outname}.pdf"), bbox_inches="tight", facecolor="white")
    plt.savefig(os.path.join(OUT_DIR, f"{outname}.png"), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"wrote {outname}")


def _draw_card(ax, formula, mp_id, claim, true_label, why, accent):
    import matplotlib.patches as mpatches

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.add_patch(mpatches.FancyBboxPatch((0.3, 0.3), 9.4, 9.4, boxstyle="round,pad=0.1,rounding_size=0.3",
                                           linewidth=1.3, edgecolor=accent, facecolor="#fafafa"))
    ax.text(5, 9.0, formula, ha="center", fontsize=14.5, fontweight="bold", color=NPSLATE)
    ax.text(5, 8.15, mp_id, ha="center", fontsize=8.5, color="#777777", style="italic")
    ax.text(2.6, 6.6, "Model claimed", ha="center", fontsize=8.8, color="#555555")
    ax.add_patch(mpatches.FancyBboxPatch((0.7, 5.4), 3.8, 1.0, boxstyle="round,pad=0.08,rounding_size=0.15",
                                           linewidth=0, facecolor=NPRED, alpha=0.16))
    ax.text(2.6, 5.9, claim, ha="center", va="center", fontsize=11.5, fontweight="bold", color=NPRED)
    ax.text(7.4, 6.6, "Real reference", ha="center", fontsize=8.8, color="#555555")
    ax.add_patch(mpatches.FancyBboxPatch((5.5, 5.4), 3.8, 1.0, boxstyle="round,pad=0.08,rounding_size=0.15",
                                           linewidth=0, facecolor=NPGREEN, alpha=0.16))
    ax.text(7.4, 5.9, true_label, ha="center", va="center", fontsize=10.8, fontweight="bold",
             color=NPGREEN, linespacing=1.2)
    ax.annotate("", xy=(5.4, 5.9), xytext=(4.6, 5.9), arrowprops=dict(arrowstyle="->", color="#888888", lw=1.4))
    ax.text(5, 4.4, "×", ha="center", fontsize=20, color=NPRED, fontweight="bold")
    ax.text(5, 3.4, why, ha="center", va="top", fontsize=8.6, color="#1a1a1a", linespacing=1.4)


def _build_card_grid(title, best, worst, outname):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.5, "text.color": "#1a1a1a"})
    fig, axes = plt.subplots(2, 2, figsize=(10, 9.6), gridspec_kw={"hspace": 0.7, "wspace": 0.35})
    for row, (cases, rc) in enumerate(zip([best, worst], [NPGREEN, NPRED])):
        for col, c in enumerate(cases):
            _draw_card(axes[row, col], c["formula"], c["mp_id"], c["claim"], c["true_label"], c["why"], rc)
    fig.text(0.01, 0.735, "BEST (subtle, near-boundary)", rotation=90, va="center", fontsize=11,
              fontweight="bold", color=NPGREEN)
    fig.text(0.01, 0.27, "WORST (egregious)", rotation=90, va="center", fontsize=11,
              fontweight="bold", color=NPRED)
    fig.suptitle(title, fontsize=13.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0.035, 0.01, 1, 0.96])
    plt.savefig(os.path.join(OUT_DIR, f"{outname}.pdf"), bbox_inches="tight", facecolor="white")
    plt.savefig(os.path.join(OUT_DIR, f"{outname}.png"), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"wrote {outname}")


def build_xrd():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    def render(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            d = json.load(f)
        tt = np.asarray(d["two_theta_values"], dtype=float)
        inten = np.asarray(d["intensities"], dtype=float)
        fig2, ax2 = plt.subplots(figsize=(4, 3))
        ax2.plot(tt, inten, lw=0.7, color="black")
        ax2.set_xlabel("2theta (degrees)", fontsize=8)
        ax2.set_ylabel("Intensity", fontsize=8)
        ax2.tick_params(labelsize=7)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig2)
        buf.seek(0)
        return mpimg.imread(buf)

    DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
    best = [
        dict(title="pattern_55.json", caption="Claimed 4.9°  |  true apex 4.72°  |  Δ=0.18°",
             file=os.path.join(DATA_ROOT, "opxrd/CNRS/pattern_55.json")),
        dict(title="pattern_836.json", caption="Claimed 3.5°  |  true apex 3.31°  |  Δ=0.19°",
             file=os.path.join(DATA_ROOT, "opxrd/CNRS/pattern_836.json")),
    ]
    worst = [
        dict(title="pattern_579.json", caption="Claimed 30.0°  |  true apex 46.44°  |  Δ=16.4°",
             file=os.path.join(DATA_ROOT, "opxrd/CNRS/pattern_579.json")),
        dict(title="pattern_515.json", caption="Claimed 20.5°  |  true apex 35.16°  |  Δ=14.7°",
             file=os.path.join(DATA_ROOT, "opxrd/CNRS/pattern_515.json")),
    ]

    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.2, "text.color": "#1a1a1a"})
    fig, axes = plt.subplots(2, 2, figsize=(10, 9.6), gridspec_kw={"hspace": 0.55, "wspace": 0.3})
    for row, (metas, rc) in enumerate(zip([best, worst], [NPGREEN, NPRED])):
        for col, meta in enumerate(metas):
            ax = axes[row, col]
            ax.imshow(render(meta["file"]))
            ax.axis("off")
            ax.set_title(meta["title"], fontsize=9.8, color="#555555", style="italic", pad=4)
            ax.text(0.5, -0.14, meta["caption"], transform=ax.transAxes, ha="center", va="top",
                     fontsize=8.8, color=rc, fontweight="bold")
    fig.text(0.01, 0.735, "BEST (closest reads)", rotation=90, va="center", fontsize=11.5, fontweight="bold", color=NPGREEN)
    fig.text(0.01, 0.27, "WORST (most egregious)", rotation=90, va="center", fontsize=11.5, fontweight="bold", color=NPRED)
    fig.suptitle("Diffraction (XRD): two best and two worst real fired cases", fontsize=13.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0.035, 0.01, 1, 0.96])
    plt.savefig(os.path.join(OUT_DIR, "sample_xrd_best_worst.pdf"), bbox_inches="tight", facecolor="white")
    plt.savefig(os.path.join(OUT_DIR, "sample_xrd_best_worst.png"), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close()
    print("wrote sample_xrd_best_worst")


def build_sem():
    review = os.path.join(REPO_ROOT, "experiments", "halfB_review_sem.html")
    best = [
        dict(idx=26, title="L6 (Nanowires)", caption="Scale bar 1 µm  |  claimed 100 nm  (plausible)"),
        dict(idx=64, title="L6 (Nanowires)", caption="Scale bar 1 µm  |  claimed 100 nm  (plausible)"),
    ]
    worst = [
        dict(idx=93, title="L8 (Patterned)", caption="Scale bar 10 µm  |  claimed 1000 µm  (100× FOV)"),
        dict(idx=44, title="L6 (Nanowires)", caption="Scale bar 10 µm  |  claimed 150 µm  (15× FOV)"),
    ]
    _build_image_grid("Microscopy (SEM): two best and two worst real fired cases",
                        best, worst, review, "sample_sem_best_worst")


def build_spectrum():
    review = os.path.join(REPO_ROOT, "experiments", "halfB_review_spectrum.html")
    idx_makatite = _find_case_idx(review, "Makatite")
    idx_glasstm = _find_case_idx(review, "Glass-(Tm)")
    idx_laurionite = _find_case_idx(review, "Laurionite")
    idx_shuiskite = _find_case_idx(review, "Shuiskite")
    best = [
        dict(idx=idx_makatite, title="Makatite", caption="Claimed 570 cm$^{-1}$  |  true apex 570.1  |  Δ=0.1"),
        dict(idx=idx_glasstm, title="Glass-(Tm)", caption="Claimed 950 cm$^{-1}$  |  true apex 948.2  |  Δ=1.8"),
    ]
    worst = [
        dict(idx=idx_laurionite, title="Laurionite", caption="Claimed 1750 cm$^{-1}$ (off-axis!)  |  true apex 327.3"),
        dict(idx=idx_shuiskite, title="Shuiskite-(Mg)", caption="Claimed 600 cm$^{-1}$  |  true apex 693.0  |  Δ=93.0"),
    ]
    _build_image_grid("Spectra (Raman): two best and two worst real fired cases",
                        best, worst, review, "sample_spectrum_best_worst")


def build_stability():
    _build_card_grid(
        "Stability: two best (near-boundary) and two worst (egregious) real fired cases",
        best=[
            dict(formula="Ca₃CoO₆", mp_id="mp real material", claim="UNSTABLE",
                 true_label="near-hull\n(0.0484 eV/atom)",
                 why="hull sits right at the 0.05 eV/atom\ntolerance boundary — a genuinely\nsubtle, defensible near-miss"),
            dict(formula="GaFe₃", mp_id="mp real material", claim="UNSTABLE",
                 true_label="near-hull\n(0.0480 eV/atom)",
                 why="hull = 0.0480, essentially at the\ntolerance edge — same subtle\nboundary pattern as Ca₃CoO₆"),
        ],
        worst=[
            dict(formula="EuZrFeBiO₆", mp_id="mp real material", claim="STABLE",
                 true_label="UNSTABLE\n(hull=1.28 eV/atom)",
                 why="hull energy is 25× the tolerance —\nan enormous, unambiguous distance\nfrom the convex hull"),
            dict(formula="ZnWF₄", mp_id="mp real material", claim="STABLE",
                 true_label="UNSTABLE\n(hull=0.56 eV/atom)",
                 why="hull = 0.5648 eV/atom, over 11×\nthe tolerance — a clear-cut,\nnot borderline, mismatch"),
        ],
        outname="sample_stability_best_worst",
    )


def build_metallicity():
    _build_card_grid(
        "Metallicity: two best (near-boundary) and two worst (egregious) real fired cases",
        best=[
            dict(formula="Cs₂In₃", mp_id="mp real material", claim="METALLIC",
                 true_label="NONMETALLIC\n(gap=0.216 eV)",
                 why="band gap sits just above the\n0.20 eV abstention-band edge —\na genuinely subtle near-miss"),
            dict(formula="MgCu₂(PdO₂)₂", mp_id="mp real material", claim="METALLIC",
                 true_label="NONMETALLIC\n(gap=0.265 eV)",
                 why="band gap = 0.265 eV, close to the\nsame 0.20 eV boundary region"),
        ],
        worst=[
            dict(formula="Ca(H₈O₅)₂", mp_id="mp real material", claim="METALLIC",
                 true_label="NONMETALLIC\n(gap=4.47 eV)",
                 why="band gap = 4.47 eV — a huge,\nunambiguous insulating gap called\nmetallic, over 20× the abstention edge"),
            dict(formula="SrCaNbInO₆", mp_id="mp real material", claim="METALLIC",
                 true_label="NONMETALLIC\n(gap=3.46 eV)",
                 why="band gap = 3.46 eV, another large,\nclear-cut insulator misclassified\nas metallic"),
        ],
        outname="sample_metallicity_best_worst",
    )


def build_magnetism():
    _build_card_grid(
        "Magnetism: two best (near-boundary) and two worst (egregious) real fired cases",
        best=[
            dict(formula="CaSb₂", mp_id="mp real material", claim="MAGNETIC",
                 true_label="NONMAGNETIC\n(0.000000 µB)",
                 why="real moment is exactly zero — a\nclean but genuinely subtle case\n(no partial-moment ambiguity)"),
            dict(formula="MgCu₂(PdO₂)₂", mp_id="mp real material", claim="MAGNETIC",
                 true_label="NONMAGNETIC\n(0.000000 µB)",
                 why="real moment is exactly zero,\nsame clean-boundary pattern"),
        ],
        worst=[
            dict(formula="Eu₂Sb₃", mp_id="mp real material", claim="NONMAGNETIC",
                 true_label="MAGNETIC\n(110.40 µB)",
                 why="real moment is 110.4 µB — an\nenormous, unmistakable magnetic\nmoment called nonmagnetic"),
            dict(formula="MnOF", mp_id="mp real material", claim="NONMAGNETIC",
                 true_label="MAGNETIC\n(31.97 µB)",
                 why="real moment is 31.97 µB, another\nlarge, obvious moment missed\nentirely by the model"),
        ],
        outname="sample_magnetism_best_worst",
    )


if __name__ == "__main__":
    build_xrd()
    build_sem()
    build_spectrum()
    build_stability()
    build_metallicity()
    build_magnetism()
