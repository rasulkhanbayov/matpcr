"""
exp3_aggregate.py
===================
Aggregate experiments/exp3_results.jsonl into the accuracy-vs-consistency
four-cell breakdown per (model, modality): correct+consistent,
correct+inconsistent, wrong+consistent, wrong+inconsistent. Pools all 3
seeds together per cell (same convention as exp2_aggregate.py).

The headline number per cell is the "gap": items that are accurate but
flagged inconsistent, plus items that are inaccurate but flagged
consistent -- these are exactly the cases where PCR and accuracy disagree,
demonstrating PCR carries information accuracy alone does not capture.

Run: python3 experiments/exp3_aggregate.py
"""

from __future__ import annotations

import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
from collections import defaultdict

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp3_results.jsonl")

MODEL_ORDER = ["local", "gemini", "gpt4o", "claude"]
MODEL_LABELS = {
    "local": "Qwen2.5-VL-7B",
    "gemini": "Gemini 2.5 Flash Lite",
    "gpt4o": "GPT-4o",
    "claude": "Claude Sonnet 4.5",
}
MODALITY_ORDER = ["xrd", "spectrum", "stability"]
MODALITY_LABELS = {
    "xrd": "Diffraction (XRD)",
    "spectrum": "Spectra (Raman)",
    "stability": "Stability",
}


def main():
    cells = defaultdict(list)  # (model, modality) -> list of (accurate, consistent) bools
    n_records = 0
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            if not final_oracle.keep(r):
                continue
            cells[(r["model"], r["modality"])].append((r["accurate"], r["consistent"]))
            n_records += 1

    print(f"Total records aggregated: {n_records}\n")

    header = (
        f"{'Model':<22} {'Modality':<18} {'n':>5} {'Acc':>7} {'PCR':>7} "
        f"{'CC':>6} {'CI':>6} {'WC':>6} {'WI':>6} {'Gap':>7}"
    )
    print(header)
    print("-" * len(header))

    all_gap_frac = []
    for modality in MODALITY_ORDER:
        for model in MODEL_ORDER:
            vals = cells.get((model, modality), [])
            if not vals:
                continue
            n = len(vals)
            cc = sum(1 for a, c in vals if a and c)
            ci = sum(1 for a, c in vals if a and not c)
            wc = sum(1 for a, c in vals if not a and c)
            wi = sum(1 for a, c in vals if not a and not c)
            acc = sum(1 for a, _ in vals if a) / n
            pcr = sum(1 for _, c in vals if c) / n
            gap = (ci + wc) / n  # cases where accuracy and consistency disagree
            all_gap_frac.append(gap)
            print(
                f"{MODEL_LABELS[model]:<22} {MODALITY_LABELS[modality]:<18} {n:>5} "
                f"{acc:>7.3f} {pcr:>7.3f} {cc:>6} {ci:>6} {wc:>6} {wi:>6} {gap:>7.3f}"
            )
        print()

    print("Legend: CC=correct+consistent CI=correct+inconsistent WC=wrong+consistent "
          "WI=wrong+inconsistent")
    print("Gap = (CI + WC) / n : fraction where accuracy and PCR disagree\n")
    if all_gap_frac:
        print(f"Mean gap across all {len(all_gap_frac)} cells: {sum(all_gap_frac)/len(all_gap_frac):.3f}")

    print("\nNote: Stability modality accuracy uses Materials Project's own strict is_stable")
    print("label; consistency uses the oracle's looser 0.05 eV/atom tolerance. MP reference")
    print("values are NOT YET independently validated by the domain co-author (see CLAUDE.md).")


def stability_balanced_accuracy():
    """Per-model accuracy on each Materials Project is_stable class and their mean (balanced accuracy)
    for the stability arm, on the records scored under the active rule."""
    from collections import defaultdict as _dd
    per = _dd(lambda: {True: [], False: []})
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            if r["modality"] != "stability" or not final_oracle.keep(r) or "true_stable" not in r:
                continue
            per[r["model"]][bool(r["true_stable"])].append(bool(r["claimed_stable"]) == bool(r["true_stable"]))
    print("\nStability balanced accuracy (MP is_stable classes):")
    for m, d in per.items():
        a_s = sum(d[True]) / len(d[True]) if d[True] else float("nan")
        a_u = sum(d[False]) / len(d[False]) if d[False] else float("nan")
        print(f"  {m:<10} stable {sum(d[True])}/{len(d[True])}  unstable {sum(d[False])}/{len(d[False])}  "
              f"balanced {(a_s + a_u) / 2:.3f}")



if __name__ == "__main__":
    main()
    stability_balanced_accuracy()
