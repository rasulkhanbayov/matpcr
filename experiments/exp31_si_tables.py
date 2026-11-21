"""
exp31_si_tables.py
==================
KBS revision R1: render the new Supplementary Tables directly from the analysis
outputs, so no number in them is copied by hand.

  S2  coverage and alternative treatments of non-checkable responses   (exp22_results.json)
  S3  paired, Holm-corrected model comparisons                         (exp23_results.json)
  S4  class-conditional and class-balanced DFT PCR                     (exp26_results.json)
  S5  violation taxonomy, spectra and DFT families                     (exp30_results.json)
  S6  common class-balanced DFT item set (paired)                      (exp29_results*.jsonl), if present

Run: python experiments/exp31_si_tables.py --out KBS_revision_R1/revised/submission/si_tables_generated.tex
"""

from __future__ import annotations

import argparse
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = ["local", "gemini", "gpt4o", "claude", "opus46", "gpt56", "gpt56sol", "qwen3vl", "qwen3vl_thinking"]
LABEL = {"local": "Qwen2.5-VL-7B", "gemini": "Gemini 2.5 Flash Lite", "gpt4o": "GPT-4o",
         "claude": "Claude Sonnet 4.5", "opus46": "Claude Opus 4.6", "gpt56": "GPT-5.6-Terra",
         "gpt56sol": "GPT-5.6-Sol", "qwen3vl": "Qwen3-VL-8B-Instruct", "qwen3vl_thinking": "Qwen3-VL-8B-Thinking"}
TYPES = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]
TLABEL = {"xrd": "Diffraction", "sem": "Microscopy", "spectrum": "Spectra", "stability": "Stability",
          "metallicity": "Metallicity", "magnetism": "Magnetism"}


def load(name):
    return json.load(open(os.path.join(HERE, name)))


def fmt_p(p):
    if p >= 0.001:
        return f"{p:.3f}"
    m, e = f"{p:.1e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


def s2():
    d = load("exp22_results.json")
    rows = []
    for m in MODELS:
        cov = [d["cells"][f"{m}|{t}"]["coverage"] for t in TYPES]
        o = d["overall"]
        r = d["rank"]
        rows.append(f"{LABEL[m]} & " + " & ".join(f"{c:.2f}" for c in cov) +
                    f" & {o['excluded'][m]:.3f} ({r['excluded'][m]}) & {o['penalised'][m]:.3f} ({r['penalised'][m]})"
                    f" & {o['lenient'][m]:.3f} ({r['lenient'][m]}) \\\\")
    ev = {t: sorted({d['cells'][f'{m}|{t}']['evaluable'] for m in MODELS}) for t in TYPES}
    evtxt = "; ".join(f"{TLABEL[t].lower()} {('--'.join(map(str, [min(v), max(v)])) if len(v) > 1 else v[0])}"
                      for t, v in ev.items())
    tau = d["kendall_tau_overall"]
    return rf"""\clearpage
\section*{{Supplementary Table S2}}
\noindent\textbf{{Coverage of the Physical-Consistency Rate and alternative treatments of non-checkable
responses.}} Each (model, constraint-type) cell attempts 90 items (30 per seed, $S=3$). Items the
oracle can score (evaluable) per cell: {evtxt}. Diffraction items without a usable reference
structure, metallicity items in the 0.05--0.20~eV abstention band and near-hull stability materials
($0<E_{{\mathrm{{hull}}}}\le0.05$~eV\,atom$^{{-1}}$) are not evaluable for any model.
For image constraint types an item counts as evaluable if at least one of the nine models produced a
checkable response on it (all models received the same items), which is a lower bound on true
evaluability. Coverage is checkable responses / evaluable items; it absorbs the rare API failures and
time-outs, which the result files do not record separately. Overall PCR (rank in parentheses) under
three conventions: \emph{{excluded}} (reported in the Article; non-checkable responses are not scored),
\emph{{penalised}} (a non-checkable response counts as a violation) and \emph{{lenient}} (it counts as
consistent). Kendall $\tau$ of the model ordering against the reported convention: penalised
{tau['penalised'][0]:.2f}, lenient {tau['lenient'][0]:.2f}.
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{3.2pt}}\renewcommand{{\arraystretch}}{{1.08}}
\begin{{tabular}}{{l cccccc ccc}}
\toprule
& \multicolumn{{6}}{{c}}{{Coverage}} & \multicolumn{{3}}{{c}}{{Overall PCR (rank)}} \\
\cmidrule(lr){{2-7}}\cmidrule(lr){{8-10}}
Model & Diffr. & Micro. & Spectra & Stab. & Metal. & Magn. & excluded & penalised & lenient \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""


def s3():
    d = load("exp23_results.json")
    def row(r):
        sc = "overall" if "+" in r["scope"] else TLABEL[r["scope"]]
        return (f"{LABEL[r['a']]} vs {LABEL[r['b']]} & {sc} & {r['effect']:+.3f} & [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]"
                f" & {r['mde80']:.3f} & {r['test'].split(' (')[0]} & {fmt_p(r['p'])} & {fmt_p(r['p_holm'])} \\\\")
    f1 = "\n".join(row(r) for r in d["F1_headline"])
    f2 = "\n".join(row(r) for r in sorted(d["F2_all_pairs_overall"], key=lambda r: -abs(r["effect"])))
    per = []
    import statistics
    for t in TYPES:
        rows = d["per_type_all_pairs"][t]
        per.append(f"{TLABEL[t]} & {sum(r['p_holm'] < 0.05 for r in rows)} & {statistics.median(r['mde80'] for r in rows):.3f} \\\\")
    return rf"""\clearpage
\section*{{Supplementary Table S3}}
\noindent\textbf{{Paired, multiplicity-corrected model comparisons.}} Differences are PCR of model A minus
model B. Image constraint types: all models answered the same items, so A and B are compared on the
items both answered checkably (exact McNemar test). DFT constraint types: models answered different
materials (Fisher's exact test). Overall: bootstrap of the difference that resamples paired items
jointly and DFT items within model ($B=10{{,}}000$; two-sided bootstrap $p$). 95\% CI: bootstrap.
MDE: smallest difference detectable with 80\% power at $\alpha=0.05$, $(z_{{0.975}}+z_{{0.80}})\times$
bootstrap SE. $p_{{\mathrm{{Holm}}}}$: Holm-corrected within the family shown. (a) The 12 comparisons
stated in the Article. (b) Within each constraint type, all 36 pairs: number significant after Holm
and median MDE. (c) All 36 pairs on overall PCR, ordered by $|\Delta|$.
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{3pt}}\renewcommand{{\arraystretch}}{{1.05}}
\begin{{tabular}}{{l l r c r l r r}}
\toprule
Comparison (A vs B) & Scope & $\Delta$ & 95\% CI & MDE & Test & $p$ & $p_{{\mathrm{{Holm}}}}$ \\
\midrule
\multicolumn{{8}}{{l}}{{\itshape (a) Comparisons stated in the Article (Holm over 12)}}\\
{f1}
\bottomrule
\end{{tabular}}}}

\vspace{{0.8em}}
{{\scriptsize\setlength{{\tabcolsep}}{{6pt}}
\begin{{tabular}}{{l r r}}
\toprule
\multicolumn{{3}}{{l}}{{\itshape (b) All 36 pairs within each constraint type (Holm over 36)}}\\
Constraint type & significant pairs & median MDE \\
\midrule
{chr(10).join(per)}
\bottomrule
\end{{tabular}}}}
\end{{table}}
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{3pt}}\renewcommand{{\arraystretch}}{{1.02}}
\begin{{tabular}}{{l l r c r l r r}}
\toprule
\multicolumn{{8}}{{l}}{{\itshape (c) All 36 pairs on overall PCR (Holm over 36): {sum(r['p_holm'] < 0.05 for r in d['F2_all_pairs_overall'])} significant}}\\
Comparison (A vs B) & Scope & $\Delta$ & 95\% CI & MDE & Test & $p$ & $p_{{\mathrm{{Holm}}}}$ \\
\midrule
{f2}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""


def s4():
    d = load("exp26_results.json")
    names = {"stability": ("on hull", "above hull"), "metallicity": (r"gap $\le$0.05 eV", r"gap $\ge$0.20 eV"),
             "magnetism": ("magnetic", "non-magnetic")}
    rows = []
    for t in ["stability", "metallicity", "magnetism"]:
        p, n = names[t]
        rows.append(rf"\multicolumn{{7}}{{l}}{{\itshape {TLABEL[t]}: positive class = {p}, negative class = {n}}}\\")
        for m in MODELS:
            c = d[f"{m}|{t}"]
            rows.append(f"{LABEL[m]} & {c['n_pos']} & {c['pcr_pos']:.3f} & {c['n_neg']} & {c['pcr_neg']:.3f} & "
                        f"{c['pooled']:.3f} & {c['balanced']:.3f} \\\\")
        rows.append(r"\addlinespace")
    return rf"""\clearpage
\section*{{Supplementary Table S4}}
\noindent\textbf{{Class-conditional and class-balanced PCR on the DFT constraint types.}} Reference classes
use each oracle's own definitions (stability: on the hull vs.\ $E_{{\mathrm{{hull}}}}>0.05$~eV\,atom$^{{-1}}$, near-hull
materials not scored; metallicity:
computed gap $\le0.05$~eV vs.\ $\ge0.20$~eV, abstention band excluded; magnetism: $|M|$ per atom
$\ge0.05\,\mu_{{\mathrm{{B}}}}$). Pooled: PCR over all checkable responses (as in the Article's main table).
Balanced: mean of the two per-class rates. Main evaluation records (each model answered its own
materials).
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{5pt}}\renewcommand{{\arraystretch}}{{1.03}}
\begin{{tabular}}{{l r r r r r r}}
\toprule
Model & $n_{{+}}$ & PCR$_{{+}}$ & $n_{{-}}$ & PCR$_{{-}}$ & pooled & balanced \\
\midrule
{chr(10).join(rows[:-1])}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""


def s5():
    d = load("exp30_results.json")
    blocks = []
    for t in ["spectrum", "stability", "metallicity", "magnetism"]:
        tx = d[t]["taxonomy"]
        n = d[t]["n_violations"]
        shown = [x for x in tx if x["count"] / n >= 0.03]
        other = n - sum(x["count"] for x in shown)
        lines = [f"& {x['category']} & {x['count']} & {100 * x['count'] / n:.1f}\\% \\\\" for x in shown]
        if other:
            lines.append(f"& other categories ($<$3\\% each) & {other} & {100 * other / n:.1f}\\% \\\\")
        lines[0] = TLABEL[t] + f" ($n={n}$) " + lines[0]
        blocks.append("\n".join(lines))
    body = ("\n" + r"\addlinespace" + "\n").join(blocks)
    return rf"""\clearpage
\section*{{Supplementary Table S5}}
\noindent\textbf{{Violation taxonomy for the spectrum and DFT-grounded oracle families.}} Every
human-confirmed real violation in the final-oracle precision audits (Article, Table~1) was labelled
open-ended by Gemini 2.5 Flash Lite and the labels were merged by a second, semantic clustering pass
(the same procedure as the diffraction and microscopy taxonomy in the Article's Fig.~1c). Categories
are machine-generated names and are indicative only; the metallicity clustering returned fine-grained
categories, which are shown as returned.
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{5pt}}\renewcommand{{\arraystretch}}{{1.05}}
\begin{{tabular}}{{l l r r}}
\toprule
Family & Category & count & share \\
\midrule
{body}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""


def s6():
    paths = [os.path.join(HERE, f) for f in ("exp29_results.jsonl", "exp29_results_local.jsonl")]
    recs = final_oracle.filter_records([json.loads(l) for p in paths if os.path.exists(p) for l in open(p)])
    if not recs:
        return ""
    cells = defaultdict(list)
    for r in recs:
        cells[(r["model"], r["modality"])].append(r)
    rows = []
    for t in ["stability", "metallicity", "magnetism"]:
        rows.append(rf"\multicolumn{{7}}{{l}}{{\itshape {TLABEL[t]}}}\\")
        for m in MODELS:
            rs = cells.get((m, t))
            if not rs:
                continue
            ch = [r for r in rs if r["checkable"]]
            pos = [r["consistent"] for r in ch if r["ref_class_positive"]]
            neg = [r["consistent"] for r in ch if not r["ref_class_positive"]]
            pp, pn = sum(pos) / len(pos), sum(neg) / len(neg)
            rows.append(f"{LABEL[m]} & {len(rs)} & {len(ch)/len(rs):.2f} & {sum(r['consistent'] for r in ch)/len(ch):.3f}"
                        f" & {pp:.3f} & {pn:.3f} & {(pp + pn) / 2:.3f} \\\\")
        rows.append(r"\addlinespace")
    paired = ""
    p34 = os.path.join(HERE, "exp34_results.json")
    if os.path.exists(p34):
        e = json.load(open(p34))
        parts = [f"{LABEL[r['a']]} $-$ {LABEL[r['b']]}: ${r['effect']:+.3f}$ [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}], "
                 f"Holm $p={r['p_holm']:.3f}$" for r in e["stated"]]
        n_sig = sum(r["p_holm"] < 0.05 for r in e["pooled_all_pairs"])
        paired = (" Paired comparisons pooled over the three types (exact McNemar on shared materials, bootstrap 95\\% CI, Holm): "
                  + "; ".join(parts) + f". Across all {len(e['pooled_all_pairs'])} pairs, {n_sig} differ after Holm correction.")
    return rf"""\clearpage
\section*{{Supplementary Table S6}}
\noindent\textbf{{Common, class-balanced DFT item set.}} Every model answered the same 90 materials per DFT
constraint type (45 per reference class, drawn once with a fixed seed from the archived
3{{,}}000-material batch; the item list is released with the code). For stability, 34 of the 45 near-hull draws
fall in the band the final oracle does not score, leaving 11 on-hull and 45 above-hull materials. Coverage: checkable / 90.
PCR$_{{+}}$, PCR$_{{-}}$: per reference class (classes as in Table~S4). Qwen3-VL-8B-Thinking is absent because
its provider endpoint had been withdrawn when this set was run (2026-10-15); Qwen2.5-VL-7B was run on CPU in float32 for this set.{paired}
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{5pt}}\renewcommand{{\arraystretch}}{{1.03}}
\begin{{tabular}}{{l r r r r r r}}
\toprule
Model & $n$ & coverage & PCR & PCR$_{{+}}$ & PCR$_{{-}}$ & balanced \\
\midrule
{chr(10).join(rows[:-1])}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""



def s7():
    d = load("exp38_results.json")["main"]
    rows = []
    for m in MODELS:
        if m not in d["original"]:
            continue
        o, a = d["original"][m], d["abstain"][m]
        rows.append(f"{LABEL[m]} & {o['stability']:.3f} & {a['stability']:.3f} & {a['stability'] - o['stability']:+.3f} & "
                    f"{o['overall']:.3f} & {a['overall']:.3f} \\\\")
    au = load("exp38_results.json")["audit_without_conflict"]
    return rf"""\clearpage
\section*{{Supplementary Table S7}}
\noindent\textbf{{Stability results under the original and the final stability rule.}} The original rule
required a STABLE claim whenever $E_{{\mathrm{{hull}}}}\le0.05$~eV\,atom$^{{-1}}$, although the stability prompt
instructs the model to treat borderline or metastable cases as UNSTABLE; a model following the prompt on a
near-hull material was therefore counted as a violation. The final rule does not score near-hull materials
($0<E_{{\mathrm{{hull}}}}\le0.05$), as for the metallicity abstention band. Main-evaluation records:
{d['band_share']['in_band']} of {d['band_share']['stability_records']} stability records are near-hull,
{d['band_share']['in_band_flagged']} of which the original rule flagged. Overall: PCR over all six constraint
types. In the precision audit, {au['removed']} of the 107 audited stability cases are near-hull; the remaining
{au['n']} were all confirmed as genuine violations by the first annotator. Kendall $\tau$ of the overall model
ordering between the two rules: {d['kendall_tau_overall_abstain']:.2f}; of the stability ordering:
{d['kendall_tau_stability_abstain']:.2f}.
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{5pt}}\renewcommand{{\arraystretch}}{{1.05}}
\begin{{tabular}}{{l r r r r r}}
\toprule
& \multicolumn{{3}}{{c}}{{Stability PCR}} & \multicolumn{{2}}{{c}}{{Overall PCR}} \\
\cmidrule(lr){{2-4}}\cmidrule(lr){{5-6}}
Model & original & final & change & original & final \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""


def s8():
    a = load("exp37_results.json")
    b = load("exp36_results.json")
    c = load("exp41_results.json")
    rows = []
    for fam in TYPES:
        x, y = a[fam], b.get(fam)
        kap = "--" if x["kappa"] != x["kappa"] else f"{x['kappa']:.2f}"
        silent = (f"{y['missed']}/{y['n_decided']} & [{y['miss_rate_ci95'][0]:.2f}, {y['miss_rate_ci95'][1]:.2f}] & {y['implied_recall']:.3f}"
                  if y else "-- & -- & --")
        z = c[fam]
        rows.append(f"{TLABEL[fam]} & {x['precision_A']:.3f} & {x['precision_B_stratified']:.3f} "
                    f"[{x['precision_B_ci95'][0]:.2f}, {x['precision_B_ci95'][1]:.2f}] & "
                    f"{z['precision_consensus']:.3f} [{z['precision_consensus_ci95'][0]:.2f}, {z['precision_consensus_ci95'][1]:.2f}] & "
                    f"{x['n_compared']} & {x['raw_agreement']:.2f} & {kap} & {z['n_adjudicated']} & {silent} \\\\")
    return rf"""\clearpage
\section*{{Supplementary Table S8}}
\noindent\textbf{{Second annotator and oracle-silent audit.}} Precision A: first annotator, all audited fired cases
(as in the Article's Table~1). Precision B: second annotator, who independently labelled a random subsample of 30
audited cases per family stratified by A's verdict (false positives over-sampled), weighted back to the audited
population by stratum; 95\% interval from per-stratum Jeffreys posteriors. $n$: subsampled cases scored under the
final oracle (for stability, near-hull cases are not scored). $\kappa$: Cohen's kappa on those cases (undefined when
both annotators gave every case the same label). Oracle-silent audit: 30 randomly sampled responses the oracle
judged consistent per family; missed = cases an annotator judged a genuine violation the oracle missed (Wilson 95\%
interval); implied recall scales the miss rate to the oracle-silent share of the audited population. Consensus:
the shared label where A and B agree, otherwise the label both annotators chose when adjudicating the case
together (adj.: number adjudicated; 24 in total, none in stability or metallicity); consensus precision is
weighted back by stratum like precision B. The consensus sided with B in every diffraction, spectrum and
magnetism dispute and with A in both microscopy disputes.
\begin{{table}}[htbp]
\centering
{{\scriptsize\setlength{{\tabcolsep}}{{2.5pt}}\renewcommand{{\arraystretch}}{{1.05}}
\begin{{tabular}}{{l r l l r r r r r l r}}
\toprule
& \multicolumn{{7}}{{c}}{{Precision audit}} & \multicolumn{{3}}{{c}}{{Oracle-silent audit}} \\
\cmidrule(lr){{2-8}}\cmidrule(lr){{9-11}}
Family & prec.\ A & prec.\ B [95\% CI] & consensus [95\% CI] & $n$ & agree & $\kappa$ & adj. & missed & 95\% CI & recall \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabular}}}}
\end{{table}}
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--include", nargs="+", default=["s2", "s3", "s4", "s5", "s6", "s7", "s8"])
    args = ap.parse_args()
    parts = [globals()[x]() for x in args.include]
    with open(args.out, "w") as f:
        f.write("% generated by experiments/exp31_si_tables.py -- do not edit by hand\n")
        f.write("\n".join(p for p in parts if p))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
