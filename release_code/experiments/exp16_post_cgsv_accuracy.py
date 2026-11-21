"""
exp16_post_cgsv_accuracy.py
=============================
Resolves version3/otherfiles(redflagetc.)/matpcr_REDFLAGS.txt item A13:
whether CGSV's PCR gain reflects genuine physical correction or the model
retreating to a value the oracle's necessary-condition check accepts
without it being the actually-correct value. exp4_results.jsonl records
each item's final-round claimed_values but never compared them to the
non-circular accuracy ground truth exp3_accuracy_vs_consistency.py uses
(nearest true XRD/Raman peak) -- this script closes that gap by resolving
each item's real source data and applying the SAME criteria exp3 uses
(XRD_ACCURACY_TOL_DEG=0.1, SPECTRUM_ACCURACY_TOL=2.0) to the CGSV item's
final claim.

source_file paths in exp4_results.jsonl point at the old (now-wiped) host's
absolute paths; resolve_path() rewrites them against wherever opXRD/RRUFF
are actually staged on this host via MATPCR_DATA_ROOT.

Run: python3 experiments/exp16_post_cgsv_accuracy.py
Output: experiments/exp4_postcgsv_accuracy.json
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.signal import find_peaks

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from halfB_collect import xrd_reference_peaks, spectrum_signal  # noqa: E402

MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP4_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp4_results.jsonl")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp4_postcgsv_accuracy.json")

XRD_ACCURACY_TOL_DEG = 0.1
SPECTRUM_ACCURACY_TOL = 2.0


def resolve_path(old_path: str) -> str:
    if "opxrd/" in old_path or "opXRD/" in old_path:
        rel = old_path.split("opxrd/")[-1] if "opxrd/" in old_path else old_path.split("opXRD/")[-1]
        return os.path.join(REPO_ROOT, "opxrd", rel)
    if "rruff" in old_path:
        rel = old_path.split("rruff/")[-1]
        return os.path.join(MATPCR_DATA_ROOT, "rruff", rel)
    return old_path


def main():
    recs = [json.loads(l) for l in open(EXP4_PATH)]
    print(f"{len(recs)} total CGSV records")

    results = {"xrd": [], "spectrum": []}
    skipped = 0
    for r in recs:
        modality = r["modality"]
        if modality not in ("xrd", "spectrum"):
            continue
        path = resolve_path(r["source_file"])
        final_claim = r["claimed_values"][-1] if r["claimed_values"] else None
        if final_claim is None:
            skipped += 1
            continue

        if modality == "xrd":
            ref = xrd_reference_peaks(path)
            if ref is None or not ref:
                skipped += 1
                continue
            nearest_dist = min(abs(x - final_claim) for x in ref)
            accurate = nearest_dist <= XRD_ACCURACY_TOL_DEG
        else:
            sig = spectrum_signal(path)
            if sig is None:
                skipped += 1
                continue
            xs, ys = sig
            rng = ys.max() - ys.min()
            if rng <= 0:
                skipped += 1
                continue
            norm = (ys - ys.min()) / rng
            peak_idx, _ = find_peaks(norm, prominence=0.05, distance=5)
            if peak_idx.size == 0:
                skipped += 1
                continue
            nearest_dist = float(np.min(np.abs(xs[peak_idx] - final_claim)))
            accurate = nearest_dist <= SPECTRUM_ACCURACY_TOL

        results[modality].append({
            "model": r["model"], "accurate": accurate,
            "before_consistent": r["before_consistent"], "after_consistent": r["after_consistent"],
        })

    print(f"skipped: {skipped}")
    for m in ("xrd", "spectrum"):
        vals = results[m]
        n = len(vals)
        if n:
            acc = sum(1 for v in vals if v["accurate"])
            print(f"{m}: n={n} post-CGSV accuracy={acc}/{n} = {acc / n:.1%}")
        else:
            print(f"{m}: n=0")

    with open(OUT_PATH, "w") as f:
        json.dump(results, f)
    print(f"Written to: {OUT_PATH}")


if __name__ == "__main__":
    main()
