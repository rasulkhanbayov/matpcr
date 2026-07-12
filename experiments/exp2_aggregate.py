"""
exp2_aggregate.py
==================
Aggregate experiments/exp2_results.jsonl into the final Table 1: PCR with
bootstrap 95% CI per (model, modality) cell, pooling all 3 seeds' items
together (matching the runbook's "PCR + rho_t ... with bootstrap 95% CIs
and S seeds" spec -- the seeds increase N for one bootstrap estimate, they
are not averaged as 3 separate point estimates).

Run: python3 experiments/exp2_aggregate.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import bootstrap_ci  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp2_results.jsonl")

MODEL_ORDER = ["local", "gemini", "gpt4o", "claude"]
MODEL_LABELS = {
    "local": "Qwen2.5-VL-7B",
    "gemini": "Gemini 2.5 Flash Lite",
    "gpt4o": "GPT-4o",
    "claude": "Claude Sonnet 4.5",
}
MODALITY_ORDER = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]
MODALITY_LABELS = {
    "xrd": "Diffraction (XRD)",
    "sem": "Microscopy (SEM)",
    "spectrum": "Spectra (Raman)",
    "stability": "Stability",
    "metallicity": "Metallicity",
    "magnetism": "Sign/magnitude (magnetism)",
}
DFT_MODALITIES = {"stability", "metallicity", "magnetism"}


def main():
    cells = defaultdict(list)  # (model, modality) -> list of 0/1 consistent
    n_records = 0
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            cells[(r["model"], r["modality"])].append(1.0 if r["consistent"] else 0.0)
            n_records += 1

    print(f"Total checkable records aggregated: {n_records}\n")

    # Per-cell table
    print(f"{'Model':<22} {'Modality':<28} {'n':>5} {'PCR':>8} {'95% CI':>20}")
    print("-" * 90)
    per_model_all = defaultdict(list)
    per_modality_all = defaultdict(list)
    for modality in MODALITY_ORDER:
        for model in MODEL_ORDER:
            vals = cells.get((model, modality), [])
            if not vals:
                continue
            pcr, lo, hi = bootstrap_ci(vals, n_boot=5000, seed=0)
            per_model_all[model].extend(vals)
            per_modality_all[modality].extend(vals)
            dft_flag = " *" if modality in DFT_MODALITIES else ""
            print(
                f"{MODEL_LABELS[model]:<22} {MODALITY_LABELS[modality]:<28} {len(vals):>5} "
                f"{pcr:>8.4f} [{lo:.4f}, {hi:.4f}]{dft_flag}"
            )
        print()

    # Overall per-model (All column)
    print("=" * 90)
    print("Overall per model (all modalities pooled):")
    for model in MODEL_ORDER:
        vals = per_model_all.get(model, [])
        if not vals:
            continue
        pcr, lo, hi = bootstrap_ci(vals, n_boot=5000, seed=0)
        print(f"  {MODEL_LABELS[model]:<22} n={len(vals):>5} PCR={pcr:.4f} [{lo:.4f}, {hi:.4f}]")

    print("\n* DFT-grounded modality (stability/metallicity/magnetism): reference values from")
    print("  Materials Project, NOT YET independently validated by the domain co-author.")
    print("  Report as provisional per CLAUDE.md's OVERRIDE note.")


if __name__ == "__main__":
    main()
