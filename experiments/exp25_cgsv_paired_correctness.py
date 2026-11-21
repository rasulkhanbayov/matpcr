"""
exp25_cgsv_paired_correctness.py
================================
KBS revision R1 (Reviewer 1 M3): what do CGSV revisions actually achieve?
The submitted paper compared final-round accuracy (exp16) with PCR. This script
measures PAIRED changes in correctness on the same items, before vs after CGSV,
using the identical non-circular accuracy criteria as the accuracy-versus-
consistency analysis (exp3/exp16):
  diffraction: claim within 0.1 deg of the nearest pymatgen reference reflection
  spectra:     claim within 2 cm^-1 of the nearest detected local maximum
                (scipy find_peaks, prominence 0.05 of the normalized range, distance 5)

Per item: first-round claim (before) and final-round claim (after) from
exp4_results.jsonl (claimed_values[0], claimed_values[-1]).
Reports, per constraint type and model:
  * accuracy before / after and the exact McNemar test on the paired correctness change
  * among revised items (oracle fired at round 1): outcome classes
      corrected  : after consistent and accurate
      admissible : after consistent but not accurate (moved to an oracle-admissible value)
      unresolved : after still inconsistent
  * distance to the true value before vs after (median), and the share of revised items
    whose claim moved closer to the true value

Note on b = 0: Algorithm 1 stops at the first consistent round, so an item that is
consistent at round 1 is never revised; zero regressions in consistency is therefore
a property of the loop, not an empirical finding. Correctness, which the loop does
not see, CAN regress, and that is what this script tests.

Run: MATPCR_DATA_ROOT=... python experiments/exp25_cgsv_paired_correctness.py [--modalities xrd spectrum]
Writes: experiments/exp25_results.json (merged per modality)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
from scipy.signal import find_peaks

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from halfB_collect import spectrum_signal, xrd_reference_peaks  # noqa: E402
from matpcr_metrics import mcnemar_exact  # noqa: E402

DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(os.path.dirname(HERE), "data"))
EXP4 = os.path.join(HERE, "exp4_results.jsonl")
OUT = os.path.join(HERE, "exp25_results.json")
TOL = {"xrd": 0.1, "spectrum": 2.0}
LABEL = {"local": "Qwen2.5-VL-7B", "gemini": "Gemini 2.5 Flash Lite", "gpt4o": "GPT-4o",
         "claude": "Claude Sonnet 4.5"}


def resolve(p: str) -> str:
    if "/opxrd/" in p:
        return os.path.join(DATA_ROOT, "opxrd", p.split("/opxrd/")[-1])
    if "/rruff/" in p:
        return os.path.join(DATA_ROOT, "rruff", p.split("/rruff/")[-1])
    return p


def truth_points(mod: str, path: str):
    if mod == "xrd":
        ref = xrd_reference_peaks(path)
        return np.asarray(ref, float) if ref else None
    sig = spectrum_signal(path)
    if sig is None:
        return None
    xs, ys = sig
    rng = ys.max() - ys.min()
    if rng <= 0:
        return None
    idx, _ = find_peaks((ys - ys.min()) / rng, prominence=0.05, distance=5)
    return xs[idx] if idx.size else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modalities", nargs="+", default=["xrd", "spectrum"])
    args = ap.parse_args()
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    recs = [json.loads(l) for l in open(EXP4)]

    for mod in args.modalities:
        rows, skipped = [], 0
        cache = {}
        for r in recs:
            if r["modality"] != mod or not r["claimed_values"]:
                continue
            path = resolve(r["source_file"])
            if path not in cache:
                cache[path] = truth_points(mod, path) if os.path.exists(path) else None
            pts = cache[path]
            if pts is None or len(pts) == 0:
                skipped += 1
                continue
            before, after = r["claimed_values"][0], r["claimed_values"][-1]
            d0 = float(np.min(np.abs(pts - before)))
            d1 = float(np.min(np.abs(pts - after)))
            rows.append(dict(model=r["model"], revised=r["rounds_used"] > 0,
                             before_consistent=r["before_consistent"], after_consistent=r["after_consistent"],
                             acc_before=d0 <= TOL[mod], acc_after=d1 <= TOL[mod], dist_before=d0, dist_after=d1))

        def summarize(rs):
            n = len(rs)
            mc = mcnemar_exact([x["acc_before"] for x in rs], [x["acc_after"] for x in rs])
            rev = [x for x in rs if x["revised"]]
            cls = defaultdict(int)
            for x in rev:
                if not x["after_consistent"]:
                    cls["unresolved"] += 1
                elif x["acc_after"]:
                    cls["corrected"] += 1
                else:
                    cls["admissible"] += 1
            closer = sum(1 for x in rev if x["dist_after"] < x["dist_before"])
            farther = sum(1 for x in rev if x["dist_after"] > x["dist_before"])
            return dict(n=n, acc_before=sum(x["acc_before"] for x in rs) / n,
                        acc_after=sum(x["acc_after"] for x in rs) / n,
                        pcr_before=sum(x["before_consistent"] for x in rs) / n,
                        pcr_after=sum(x["after_consistent"] for x in rs) / n,
                        acc_lost=mc["b_regressions"], acc_gained=mc["c_fixes"], mcnemar_p=mc["p_value"],
                        n_revised=len(rev), revised_corrected=cls["corrected"],
                        revised_admissible=cls["admissible"], revised_unresolved=cls["unresolved"],
                        revised_moved_closer=closer, revised_moved_farther=farther,
                        median_dist_before_revised=float(np.median([x["dist_before"] for x in rev])) if rev else None,
                        median_dist_after_revised=float(np.median([x["dist_after"] for x in rev])) if rev else None)

        res = {"pooled": summarize(rows), "skipped": skipped}
        for m in LABEL:
            sub = [x for x in rows if x["model"] == m]
            if sub:
                res[m] = summarize(sub)
        out[mod] = res
        print(f"\n=== {mod}: n={len(rows)} (skipped {skipped} without a resolvable reference)")
        print(f"{'model':<22}{'n':>5}{'acc0':>7}{'acc1':>7}{'lost':>6}{'gain':>6}{'p':>9}"
              f"{'rev':>5}{'corr':>6}{'admis':>7}{'unres':>7}{'closer':>8}{'farther':>8}")
        for k in ["pooled"] + list(LABEL):
            if k not in res:
                continue
            s = res[k]
            print(f"{(LABEL.get(k, k)):<22}{s['n']:>5}{s['acc_before']:>7.3f}{s['acc_after']:>7.3f}"
                  f"{s['acc_lost']:>6}{s['acc_gained']:>6}{s['mcnemar_p']:>9.2g}{s['n_revised']:>5}"
                  f"{s['revised_corrected']:>6}{s['revised_admissible']:>7}{s['revised_unresolved']:>7}"
                  f"{s['revised_moved_closer']:>8}{s['revised_moved_farther']:>8}")
        json.dump(out, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
