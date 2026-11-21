"""
exp21_precision_intervals.py
============================
KBS revision R1 (Reviewer 2, W3): interval estimates and an "unsure"
sensitivity analysis for the human oracle-precision audit (Table 1).

For each oracle family, reads the single-annotator review export in the repo
root and reports:
  - precision = real / (real + false_positive)   (the Table 1 convention)
  - Wilson and exact Clopper-Pearson 95% intervals for that precision
  - sensitivity: unsure counted as real (upper) and as false positive (lower)
No model calls; deterministic.

Run: python experiments/exp21_precision_intervals.py
Writes: experiments/exp21_results.json
"""

from __future__ import annotations

import json
import math
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import re

from scipy.stats import beta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = {
    "Diffraction (XRD)": "xrd.txt",
    "Microscopy (SEM)": "sem.txt",
    "Spectra (Raman)": "spectrum_halfB_review_2026-08-06.txt",
    "Stability": "stability_halfB_review_2026-08-06.txt",
    "Metallicity": "metallicity_halfB_review_2026-08-06.txt",
    "Magnetism": "magnetism_halfB_review_2026-08-06.txt",
}


def load_verdicts(path: str) -> list[str]:
    txt = open(path, encoding="utf-8").read()
    # some exports have bare tokens: "verdict": real  -> quote them
    txt = re.sub(r'("verdict"\s*:\s*)(real|false_positive|unsure)\b', r'\1"\2"', txt)
    return {r["case"]: r["verdict"] for r in json.loads(txt)["reviews"]}


def scored_cases(fam):
    """Case numbers (1-based, review-page order) that are scored under the active stability rule."""
    if fam not in ("Stability", "stability"):
        return None
    recs = [json.loads(l) for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "halfB_dft_fired_cases.jsonl"))]
    fired = [r for r in recs if r["claim_type"] == "stability" and str(r["fired"]).lower() == "true"]
    return {i for i, r in enumerate(fired, 1) if final_oracle.keep_dft_fired(r)}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def main() -> None:
    out = {}
    print(f"{'Family':<20}{'real':>6}{'FP':>5}{'uns':>5}{'prec':>8}  {'Wilson 95%':<17}{'Clopper-Pearson':<17}"
          f"{'unsure=FP':>10}{'unsure=real':>12}")
    for fam, fn in EXPORTS.items():
        vd = load_verdicts(os.path.join(REPO_ROOT, fn))
        keep = scored_cases(fam)
        v = [x for c, x in vd.items() if keep is None or c in keep]
        r, fp, u = v.count("real"), v.count("false_positive"), v.count("unsure")
        n = r + fp
        prec = r / n
        w = wilson(r, n)
        cp = clopper_pearson(r, n)
        lower = r / (r + fp + u)          # unsure counted as false positives
        upper = (r + u) / (r + fp + u)    # unsure counted as genuine violations
        out[fam] = dict(n_reviewed=len(v), real=r, false_positive=fp, unsure=u, precision=prec,
                        wilson95=w, clopper_pearson95=cp, unsure_as_fp=lower, unsure_as_real=upper)
        print(f"{fam:<20}{r:>6}{fp:>5}{u:>5}{prec:>8.3f}  [{w[0]:.3f}, {w[1]:.3f}]   "
              f"[{cp[0]:.3f}, {cp[1]:.3f}]   {lower:>8.3f}{upper:>12.3f}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp21_results.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
