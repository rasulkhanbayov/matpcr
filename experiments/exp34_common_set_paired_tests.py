"""
exp34_common_set_paired_tests.py
================================
KBS revision R1 (Reviewer 2 W4): paired model comparisons on the common, class-balanced DFT item
set of exp29 (every model answered the same 90 materials per DFT constraint type).

For every model pair: PCR difference on the materials both answered checkably, pooled over the
three DFT types and per type, exact McNemar p, Holm correction across all pairs (pooled family and
each per-type family), bootstrap 95% CI of the difference (paired resampling, B=10,000) and MDE80.
Also reports the four comparisons stated in the Article that can be formed on this set.

Run: python experiments/exp34_common_set_paired_tests.py
Writes: experiments/exp34_results.json
"""

from __future__ import annotations

import itertools
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from matpcr_metrics import holm_bonferroni, mcnemar_exact  # noqa: E402

LABEL = {"local": "Qwen2.5-VL-7B", "gemini": "Gemini 2.5 Flash Lite", "gpt4o": "GPT-4o",
         "claude": "Claude Sonnet 4.5", "opus46": "Claude Opus 4.6", "gpt56": "GPT-5.6-Terra",
         "gpt56sol": "GPT-5.6-Sol", "qwen3vl": "Qwen3-VL-8B-Instruct"}
TYPES = ["stability", "metallicity", "magnetism"]
Z = 1.959964 + 0.841621


def load():
    d = defaultdict(dict)
    for f in ["exp29_results.jsonl", "exp29_results_local.jsonl"]:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            for l in open(p):
                r = json.loads(l)
                if not final_oracle.keep(r):
                    continue
                if r["checkable"]:
                    d[r["model"]][(r["modality"], r["source_id"])] = bool(r["consistent"])
    # include a model only if it covers (almost) the full set (a run may still be in progress)
    full = max(len(v) for v in d.values())
    return {m: v for m, v in d.items() if len(v) >= 0.95 * full}


def compare(d, a, b, types, rng):
    keys = sorted(k for k in set(d[a]) & set(d[b]) if k[0] in types)
    xa = np.array([d[a][k] for k in keys], float)
    xb = np.array([d[b][k] for k in keys], float)
    mc = mcnemar_exact(list(xb.astype(bool)), list(xa.astype(bool)))
    idx = rng.integers(0, len(keys), (10_000, len(keys)))
    boots = xa[idx].mean(1) - xb[idx].mean(1)
    return dict(a=a, b=b, scope="+".join(types), n=len(keys), effect=float(xa.mean() - xb.mean()),
                ci95=[float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                mde80=float(Z * boots.std(ddof=1)), p=float(mc["p_value"]),
                a_only=int(mc["c_fixes"]), b_only=int(mc["b_regressions"]))


def holm(rows):
    for r, q in zip(rows, holm_bonferroni([r["p"] for r in rows])):
        r["p_holm"] = float(q)
    return rows


def main():
    d = load()
    models = [m for m in LABEL if m in d]
    print("models with complete common-set responses:", ", ".join(LABEL[m] for m in models))
    rng = np.random.default_rng(0)
    pooled = holm([compare(d, a, b, TYPES, rng) for a, b in itertools.combinations(models, 2)])
    per = {t: holm([compare(d, a, b, [t], rng) for a, b in itertools.combinations(models, 2)]) for t in TYPES}
    stated = [("gpt56", "gpt4o"), ("opus46", "claude"), ("gpt56sol", "gpt56")]
    stated_rows = holm([compare(d, a, b, TYPES, rng) for a, b in stated if a in d and b in d])
    print("\nComparisons stated in the Article, pooled over the three DFT types (Holm over these):")
    for r in stated_rows:
        print(f"  {LABEL[r['a']]} - {LABEL[r['b']]}: {r['effect']:+.3f} [{r['ci95'][0]:+.3f},{r['ci95'][1]:+.3f}] "
              f"n={r['n']} p={r['p']:.3g} p_Holm={r['p_holm']:.3g} MDE80={r['mde80']:.3f}")
    print(f"\nAll {len(pooled)} pairs pooled: {sum(r['p_holm'] < 0.05 for r in pooled)} significant after Holm; "
          f"MDE80 {min(r['mde80'] for r in pooled):.3f}-{max(r['mde80'] for r in pooled):.3f}")
    for r in sorted(pooled, key=lambda r: r["p"])[:8]:
        print(f"  {LABEL[r['a']]:<22} - {LABEL[r['b']]:<22} {r['effect']:+.3f} p_Holm={r['p_holm']:.3g}")
    for t in TYPES:
        print(f"{t:<12}: {sum(r['p_holm'] < 0.05 for r in per[t])} of {len(per[t])} pairs significant after Holm; "
              f"median MDE80 {np.median([r['mde80'] for r in per[t]]):.3f}")
    json.dump({"models": models, "stated": stated_rows, "pooled_all_pairs": pooled, "per_type_all_pairs": per},
              open(os.path.join(HERE, "exp34_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
