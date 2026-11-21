"""
exp32_second_annotator_pages.py
===============================
KBS revision R1 (Reviewer 2 W3): build blind review pages for a second, independent
annotator on a stratified random subsample of the audited oracle-fired cases.

For each of the six oracle families, 30 cases are drawn with random.Random(20261015) from the
cases the first annotator decided (real or false positive), stratified by the first annotator's
verdict in proportion to its frequency (at least 3 false positives when available, so agreement on
the minority class is estimable). The case blocks are copied verbatim from the original review pages
(same image, chain, oracle verdict and reference values the first annotator saw), WITHOUT the first
annotator's verdicts. Each page exports {"family", "reviews": [{"case": <original case number>,
"verdict": ...}]}, which experiments/exp13_second_reviewer_kappa.py compares with the first export.

Inputs: the six review pages (Hugging Face dataset, review_pages/; or experiments/ after
scripts/download_from_hf.py) and the first annotator's exports in the repo root.
Run: python experiments/exp32_second_annotator_pages.py --pages_dir <dir with halfB_review_*.html> --out_dir <dir>
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FAMILIES = [
    ("xrd", "halfB_review_xrd.html", "xrd.txt"),
    ("sem", "halfB_review_sem.html", "sem.txt"),
    ("spectrum", "halfB_review_spectrum.html", "spectrum_halfB_review_2026-08-06.txt"),
    ("stability", "halfB_review_dft_stability.html", "stability_halfB_review_2026-08-06.txt"),
    ("metallicity", "halfB_review_dft_metallicity.html", "metallicity_halfB_review_2026-08-06.txt"),
    ("magnetism", "halfB_review_dft_magnetism.html", "magnetism_halfB_review_2026-08-06.txt"),
]
N = 30
MIN_FP = 3


def first_verdicts(path):
    txt = open(path).read()
    txt = re.sub(r'("verdict"\s*:\s*)(real|false_positive|unsure)\b', r'\1"\2"', txt)
    return {r["case"]: r["verdict"] for r in json.loads(txt)["reviews"]}


def split_cases(html):
    head, rest = html.split('<div class="case" id="case-0">', 1)
    rest = '<div class="case" id="case-0">' + rest
    blocks = re.split(r'(?=<div class="case" id="case-\d+">)', rest)
    blocks = [b for b in blocks if b.startswith('<div class="case"')]
    tail_i = blocks[-1].find("<script>")
    if tail_i != -1:
        blocks[-1] = blocks[-1][:tail_i]
    style = re.search(r"<style>.*?</style>", head, re.S).group(0)
    return style, blocks


def sample(verdicts, rng):
    real = sorted(c for c, v in verdicts.items() if v == "real")
    fp = sorted(c for c, v in verdicts.items() if v == "false_positive")
    n_fp = min(len(fp), max(MIN_FP, round(N * len(fp) / (len(real) + len(fp)))))
    chosen = rng.sample(fp, n_fp) + rng.sample(real, N - n_fp)
    rng.shuffle(chosen)
    return chosen


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Second-annotator review: {family}</title>{style}</head><body>
<h1>Second-annotator review: {family} oracle ({n} cases)</h1>
<div class="summary">
<p>For each case, decide independently whether the oracle's INCONSISTENT verdict is a genuine physical
violation of the stated constraint (<b>Real</b>), or an oracle/parsing artifact (<b>False positive</b>).
Use <b>Unsure</b> only if you cannot decide. Do not consult the first annotator's labels.</p>
<span id="tally">Reviewed: 0 / {n}</span> &nbsp;
<button onclick="exportReview()">Export my review</button>
<textarea id="export-output" rows="6" style="width:100%"></textarea></div>
{cases}
<script>
const CASES = {case_list};
function updateTally() {{
  let k = 0; for (const c of CASES) {{ for (const r of document.getElementsByName('review-' + c)) if (r.checked) k++; }}
  document.getElementById('tally').textContent = 'Reviewed: ' + k + ' / ' + CASES.length;
}}
function exportReview() {{
  const out = [];
  for (const c of CASES) {{ let v = null; for (const r of document.getElementsByName('review-' + c)) if (r.checked) v = r.value; out.push({{case: c, verdict: v}}); }}
  document.getElementById('export-output').value = JSON.stringify({{family: "{family}", annotator: "second", reviews: out}}, null, 2);
}}
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    rng = random.Random(20261015)
    manifest = {}
    for fam, page, export in FAMILIES:
        verdicts = first_verdicts(os.path.join(REPO, export))
        style, blocks = split_cases(open(os.path.join(args.pages_dir, page)).read())
        assert len(blocks) == len(verdicts), (fam, len(blocks), len(verdicts))
        chosen = sample(verdicts, rng)
        out_blocks = []
        for c in chosen:
            b = blocks[c - 1]
            # radio groups keyed by the ORIGINAL case number, and the tally hook rewired
            b = re.sub(r'name="review-\d+"', f'name="review-{c}"', b)
            out_blocks.append(b)
        html = PAGE.format(family=fam, style=style, n=len(chosen), cases="\n".join(out_blocks),
                           case_list=json.dumps(chosen))
        fn = os.path.join(args.out_dir, f"second_annotator_{fam}.html")
        open(fn, "w").write(html)
        manifest[fam] = {"cases": chosen, "first_annotator_fp_in_sample": sum(verdicts[c] == "false_positive" for c in chosen)}
        print(f"{fam:<12} {len(chosen)} cases ({manifest[fam]['first_annotator_fp_in_sample']} first-annotator FPs) -> {fn}")
    json.dump(manifest, open(os.path.join(args.out_dir, "second_annotator_sample.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
