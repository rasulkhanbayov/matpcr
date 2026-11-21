"""
exp30_taxonomy_all_families.py
==============================
KBS revision R1 (Reviewer 2 W2): extend the violation taxonomy (exp10, which covered
diffraction and microscopy only) to the spectrum and three DFT-grounded families,
using the human audits performed under the FINAL oracle definitions
(spectrum n=495, stability n=107, metallicity n=114, magnetism n=115; all dated
2026-08-06). The diffraction/microscopy taxonomy from exp10 is unchanged: those two
oracles were never revised, so their audits already match the final definitions.

Method (identical to exp10): each human-confirmed real violation's chain is labelled
open-ended by Gemini 2.5 Flash Lite, then the free-text labels are merged into 4-8
canonical categories by a second semantic-clustering pass. Case N in a review export
is the Nth fired record of that family in file order (as rendered by
halfB_report.py / halfB_report_dft.py); the script refuses to run if the counts differ.

Run: python experiments/exp30_taxonomy_all_families.py
Writes: experiments/exp30_results.json
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import exp10_violation_taxonomy as tax  # noqa: E402

TEXT_PROMPT = """A language model was asked, from a chemical formula alone, to make a claim about a computed \
materials property ({modality}). A human reviewer has already confirmed that this claim is a REAL inconsistency \
with the Materials Project reference value (not a false positive). Your job is only to classify WHY the reasoning \
went wrong, not whether it is wrong.

MODALITY: {modality}
TASK PROMPT GIVEN TO THE MODEL: {prompt}
MODEL'S FULL REASONING CHAIN: {chain_text}

In 2-5 words, name the SPECIFIC failure mode this reasoning chain shows (e.g. "assumed ionic means insulating", \
"ignored transition-metal moment", "overgeneralized from known analogue", "treated metastable as stable"). Be \
specific and consistent -- if you see the same underlying mistake pattern again, use the SAME short label. End your \
response with EXACTLY one line:
CATEGORY: <your 2-5 word label>
"""

FAMILIES = [
    ("spectrum", "spectrum_halfB_review_2026-08-06.txt", "halfB_fired_cases.jsonl", "modality"),
    ("stability", "stability_halfB_review_2026-08-06.txt", "halfB_dft_fired_cases.jsonl", "claim_type"),
    ("metallicity", "metallicity_halfB_review_2026-08-06.txt", "halfB_dft_fired_cases.jsonl", "claim_type"),
    ("magnetism", "magnetism_halfB_review_2026-08-06.txt", "halfB_dft_fired_cases.jsonl", "claim_type"),
]


def truthy(x):
    return x is True or str(x).lower() == "true"


def load_real(family, review_file, fired_file, key):
    fired = [r for r in map(json.loads, open(os.path.join(HERE, fired_file)))
             if r.get(key) == family and truthy(r.get("fired"))]
    txt = open(os.path.join(REPO_ROOT, review_file)).read()
    txt = re.sub(r'("verdict"\s*:\s*)(real|false_positive|unsure)\b', r'\1"\2"', txt)
    reviews = {r["case"]: r["verdict"] for r in json.loads(txt)["reviews"]}
    if len(reviews) != len(fired):
        raise RuntimeError(f"{family}: {len(reviews)} reviewed cases vs {len(fired)} fired records -- mapping stale")
    real = [dict(fired[i], modality=family, source_file=fired[i].get("source_file") or fired[i].get("material_id")) for i in range(len(fired)) if reviews.get(i + 1) == "real"]
    return real


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", nargs="+", default=[f[0] for f in FAMILIES])
    args = ap.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")
    image_prompt = tax.CATEGORIZE_PROMPT
    out_path = os.path.join(HERE, "exp30_results.json")
    results = json.load(open(out_path)) if os.path.exists(out_path) else {}
    total = 0.0
    for family, review_file, fired_file, key in FAMILIES:
        if family not in args.families:
            continue
        cases = load_real(family, review_file, fired_file, key)
        tax.CATEGORIZE_PROMPT = (image_prompt.replace("(an XRD diffractogram or an SEM micrograph with a scale bar)",
                                                      "(a Raman spectrum)") if family == "spectrum" else TEXT_PROMPT)
        print(f"[{family}] {len(cases)} human-confirmed real violations", flush=True)
        labeled, cost = tax.categorize(cases, api_key)
        mapping, ccost = tax.cluster_labels_semantic(labeled, family, api_key)
        total += cost + (ccost or 0.0)
        taxonomy = tax.build_taxonomy(labeled, mapping)
        results[family] = {"n_violations": len(cases), "n_labeled": len(labeled), "taxonomy": taxonomy}
        for t in taxonomy:
            print(f"    {t['category']}: {t['count']} ({t['frac']:.1%})", flush=True)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
    tax.CATEGORIZE_PROMPT = image_prompt
    print(f"Total API cost: ${total:.4f}")


if __name__ == "__main__":
    main()
