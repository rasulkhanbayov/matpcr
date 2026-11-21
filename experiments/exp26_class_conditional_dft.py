"""
exp26_class_conditional_dft.py
==============================
KBS revision R1 (Reviewer 1 M4): the DFT samples are class-imbalanced (few near-hull
structures, more magnetic than non-magnetic, etc.), so a pooled PCR can reflect the
sampled base rate rather than discrimination. For each DFT constraint type and model,
report PCR within each reference class and the class-balanced PCR (mean of the two
per-class rates), alongside the pooled PCR of Table 1.

Reference classes (the oracle's own definitions):
  stability   near-hull (E_hull <= 0.05 eV/atom)  vs  above hull
  metallicity computed gap <= 0.05 eV            vs  gap >= 0.20 eV   (0.05-0.20 abstain)
  magnetism   |M|/atom >= 0.05 muB               vs  below

Run: MATPCR_DATA_ROOT=... python experiments/exp26_class_conditional_dft.py
Writes: experiments/exp26_results.json
"""

from __future__ import annotations

import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(os.path.dirname(HERE), "data"))
FILES = ["exp2_dft_results_panther_20260805.jsonl", "exp2_gpt56sol_dft.jsonl"]
MODELS = ["local", "gemini", "gpt4o", "claude", "opus46", "gpt56", "gpt56sol", "qwen3vl", "qwen3vl_thinking"]
LABEL = {"local": "Qwen2.5-VL-7B", "gemini": "Gemini 2.5 Flash Lite", "gpt4o": "GPT-4o",
         "claude": "Claude Sonnet 4.5", "opus46": "Claude Opus 4.6", "gpt56": "GPT-5.6-Terra",
         "gpt56sol": "GPT-5.6-Sol", "qwen3vl": "Qwen3-VL-8B-Instruct", "qwen3vl_thinking": "Qwen3-VL-8B-Thinking"}
CLASSES = {
    # final protocol: near-hull band excluded, so the positive class is "on the hull"
    "stability": ("on-hull", "above-hull", lambda m: m["energy_above_hull"] <= 0.05),
    "metallicity": ("gap<=0.05", "gap>=0.20", lambda m: m["band_gap"] <= 0.05),
    "magnetism": ("magnetic", "non-magnetic",
                  lambda m: abs(m["total_magnetization"]) / max(m["nsites"], 1) >= 0.05),
}


def main():
    mp = {json.loads(l)["material_id"]: json.loads(l)
          for l in open(os.path.join(DATA_ROOT, "mp_data", "mp_reference_batch.jsonl"))}
    cell = defaultdict(lambda: defaultdict(list))
    for f in FILES:
        for l in open(os.path.join(HERE, f)):
            r = json.loads(l)
            if not final_oracle.keep(r):
                continue
            pos_name, neg_name, is_pos = CLASSES[r["modality"]]
            cls = pos_name if is_pos(mp[r["source_id"]]) else neg_name
            cell[(r["model"], r["modality"])][cls].append(bool(r["consistent"]))

    out = {}
    for mod, (pn, nn, _) in CLASSES.items():
        print(f"\n=== {mod}: PCR by reference class ({pn} / {nn}) ===")
        print(f"{'model':<24}{'n_'+pn:>14}{'PCR':>7}{'n_'+nn:>16}{'PCR':>7}{'pooled':>8}{'balanced':>10}")
        for m in MODELS:
            c = cell[(m, mod)]
            a, b = c.get(pn, []), c.get(nn, [])
            pa = sum(a) / len(a) if a else float("nan")
            pb = sum(b) / len(b) if b else float("nan")
            pooled = (sum(a) + sum(b)) / (len(a) + len(b))
            bal = (pa + pb) / 2
            out[f"{m}|{mod}"] = dict(n_pos=len(a), pcr_pos=pa, n_neg=len(b), pcr_neg=pb, pooled=pooled, balanced=bal)
            print(f"{LABEL[m]:<24}{len(a):>14}{pa:>7.3f}{len(b):>16}{pb:>7.3f}{pooled:>8.3f}{bal:>10.3f}")
    json.dump(out, open(os.path.join(HERE, "exp26_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
