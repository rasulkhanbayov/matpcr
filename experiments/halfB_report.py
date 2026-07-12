"""
halfB_report.py
================
Build one self-contained HTML review page per modality from
experiments/halfB_fired_cases.jsonl (produced by halfB_collect.py).

Each page shows every oracle-FIRED case: the image/plot the model saw, its
full reasoning chain, the model's parsed claim, and the oracle's computed
verdict inputs (so the reviewer can check the oracle's arithmetic, not just
trust it). A reviewer marks each case REAL VIOLATION or FALSE POSITIVE via
radio buttons; a running tally and an "Export My Review" button dump the
marks as JSON (paste-back format, since this stays a static HTML file with
no backend) so precision can be computed afterward.

This script does NOT perform the review -- it only prepares the material.
Half-B itself (recording true-violation fraction per family) is human work.

Run: python3 experiments/halfB_report.py
Output: experiments/halfB_review_<modality>.html (one per modality)
"""

from __future__ import annotations

import base64
import html
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRED_CASES_PATH = os.path.join(REPO_ROOT, "experiments", "halfB_fired_cases.jsonl")
OUT_DIR = os.path.join(REPO_ROOT, "experiments")


def load_fired_cases():
    by_modality = {}
    with open(FIRED_CASES_PATH) as f:
        for line in f:
            r = json.loads(line)
            if not r.get("fired"):
                continue
            by_modality.setdefault(r["modality"], []).append(r)
    return by_modality


def image_to_data_uri(path: str, max_width: int = 800, jpeg_quality: int = 82) -> str:
    """Downscale+re-encode before embedding -- raw NFFA-EUROPE JPGs (1024x768
    each) pushed the SEM review page to ~92MB across 105 cases, too heavy to
    load/share comfortably as a static page. The scale bar's info-bar text
    still needs to stay legible for review, so this resizes rather than
    just re-compressing at full resolution."""
    from PIL import Image
    import io

    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=jpeg_quality)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def render_case_html(idx: int, case: dict) -> str:
    img_uri = image_to_data_uri(case["image_path"])
    chain_escaped = html.escape(case["chain_text"])
    parsed = case["parsed"]
    claim_str = f"{parsed['value']} {parsed['unit']}"
    if parsed.get("was_range"):
        claim_str += " (model gave a range; midpoint used)"

    extra_rows = ""
    if case["modality"] == "xrd":
        extra_rows = f"""
        <tr><th>Modality-specific note</th><td>XRD oracle: tol_deg=0.5, reference peaks from
        pymatgen XRDCalculator on the sample's labeled structure (all usable phases). Check
        whether {parsed['value']:.2f} deg is genuinely far from any real Bragg peak, or if it's
        borderline / near the tolerance boundary.</td></tr>
        """
    elif case["modality"] == "sem":
        extra_rows = f"""
        <tr><th>Modality-specific note</th><td>SEM oracle: claim exceeds the field of view
        implied by the image's scale bar. Check the image directly -- does the claimed size
        look implausible for what's shown, or could the scale-bar reading be wrong?</td></tr>
        """
    elif case["modality"] == "spectrum":
        extra_rows = f"""
        <tr><th>Modality-specific note</th><td>Spectrum oracle: no local maximum with enough
        prominence (>=5% of the spectrum's intensity range) was found within 5 cm-1 of
        {parsed['value']:.1f}. Check the plot -- is the claimed position genuinely off-peak,
        or is there a real (if modest) bump the oracle's threshold missed?</td></tr>
        """

    return f"""
    <div class="case" id="case-{idx}">
      <div class="case-header">
        <span class="case-num">Case #{idx + 1}</span>
        <span class="model-badge">{html.escape(case['model'])}</span>
        <span class="source">{html.escape(os.path.basename(case['source_file']))}</span>
      </div>
      <div class="case-body">
        <div class="case-image">
          <img src="{img_uri}" alt="case image" />
        </div>
        <div class="case-details">
          <table>
            <tr><th>Model's claim</th><td class="claim">{html.escape(claim_str)}</td></tr>
            <tr><th>Oracle verdict</th><td class="verdict-fired">INCONSISTENT (fired)</td></tr>
            {extra_rows}
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
<title>Half-B Review — {modality} oracle</title>
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
  .case-image {{ flex: 0 0 320px; }}
  .case-image img {{ max-width: 320px; max-height: 320px; border: 1px solid #ddd; border-radius: 4px; }}
  .case-details {{ flex: 1; min-width: 300px; }}
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
<h1>Half-B Precision Review — {modality} oracle ({n_cases} fired cases)</h1>
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
  document.getElementById('export-output').value = JSON.stringify({{modality: "{modality}", reviews: results}}, null, 2);
}}
</script>
</body>
</html>
"""


def main():
    by_modality = load_fired_cases()
    for modality, cases in by_modality.items():
        cases_html = "\n".join(render_case_html(i, c) for i, c in enumerate(cases))
        page = PAGE_TEMPLATE.format(modality=modality, n_cases=len(cases), cases_html=cases_html)
        out_path = os.path.join(OUT_DIR, f"halfB_review_{modality}.html")
        with open(out_path, "w") as f:
            f.write(page)
        print(f"{modality}: {len(cases)} cases -> {out_path} ({os.path.getsize(out_path)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
