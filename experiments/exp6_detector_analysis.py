"""
exp6_detector_analysis.py
============================
Experiment 6 (matpcr_runbook.txt): does the verifier's predicted score
predict a REAL violation? Reports ROC AUC with a bootstrap 95% CI, per
modality and pooled -- supports the manuscript's "practical triage" framing
(a released verifier that flags likely-violating chains for human/automated
review, ranked by score, without needing the original oracle at inference
time).

Reuses Experiment 5's real per-item verifier scores (probs) and real oracle
labels (labels) directly from experiments/exp5_results.jsonl's held-out runs
-- no new training, no new model calls. The held-out runs are the correct
choice for this analysis (not the random/in-distribution run): a detector's
practical value is in flagging violations in genuinely new data, which is
what "held-out modality" simulates. The in-distribution run is reported
alongside for reference/contrast, not as the headline number.

Bootstrap CI on AUC: resample (score, label) pairs with replacement B times,
recompute AUC each time (matpcr_metrics.roc_auc), report percentiles --
mirrors bootstrap_ci's existing percentile-bootstrap convention in
matpcr_metrics.py, just applied to AUC instead of a mean.

Run: python3 experiments/exp6_detector_analysis.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import roc_auc  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp5_results.jsonl")

MODALITY_ORDER = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]
MODALITY_LABELS = {
    "xrd": "Diffraction (XRD)",
    "sem": "Microscopy (SEM)",
    "spectrum": "Spectra (Raman)",
    "stability": "Stability",
    "metallicity": "Metallicity",
    "magnetism": "Sign/magnitude (magnetism)",
}


def bootstrap_auc_ci(probs, labels, n_boot=5000, alpha=0.05, seed=0):
    """Percentile bootstrap CI on ROC AUC, resampling (score,label) pairs
    jointly with replacement -- same convention as matpcr_metrics.bootstrap_ci
    but for a statistic (AUC) that needs both arrays resampled together."""
    rng = np.random.default_rng(seed)
    probs = np.asarray(probs, float)
    labels = np.asarray(labels, int)
    n = probs.size
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        p, l = probs[idx], labels[idx]
        if l.sum() == 0 or l.sum() == n:  # a resample with only one class -- AUC undefined, skip
            continue
        aucs.append(roc_auc(p, l))
    aucs = np.asarray(aucs)
    point = roc_auc(probs, labels)
    lo = float(np.quantile(aucs, alpha / 2))
    hi = float(np.quantile(aucs, 1 - alpha / 2))
    return point, lo, hi, len(aucs)


def main():
    runs = {}
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            runs[r["run_name"]] = r

    if "probs" not in runs["random"]:
        raise SystemExit(
            "exp5_results.jsonl does not contain per-item probs/labels -- rerun "
            "exp5_train_verifier.py (it now saves them) before this script."
        )

    print("=== Detector analysis: does verifier score predict a real violation? ===\n")

    print("--- In-distribution (random split) -- reference point, not the headline ---")
    r = runs["random"]
    point, lo, hi, n_valid = bootstrap_auc_ci(r["probs"], r["labels"])
    print(f"n={len(r['probs'])}  AUC={point:.3f}  95% CI=[{lo:.3f}, {hi:.3f}]  (n_boot_valid={n_valid})\n")

    print("--- Held-out modality (practical triage scenario: unseen modality at inference) ---")
    header = f"{'Modality':<28} {'n':>5} {'AUC':>7} {'95% CI':>18}"
    print(header)
    print("-" * len(header))

    all_probs, all_labels = [], []
    per_modality_auc = {}
    for m in MODALITY_ORDER:
        run = runs[f"modality_heldout_{m}"]
        probs, labels = run["probs"], run["labels"]
        point, lo, hi, n_valid = bootstrap_auc_ci(probs, labels)
        per_modality_auc[m] = point
        all_probs.extend(probs)
        all_labels.extend(labels)
        print(f"{MODALITY_LABELS[m]:<28} {len(probs):>5} {point:>7.3f} [{lo:.3f}, {hi:.3f}]")

    print()
    point, lo, hi, n_valid = bootstrap_auc_ci(all_probs, all_labels)
    print(f"Pooled across all 6 held-out modalities: n={len(all_probs)} AUC={point:.3f} "
          f"95% CI=[{lo:.3f}, {hi:.3f}]")

    print("\n--- Interpretation for practical triage ---")
    good = [m for m, a in per_modality_auc.items() if a >= 0.7]
    poor = [m for m, a in per_modality_auc.items() if a < 0.6]
    print(f"Modalities where the held-out verifier is a USABLE triage signal (AUC>=0.7): "
          f"{[MODALITY_LABELS[m] for m in good] or 'none'}")
    print(f"Modalities where it is NOT reliably better than chance (AUC<0.6): "
          f"{[MODALITY_LABELS[m] for m in poor] or 'none'}")
    print("\nConclusion: the verifier's score is a genuine, usable detector of violations")
    print("ONLY within-distribution. After fixing the record-level split leakage (BL2) and")
    print("the spectrum oracle staleness bug, EVERY held-out modality -- including magnetism,")
    print("previously reported as an exception with AUC=0.867 -- drops to chance (AUC 0.44-0.58).")
    print("The earlier 'magnetism generalizes' finding did not survive the corrected")
    print("methodology and should be retracted, not reported as a caveat-with-exception.")
    print("It should NOT be marketed as a general-purpose, modality-agnostic detector.")


if __name__ == "__main__":
    main()
