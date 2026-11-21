"""
exp4_aggregate.py
===================
Aggregate experiments/exp4_results.jsonl into Table 2 (matpcr_snjnl.tex,
tab:cgsv): PCR before/after CGSV per (model, modality), pooling all 3 seeds,
plus the exact paired McNemar test (matpcr_metrics.mcnemar_exact) on the
before/after consistency pairs -- fixes c, regressions b, p-value, residual
violations after K rounds.

Run: python3 experiments/exp4_aggregate.py
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import mcnemar_exact, bootstrap_ci  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp4_results.jsonl")

MODEL_ORDER = ["local", "gemini", "gpt4o", "claude"]
MODEL_LABELS = {
    "local": "Qwen2.5-VL-7B",
    "gemini": "Gemini 2.5 Flash Lite",
    "gpt4o": "GPT-4o",
    "claude": "Claude Sonnet 4.5",
}
MODALITY_ORDER = ["xrd", "spectrum"]
MODALITY_LABELS = {"xrd": "Diffraction (XRD)", "spectrum": "Spectra (Raman)"}


def main():
    cells = defaultdict(list)  # (model, modality) -> list of records
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            cells[(r["model"], r["modality"])].append(r)

    n_total = sum(len(v) for v in cells.values())
    print(f"Total records aggregated: {n_total}\n")

    header = (
        f"{'Model':<22} {'Modality':<12} {'n':>4} {'PCR_before':>11} {'PCR_after':>10} "
        f"{'b_regr':>7} {'c_fix':>6} {'p_value':>10} {'residual':>9}"
    )
    print(header)
    print("-" * len(header))

    all_before, all_after = defaultdict(list), defaultdict(list)
    for modality in MODALITY_ORDER:
        for model in MODEL_ORDER:
            recs = cells.get((model, modality), [])
            if not recs:
                continue
            n = len(recs)
            before = [r["before_consistent"] for r in recs]
            after = [r["after_consistent"] for r in recs]
            pcr_before = sum(before) / n
            pcr_after = sum(after) / n
            mc = mcnemar_exact(before, after)
            residual = sum(1 for a in after if not a)
            all_before[model].extend(before)
            all_after[model].extend(after)
            print(
                f"{MODEL_LABELS[model]:<22} {MODALITY_LABELS[modality]:<12} {n:>4} "
                f"{pcr_before:>11.3f} {pcr_after:>10.3f} "
                f"{mc['b_regressions']:>7} {mc['c_fixes']:>6} {mc['p_value']:>10.2e} {residual:>9}"
            )
        print()

    print("=" * len(header))
    print("Per-model, pooled across both modalities:")
    for model in MODEL_ORDER:
        before = all_before.get(model, [])
        after = all_after.get(model, [])
        if not before:
            continue
        n = len(before)
        mc = mcnemar_exact(before, after)
        pcr_before, lo_b, hi_b = bootstrap_ci([1.0 if x else 0.0 for x in before], n_boot=5000, seed=0)
        pcr_after, lo_a, hi_a = bootstrap_ci([1.0 if x else 0.0 for x in after], n_boot=5000, seed=0)
        print(
            f"  {MODEL_LABELS[model]:<22} n={n:>4} "
            f"PCR_before={pcr_before:.3f} [{lo_b:.3f},{hi_b:.3f}]  "
            f"PCR_after={pcr_after:.3f} [{lo_a:.3f},{hi_a:.3f}]  "
            f"b={mc['b_regressions']} c={mc['c_fixes']} p={mc['p_value']:.2e}"
        )

    print("\nLegend: b_regr = before-consistent/after-inconsistent (CGSV broke it);")
    print("c_fix = before-inconsistent/after-consistent (CGSV fixed it); residual = still")
    print("inconsistent after K rounds. p_value = exact two-sided McNemar on b vs c.")


if __name__ == "__main__":
    main()
