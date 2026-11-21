"""
exp33_oracle_silent_pages.py
============================
KBS revision R1 (Reviewer 1 M2): the positive control measures recovery of INJECTED violations,
not how many genuine violations in real model responses the oracles miss. This script builds
review pages for a human audit of ORACLE-SILENT real responses (the oracle judged the claim
consistent), so the miss rate on real responses can be estimated.

Sampling: for each family, 30 records drawn with random.Random(20261016) from the oracle-silent
records of the Half-B collections (halfB_fired_cases.jsonl for diffraction/microscopy/spectra,
halfB_dft_fired_cases.jsonl for the DFT families), i.e. the same response populations whose
fired cases were audited for precision. Images are regenerated from the source data with the same
rendering as the model saw (exp17 helpers); DFT pages show the formula, claim and Materials
Project reference values.

Each page asks: is the stated quantity a genuine violation of the physical constraint that the
oracle missed? and exports {"family", "reviews": [{"case", "key", "verdict"}]} with verdicts
missed_violation / clean / unsure.

Run:
  python experiments/exp33_oracle_silent_pages.py --sample_only           # list SEM categories needed
  MATPCR_DATA_ROOT=... python experiments/exp33_oracle_silent_pages.py --out_dir <dir>
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
N = 30
SEED = 20261016


def truthy(x):
    return x is True or str(x).lower() == "true"


def load_samples():
    g = [json.loads(l) for l in open(os.path.join(HERE, "halfB_fired_cases.jsonl"))]
    d = [json.loads(l) for l in open(os.path.join(HERE, "halfB_dft_fired_cases.jsonl"))]
    rng = random.Random(SEED)
    out = {}
    for fam in ["xrd", "sem", "spectrum"]:
        pool = [r for r in g if r["modality"] == fam and not truthy(r["fired"]) and truthy(r.get("oracle_consistent"))]
        out[fam] = rng.sample(pool, N)
    for fam in ["stability", "metallicity", "magnetism"]:
        pool = [r for r in d if r["claim_type"] == fam and not truthy(r["fired"]) and truthy(r.get("oracle_consistent"))]
        out[fam] = rng.sample(pool, N)
    return out


GUIDE = {
    "xrd": "The model was asked for the 2-theta position of the STRONGEST peak. The oracle accepted the claim because "
           "it lies within 0.5 deg of a reference Bragg reflection of the labelled structure. Mark MISSED VIOLATION only if "
           "the stated value is physically inadmissible for this pattern (e.g. no real peak exists there in the measured "
           "data, or it is outside the measured range), not merely imprecise or the wrong one of several real peaks.",
    "sem": "The model was asked for the size of the largest visible feature. The oracle accepted the claim because it does "
           "not exceed the field of view implied by the scale bar. Mark MISSED VIOLATION only if the stated size is "
           "physically impossible for what is shown given the scale bar (e.g. off by an order of magnitude through a unit or "
           "scale error) even though it is below the field of view.",
    "spectrum": "The model was asked for the Raman shift of the strongest peak. The oracle accepted the claim because a "
                "genuine local maximum of sufficient prominence lies within 5 cm-1. Mark MISSED VIOLATION only if no real "
                "peak exists at the stated position in the plotted spectrum (e.g. a noise wiggle or baseline), not merely "
                "if a different peak is stronger.",
    "stability": "The oracle accepted the STABLE/UNSTABLE claim because it agrees with the Materials Project hull energy "
                 "at the 0.05 eV/atom near-hull threshold. Mark MISSED VIOLATION if, given the reference values shown, the "
                 "claim is nevertheless physically wrong (e.g. the reasoning asserts something the reference contradicts).",
    "metallicity": "The oracle accepted the METALLIC/NONMETALLIC claim because it agrees with the Materials Project band gap "
                   "(<=0.05 eV metallic, >=0.20 eV non-metallic). Mark MISSED VIOLATION if the claim is nevertheless "
                   "physically wrong given the reference values shown.",
    "magnetism": "The oracle accepted the claim because the magnetic class (and, if magnetic, the per-atom magnitude within "
                 "one order of magnitude) agrees with the Materials Project net magnetization. Mark MISSED VIOLATION if the "
                 "claim is nevertheless physically wrong given the reference values shown.",
}


def image_for(fam, rec, img_dir):
    import exp17_rebuild_review_images as r17
    from halfB_report import image_to_data_uri
    src = r17.resolve_source(rec["source_file"])
    if src is None:
        return None
    if fam == "sem":
        return image_to_data_uri(src)
    out = os.path.join(img_dir, f"silent_{fam}_{os.path.basename(src)}.png")
    ok = r17.render_xrd(src, out) if fam == "xrd" else r17.render_spectrum(src, out)
    return image_to_data_uri(out) if ok else None


def case_html(i, fam, rec, img):
    claim = rec["parsed"]
    if isinstance(claim, dict):
        claim = f"{claim.get('value')} {claim.get('unit', '')}"
    rows = [f"<tr><th>Model's claim</th><td class='claim'>{html.escape(str(claim))}</td></tr>",
            "<tr><th>Oracle verdict</th><td>CONSISTENT (did not fire)</td></tr>"]
    if "formula" in rec:
        rows.insert(0, f"<tr><th>Formula</th><td>{html.escape(rec['formula'])} ({html.escape(rec['material_id'])})</td></tr>")
        rows.append(f"<tr><th>Materials Project reference</th><td>{html.escape(str(rec['reference']))}</td></tr>")
    img_html = f"<div class='case-image'><img src='{img}'/></div>" if img else ""
    key = rec.get("material_id") or os.path.basename(rec["source_file"])
    return f"""<div class="case" id="case-{i}"><div class="case-header"><span class="case-num">Case #{i + 1}</span>
<span class="model-badge">{html.escape(rec['model'])}</span><span class="source">{html.escape(key)}</span></div>
<div class="case-body">{img_html}<div class="case-details"><table>{''.join(rows)}</table>
<details open><summary>Full reasoning chain</summary><pre class="chain">{html.escape(rec['chain_text'])}</pre></details>
<div class="review-controls"><b>Your review:</b>
<label><input type="radio" name="review-{i}" value="missed_violation" onchange="t()"> Missed violation (oracle wrong)</label>
<label><input type="radio" name="review-{i}" value="clean" onchange="t()"> Clean (oracle right)</label>
<label><input type="radio" name="review-{i}" value="unsure" onchange="t()"> Unsure</label></div></div></div></div>""", key


STYLE = """<style>body{font-family:sans-serif;max-width:1000px;margin:0 auto;padding:20px;background:#fafafa}
.summary{position:sticky;top:0;background:#fff;padding:12px;border-radius:8px;box-shadow:0 1px 4px #0003;z-index:9}
.case{background:#fff;border-radius:8px;margin:16px 0;box-shadow:0 1px 3px #0002}.case-header{background:#eee;padding:6px 12px;display:flex;gap:12px;font-size:.85rem}
.model-badge{background:#333;color:#fff;padding:1px 8px;border-radius:4px}.case-body{display:flex;gap:16px;padding:12px;flex-wrap:wrap}
.case-image img{max-width:340px;border:1px solid #ddd}.case-details{flex:1;min-width:300px}th{text-align:left;color:#555;padding:3px 8px;vertical-align:top}
td{padding:3px 8px}pre.chain{white-space:pre-wrap;background:#f6f6f6;padding:8px;font-size:.8rem}.review-controls label{display:block}</style>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample_only", action="store_true")
    ap.add_argument("--out_dir")
    args = ap.parse_args()
    samples = load_samples()
    if args.sample_only:
        from collections import Counter
        print("SEM categories needed:", Counter(r["source_file"].split("/extracted/")[-1].split("/")[0] for r in samples["sem"]))
        return
    os.makedirs(args.out_dir, exist_ok=True)
    img_dir = os.path.join(args.out_dir, "_img")
    os.makedirs(img_dir, exist_ok=True)
    manifest = {}
    for fam, recs in samples.items():
        blocks, keys, missing = [], [], 0
        for i, rec in enumerate(recs):
            img = image_for(fam, rec, img_dir) if fam in ("xrd", "sem", "spectrum") else None
            if fam in ("xrd", "sem", "spectrum") and img is None:
                missing += 1
            b, k = case_html(i, fam, rec, img)
            blocks.append(b)
            keys.append(k)
        page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Oracle-silent audit: {fam}</title>{STYLE}</head><body>
<h1>Oracle-silent audit: {fam} ({len(recs)} cases)</h1><div class="summary"><p>{html.escape(GUIDE[fam])}</p>
<span id="tally">Reviewed: 0 / {len(recs)}</span> <button onclick="ex()">Export my review</button>
<textarea id="out" rows="5" style="width:100%"></textarea></div>{''.join(blocks)}
<script>const K={json.dumps(keys)};
function t(){{let k=0;for(let i=0;i<K.length;i++)for(const r of document.getElementsByName('review-'+i))if(r.checked)k++;document.getElementById('tally').textContent='Reviewed: '+k+' / '+K.length;}}
function ex(){{const o=[];for(let i=0;i<K.length;i++){{let v=null;for(const r of document.getElementsByName('review-'+i))if(r.checked)v=r.value;o.push({{case:i+1,key:K[i],verdict:v}});}}
document.getElementById('out').value=JSON.stringify({{family:"{fam}",audit:"oracle_silent",reviews:o}},null,2);}}</script></body></html>"""
        fn = os.path.join(args.out_dir, f"oracle_silent_{fam}.html")
        open(fn, "w").write(page)
        manifest[fam] = {"keys": keys, "models": [r["model"] for r in recs], "images_missing": missing}
        print(f"{fam:<12} {len(recs)} cases, images missing: {missing} -> {fn}")
    json.dump(manifest, open(os.path.join(args.out_dir, "oracle_silent_sample.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
