"""
exp15_multiplicity_correction.py
==================================
Applies Holm-Bonferroni and Benjamini-Hochberg multiple-comparisons
correction to the family of significance tests reported in Table 2
(matpcr_snjnl.tex, tab:cgsv): the 4 per-model CGSV McNemar tests plus the
2 mechanism-isolation control tests (self-refinement, generic re-prompting)
-- exactly the family the manuscript's own Statistics paragraph (Methods)
flags as "not yet corrected for multiple comparisons" (a standing item from
the supervisor audit, matpcr_REDFLAGS.txt BL1/EX10).

Does NOT include the 144 (model, constraint-type, seed) PCR sweep cells --
those are bootstrap-CI point estimates, not hypothesis tests with p-values,
so a Holm/BH correction (designed for families of significance tests) does
not apply to them the same way. This script corrects the actual p-value
family: Table 2's 6 McNemar tests.

Reuses matpcr_metrics.mcnemar_exact (recomputed directly from raw
before/after records, not hardcoded from the manuscript's printed values)
and the new matpcr_metrics.holm_bonferroni / benjamini_hochberg functions.

Run: python3 experiments/exp15_multiplicity_correction.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import mcnemar_exact, holm_bonferroni, benjamini_hochberg  # noqa: E402

EXP4_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp4_results.jsonl")
EXP7_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp7_results.jsonl")

MODEL_ORDER = ["local", "gemini", "gpt4o", "claude"]
MODEL_LABELS = {
    "local": "Qwen2.5-VL-7B",
    "gemini": "Gemini 2.5 Flash Lite",
    "gpt4o": "GPT-4o",
    "claude": "Claude Sonnet 4.5",
}


def main():
    # --- 4 CGSV per-model tests, pooled across both modalities (xrd+spectrum) ---
    cgsv_before, cgsv_after = defaultdict(list), defaultdict(list)
    with open(EXP4_PATH) as f:
        for line in f:
            r = json.loads(line)
            cgsv_before[r["model"]].append(r["before_consistent"])
            cgsv_after[r["model"]].append(r["after_consistent"])

    tests = []  # (label, b, c, p)
    for model in MODEL_ORDER:
        mc = mcnemar_exact(cgsv_before[model], cgsv_after[model])
        tests.append((f"{MODEL_LABELS[model]} (CGSV)", mc["b_regressions"], mc["c_fixes"], mc["p_value"]))

    # --- 2 mechanism-isolation controls, pooled across both models and modalities ---
    control_before, control_after = defaultdict(list), defaultdict(list)
    with open(EXP7_PATH) as f:
        for line in f:
            r = json.loads(line)
            if r["control"] not in ("self_refine", "re_prompt"):
                continue
            control_before[r["control"]].append(r["before_consistent"])
            control_after[r["control"]].append(r["after_consistent"])

    for control, label in [("self_refine", "Self-refinement (control)"), ("re_prompt", "Generic re-prompting (control)")]:
        mc = mcnemar_exact(control_before[control], control_after[control])
        tests.append((label, mc["b_regressions"], mc["c_fixes"], mc["p_value"]))

    labels = [t[0] for t in tests]
    raw_p = [t[3] for t in tests]
    holm_adj = holm_bonferroni(raw_p)
    bh_adj = benjamini_hochberg(raw_p)

    print(f"Multiple-comparisons correction over the {len(tests)}-test family "
          f"(4 CGSV + 2 controls, Table 2):\n")
    header = f"{'Test':<32} {'b':>4} {'c':>5} {'raw p':>12} {'Holm-adj':>12} {'sig@.05':>8}   {'BH-adj':>12} {'sig@.05':>8}"
    print(header)
    print("-" * len(header))
    alpha = 0.05
    for (label, b, c, p), h, bh in zip(tests, holm_adj, bh_adj):
        print(f"{label:<32} {b:>4} {c:>5} {p:>12.3e} {h:>12.3e} "
              f"{'yes' if h < alpha else 'no':>8}   {bh:>12.3e} {'yes' if bh < alpha else 'no':>8}")

    print("\nConclusion: ", end="")
    all_cgsv_survive_holm = all(h < alpha for (label, *_), h in zip(tests[:4], holm_adj[:4]))
    controls_stay_ns = all(h >= alpha for (label, *_), h in zip(tests[4:], holm_adj[4:]))
    if all_cgsv_survive_holm and controls_stay_ns:
        print("all 4 CGSV effects survive the strictest (Holm) correction; both "
              "negative controls remain non-significant either way. The qualitative "
              "finding (CGSV works, generic self-refinement/re-prompting do not) is "
              "robust to multiple-comparisons correction.")
    else:
        print("NOT all effects survive correction -- re-check before reporting.")


if __name__ == "__main__":
    main()
