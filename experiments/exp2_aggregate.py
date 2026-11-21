"""
exp2_aggregate.py
==================
Aggregate experiments/exp2_results.jsonl into the final Table 1: PCR with
bootstrap 95% CI per (model, modality) cell, pooling all 3 seeds' items
together (matching the runbook's "PCR + rho_t ... with bootstrap 95% CIs
and S seeds" spec -- the seeds increase N for one bootstrap estimate, they
are not averaged as 3 separate point estimates).

Run: python3 experiments/exp2_aggregate.py
     (original 4-model sweep, experiments/exp2_results.jsonl)

Final 9-model manuscript Table 1 (Panther re-run + GPT-5.6-Sol addendum):
     python3 experiments/exp2_aggregate.py --results \
         experiments/exp2_results_panther.jsonl \
         experiments/exp2_dft_results_panther_20260805.jsonl \
         experiments/exp2_gpt56sol_geometric.jsonl \
         experiments/exp2_gpt56sol_dft.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import bootstrap_ci  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp2_results.jsonl")

MODEL_ORDER = ["local", "gemini", "gpt4o", "claude",
               "opus46", "gpt56", "gpt56sol", "qwen3vl", "qwen3vl_thinking"]
MODEL_LABELS = {
    "local": "Qwen2.5-VL-7B",
    "gemini": "Gemini 2.5 Flash Lite",
    "gpt4o": "GPT-4o",
    "claude": "Claude Sonnet 4.5",
    "opus46": "Claude Opus 4.6",
    "gpt56": "GPT-5.6-Terra",
    "gpt56sol": "GPT-5.6-Sol",
    "qwen3vl": "Qwen3-VL-8B-Instruct",
    "qwen3vl_thinking": "Qwen3-VL-8B-Thinking",
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", default=[RESULTS_PATH],
                    help="one or more exp2-style .jsonl files, pooled together")
    args = ap.parse_args()

    cells = defaultdict(list)  # (model, modality) -> list of 0/1 consistent
    n_records = 0
    for path in args.results:
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if not final_oracle.keep(r):
                    continue
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

    # Manuscript Table 1 column groups: Diffraction / Microscopy / Spectra / DFT (pooled) / All
    print("\nTable 1 layout (PCR, pooled over seeds; DFT = stability+metallicity+magnetism):")
    print(f"  {'Model':<22} {'Diffr.':>7} {'Micro.':>7} {'Spectra':>7} {'DFT':>7} {'All':>7}")
    for model in MODEL_ORDER:
        if not per_model_all.get(model):
            continue
        row = []
        for group in (["xrd"], ["sem"], ["spectrum"], sorted(DFT_MODALITIES)):
            vals = [v for m in group for v in cells.get((model, m), [])]
            row.append(f"{sum(vals) / len(vals):>7.3f}" if vals else f"{'-':>7}")
        allv = per_model_all[model]
        row.append(f"{sum(allv) / len(allv):>7.3f}")
        print(f"  {MODEL_LABELS[model]:<22} " + " ".join(row))

    print("\n* DFT-grounded modality (stability/metallicity/magnetism): reference values from")
    print("  Materials Project, NOT YET independently validated by the domain co-author.")
    print("  Report as provisional per CLAUDE.md's OVERRIDE note.")


if __name__ == "__main__":
    main()
