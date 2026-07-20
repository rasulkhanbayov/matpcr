"""
halfB_report_dft.py
=====================
Build one self-contained HTML review page per DFT claim type
(stability/metallicity/magnetism) from
experiments/halfB_dft_fired_cases.jsonl (produced by halfB_collect_dft.py).

Same review pattern as halfB_report.py, adapted for the text-only DFT
modality: no image, shows the chemical formula, the model's claim, the real
Materials Project reference values, and the full reasoning chain. A
reviewer marks each case REAL VIOLATION or FALSE POSITIVE via radio buttons;
a running tally and an "Export My Review" button dump the marks as JSON.

Run: python3 experiments/halfB_report_dft.py
Output: experiments/halfB_review_dft_<claim_type>.html
"""

from __future__ import annotations

import html
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRED_CASES_PATH = os.path.join(REPO_ROOT, "experiments", "halfB_dft_fired_cases.jsonl")
OUT_DIR = os.path.join(REPO_ROOT, "experiments")


def load_fired_cases():
    by_claim_type = {}
    with open(FIRED_CASES_PATH) as f:
        for line in f:
            r = json.loads(line)
            if not r.get("fired"):
                continue
            by_claim_type.setdefault(r["claim_type"], []).append(r)
    return by_claim_type


def render_case_html(idx: int, case: dict) -> str:
    chain_escaped = html.escape(case["chain_text"])
    ref = case["reference"]
    claim = case["parsed"]

    if case["claim_type"] == "stability":
        near_hull_note = (
            " (near-hull/potentially metastable, per M.K.'s review -- not strictly 'stable')"
            if 0 < ref["energy_above_hull"] <= 0.05 else ""
        )
        note = (
            f"Stability oracle: consistent iff (claimed=='STABLE') == (energy_above_hull &lt;= 0.05 eV/atom). "
            f"Real energy_above_hull = {ref['energy_above_hull']:.4f} eV/atom{near_hull_note} "
            f"(Materials Project's own is_stable flag: {ref['is_stable']} -- note this can differ from the "
            f"oracle's 0.05 eV/atom rule; see CLAUDE.md definition-mismatch note). "
            f"Model claimed: {claim}."
        )
    elif case["claim_type"] == "metallicity":
        note = (
            f"Metallicity oracle: consistent iff (claimed=='METALLIC') == (band_gap &lt;= 0.05 eV), for "
            f"band_gap outside the 0.05-0.20 eV abstention band (M.K.'s review; ambiguous-band materials "
            f"are excluded from collection entirely, so every case shown here is clearly gapped or "
            f"clearly gapless). Real band_gap = {ref['band_gap']:.4f} eV "
            f"(Materials Project is_metal flag: {ref['is_metal']}). Model claimed: {claim}."
        )
    else:  # magnetism
        classification = claim.get("classification") if isinstance(claim, dict) else claim
        magnitude = claim.get("magnitude_muB_per_atom") if isinstance(claim, dict) else None
        n_atoms = ref.get("nsites")
        ref_per_atom = abs(ref["total_magnetization"]) / n_atoms if n_atoms else float("nan")
        note = (
            f"Magnetism-magnitude oracle (M.K.'s redesign, 2026-07): classification is decided by "
            f"|total_magnetization|/atom vs. a 0.05 muB/atom threshold; magnitude (never sign) is then "
            f"compared only for magnetic materials, within an order-of-magnitude band. "
            f"Real |total_magnetization| = {abs(ref['total_magnetization']):.6f} muB over {n_atoms} atoms "
            f"= {ref_per_atom:.4f} muB/atom. Model classified: {classification}"
            + (f", claimed magnitude {magnitude} muB/atom." if magnitude is not None else " (no magnitude claim; classification-only).")
        )

    return f"""
    <div class="case" id="case-{idx}">
      <div class="case-header">
        <span class="case-num">Case #{idx + 1}</span>
        <span class="model-badge">{html.escape(case['model'])}</span>
        <span class="source">{html.escape(case['material_id'])} — {html.escape(case['formula'])}</span>
      </div>
      <div class="case-body">
        <div class="case-details" style="flex: 1;">
          <table>
            <tr><th>Formula</th><td class="claim">{html.escape(case['formula'])}</td></tr>
            <tr><th>Model's claim</th><td class="claim">{html.escape(str(claim))}</td></tr>
            <tr><th>Oracle verdict</th><td class="verdict-fired">INCONSISTENT (fired)</td></tr>
            <tr><th>Reference values</th><td>hull={ref['energy_above_hull']:.4f} eV/atom,
                is_stable={ref['is_stable']}, band_gap={ref['band_gap']:.4f} eV,
                is_metal={ref['is_metal']}, total_magnetization={ref['total_magnetization']:.6f} muB,
                nsites={ref.get('nsites')}</td></tr>
            <tr><th>Claim-type note</th><td>{note}</td></tr>
          </table>
          <details open>
            <summary>Full reasoning chain</summary>
            <pre class="chain">{chain_escaped}</pre>
          </details>
          <div class="review-controls">
            <label class="review-label">Your review:</label>
            <label><input type="radio" name="review-{idx}" value="real" onchange="updateTally()"> Real violation (oracle correct)</label>
            <label><input type="radio" name="review-{idx}" value="false_positive" onchange="updateTally()"> False positive (oracle wrong)</label>
            <label><input type="radio" name="review-{idx}" value="unsure" onchange="updateTally()"> Unsure / needs discussion</label>
          </div>
        </div>
      </div>
    </div>
    """


PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Half-B Review — DFT {claim_type} oracle</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px;
         background: #fafafa; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; }}
  .summary {{ position: sticky; top: 0; background: white; padding: 12px 16px; border-radius: 8px;
              box-shadow: 0 1px 4px rgba(0,0,0,0.15); margin-bottom: 20px; z-index: 10; }}
  .summary strong {{ font-size: 1.1rem; }}
  .case {{ background: white; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
           overflow: hidden; }}
  .case-header {{ background: #f0f0f0; padding: 8px 16px; display: flex; gap: 12px; align-items: center;
                   font-size: 0.85rem; }}
  .case-num {{ font-weight: 600; }}
  .model-badge {{ background: #333; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  .source {{ color: #666; font-family: monospace; font-size: 0.75rem; }}
  .case-body {{ display: flex; gap: 16px; padding: 16px; flex-wrap: wrap; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
  th {{ text-align: left; padding: 4px 8px; color: #555; font-size: 0.85rem; white-space: nowrap; vertical-align: top; }}
  td {{ padding: 4px 8px; font-size: 0.85rem; }}
  .claim {{ font-weight: 600; }}
  .verdict-fired {{ color: #c0392b; font-weight: 600; }}
  .chain {{ background: #f7f7f7; padding: 10px; border-radius: 4px; font-size: 0.8rem;
            white-space: pre-wrap; max-height: 300px; overflow-y: auto; }}
  .review-controls {{ margin-top: 10px; padding: 10px; background: #fff8e1; border-radius: 4px; }}
  .review-label {{ font-weight: 600; display: block; margin-bottom: 6px; }}
  .review-controls label {{ display: inline-block; margin-right: 16px; font-size: 0.85rem; cursor: pointer; }}
  button {{ background: #2980b9; color: white; border: none; padding: 8px 16px; border-radius: 4px;
            cursor: pointer; font-size: 0.9rem; }}
  button:hover {{ background: #2471a3; }}
  #export-output {{ width: 100%; height: 100px; margin-top: 10px; font-family: monospace; font-size: 0.75rem; }}
</style>
</head>
<body>
<h1>Half-B Precision Review — DFT {claim_type} oracle ({n_cases} fired cases)</h1>
<p style="color:#666; font-size:0.85rem;">Note: Materials Project is an APPROVED standardized
computational reference for this oracle (domain co-author M.K.'s review, 2026-07, conditional
on the oracle corrections now implemented -- metallicity abstention band, magnetism
classify-then-magnitude redesign, stability near-hull framing). These are computational
references, not experimental ground truth. This review pass supersedes the prior PI-override
pass (which used the OLD, uncorrected oracle logic) -- do not merge or compare precision
numbers across the two passes.</p>
<div class="summary">
  <strong id="tally">Reviewed: 0 / {n_cases}</strong>
  &nbsp;|&nbsp; Real: <span id="tally-real">0</span>
  &nbsp;|&nbsp; False positive: <span id="tally-fp">0</span>
  &nbsp;|&nbsp; Unsure: <span id="tally-unsure">0</span>
  &nbsp;|&nbsp; <strong>Precision so far: <span id="tally-precision">--</span></strong>
  <br><br>
  <button onclick="exportReview()">Export My Review</button>
  <textarea id="export-output" placeholder="Click Export to generate a JSON summary here — copy it out and send it back for the record." readonly></textarea>
</div>
{cases_html}
<script>
function updateTally() {{
  let real = 0, fp = 0, unsure = 0;
  const total = {n_cases};
  for (let i = 0; i < total; i++) {{
    const radios = document.getElementsByName('review-' + i);
    for (const r of radios) {{
      if (r.checked) {{
        if (r.value === 'real') real++;
        else if (r.value === 'false_positive') fp++;
        else if (r.value === 'unsure') unsure++;
      }}
    }}
  }}
  const reviewed = real + fp + unsure;
  document.getElementById('tally').textContent = 'Reviewed: ' + reviewed + ' / ' + total;
  document.getElementById('tally-real').textContent = real;
  document.getElementById('tally-fp').textContent = fp;
  document.getElementById('tally-unsure').textContent = unsure;
  const judged = real + fp;
  const precision = judged > 0 ? (100 * real / judged).toFixed(1) + '%' : '--';
  document.getElementById('tally-precision').textContent = precision;
}}
function exportReview() {{
  const total = {n_cases};
  const results = [];
  for (let i = 0; i < total; i++) {{
    const radios = document.getElementsByName('review-' + i);
    let value = null;
    for (const r of radios) {{ if (r.checked) value = r.value; }}
    results.push({{case: i + 1, verdict: value}});
  }}
  document.getElementById('export-output').value = JSON.stringify({{claim_type: "{claim_type}", reviews: results}}, null, 2);
}}
</script>
</body>
</html>
"""


def main():
    by_claim_type = load_fired_cases()
    for claim_type, cases in by_claim_type.items():
        cases_html = "\n".join(render_case_html(i, c) for i, c in enumerate(cases))
        page = PAGE_TEMPLATE.format(claim_type=claim_type, n_cases=len(cases), cases_html=cases_html)
        out_path = os.path.join(OUT_DIR, f"halfB_review_dft_{claim_type}.html")
        with open(out_path, "w") as f:
            f.write(page)
        print(f"{claim_type}: {len(cases)} cases -> {out_path} ({os.path.getsize(out_path)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
