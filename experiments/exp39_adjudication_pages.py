"""
exp39_adjudication_pages.py
===========================
KBS revision R1 (Reviewer 2 W3): adjudication of the cases on which the two precision-audit
annotators disagree. For each family, every case of the second-annotator subsample with
different labels is shown exactly as both annotators saw it (case block copied verbatim from
the original review page), together with both labels. The annotators decide a consensus label
together and may record a short reason. Export: {"family", "reviews": [{"case", "verdict", "note"}]}
with verdict in real / false_positive.

Run: python experiments/exp39_adjudication_pages.py --pages_dir <dir with halfB_review_*.html> --out_dir <dir>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from exp32_second_annotator_pages import FAMILIES, first_verdicts, split_cases  # noqa: E402

LABEL = {"real": "Real violation", "false_positive": "False positive", "unsure": "Unsure"}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Adjudication: {family}</title>{style}
<style>.labels{{background:#fff7e0;border:1px solid #e0c060;border-radius:6px;padding:6px 10px;margin:8px 16px}}
.note{{width:95%;margin:4px 0}}</style></head><body>
<h1>Adjudication: {family} ({n} disagreements)</h1>
<div class="summary"><p>The two annotators labelled each case below differently. Discuss each case together,
using LABELING_GUIDELINES.md, and choose ONE consensus label. Add a short reason if useful.</p>
<span id="tally">Decided: 0 / {n}</span> &nbsp;<button onclick="exportReview()">Export consensus</button>
<textarea id="export-output" rows="6" style="width:100%"></textarea></div>
{cases}
<script>
const CASES = {case_list};
function updateTally() {{
  let k = 0; for (const c of CASES) {{ for (const r of document.getElementsByName('consensus-' + c)) if (r.checked) k++; }}
  document.getElementById('tally').textContent = 'Decided: ' + k + ' / ' + CASES.length;
}}
function exportReview() {{
  const out = [];
  for (const c of CASES) {{
    let v = null; for (const r of document.getElementsByName('consensus-' + c)) if (r.checked) v = r.value;
    out.push({{case: c, verdict: v, note: document.getElementById('note-' + c).value}});
  }}
  document.getElementById('export-output').value = JSON.stringify({{family: "{family}", stage: "adjudication", reviews: out}}, null, 2);
}}
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()
    hr = os.path.join(REPO, "KBS_revision_R1", "human_review")
    manifest = {}
    for fam, page, export in FAMILIES:
        A = first_verdicts(os.path.join(REPO, export))
        B = first_verdicts(os.path.join(hr, f"second_annotator_{fam}_review.json"))
        dis = sorted(c for c in B if A.get(c) != B[c])
        manifest[fam] = [{"case": c, "annotator_1": A[c], "annotator_2": B[c]} for c in dis]
        if not dis:
            print(f"{fam:<12} 0 disagreements, no page")
            continue
        style, blocks = split_cases(open(os.path.join(args.pages_dir, page)).read())
        out = []
        for c in dis:
            b = blocks[c - 1]
            # replace the original radio controls with consensus controls
            b = re.sub(r'<div class="review-controls">.*?</div>',
                       f'<div class="review-controls"><label class="review-label">Consensus:</label>'
                       f'<label><input type="radio" name="consensus-{c}" value="real" onchange="updateTally()"> Real violation</label>'
                       f'<label><input type="radio" name="consensus-{c}" value="false_positive" onchange="updateTally()"> False positive</label>'
                       f'<input class="note" id="note-{c}" placeholder="reason (optional)"></div>', b, count=1, flags=re.S)
            labels = (f'<div class="labels"><b>Annotator 1:</b> {LABEL[A[c]]} &nbsp;&nbsp; '
                      f'<b>Annotator 2:</b> {LABEL[B[c]]}</div>')
            b = b.replace('<div class="case-body">', labels + '<div class="case-body">', 1)
            out.append(b)
        html = PAGE.format(family=fam, style=style, n=len(dis), cases="\n".join(out), case_list=json.dumps(dis))
        fn = os.path.join(args.out_dir, f"adjudication_{fam}.html")
        open(fn, "w").write(html)
        print(f"{fam:<12} {len(dis)} disagreements -> {fn}")
    json.dump(manifest, open(os.path.join(args.out_dir, "adjudication_cases.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
