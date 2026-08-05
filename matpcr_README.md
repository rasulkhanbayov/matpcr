# MatPCR (DFT-grounded, cross-modal) — Student README (start here)

> ⚠️ **SUPERSEDED — this root-level README/manuscript predate the Phase 1-3 revision
> round (supervisor audit + Dr. Mustafa's DFT review response).** The current,
> submission-track manuscript, oracle code, and README live in `VERSION2/` —
> see `VERSION2/matpcr_README.md`. Do NOT submit `matpcr_snjnl.tex` from this
> directory; it still contains pre-correction numbers and a retracted finding.
> This file is kept only as the historical pre-revision draft.

Your entry point to the project. Plain-language summary of what the paper claims,
how to build it, what to run, and what to do next. The detailed protocol is in
`matpcr_runbook.txt`.

---

## 1. What the paper claims and why it matters

**One sentence:** Materials data carries its own physics, so we can check whether a
vision–language or language model's *reasoning* is physically consistent **without
human labels**, deepen that check with **DFT-computed references**, release a
**verifier** that predicts violations, and use the same signal to make models
self-correct.

**The gap:** Existing materials-model work scores the *final answer* against
*human labels*. A fast-growing discovery-agent line instead verifies *final
proposals* or the correctness of *DFT execution*. Neither measures, nor makes
reusable, the physical consistency of the *reasoning chain* itself.

**The contribution (5 parts):**
1. Reframe evaluation to **physical consistency of the reasoning chain**, across
   vision–language (images) and language (structure/text) inputs.
2. **MatPCR**: programmatic oracles (Bragg, scale bar, spectral peak) **plus
   DFT-grounded** oracles (stability vs convex hull, metallicity, property
   sign/magnitude) — all label-free.
3. **PCR**, a metric with confidence intervals and a paired significance test.
4. A fine-tuned, **released physical-consistency verifier** (the citable artifact).
5. **CGSV**, a label-free agentic self-verification loop.

**Closest neighbors to cite and stay distinct from** (verify each before submission). Materials reasoning/benchmarks: LLM4Mat-Bench, AtomWorld, "Can Multimodal LLMs See Materials Clearly?", MatterChat (Nat. Mach. Intell. 2026). Physical-law evaluation of model reasoning: ConservationBench (ICLR 2026, "VLMs cannot reason about physical transformation"), P1-VL (physics-Olympiad VLM with self-verification), physics-informed metrics for video generation, and neurosymbolic reference-free auditing of clinical VLM reasoning. Discovery agents: DREAMS, Crystalyse, MAPPS, physics-aware rejection sampling (arXiv 2509.00768), MatPC. Verifiers / process-reward / RLVR: ProcessBench, CompassVerifier, tool-integrated self-verification (T1), and the observation that verification is under-specified for science (arXiv 2602.08321). General CoT verification: CoRGI, MM-Verify, VLM-R3, PROVE. **None** provide a DFT-grounded, cross-modal, label-free benchmark + metric + released verifier for *reasoning-chain* physical consistency in materials. That is your wedge.

**Honest venue note:** Core *Nature* / *Nature Materials* almost always require
experimentally synthesized-and-characterized results, which you do not have (no
wet lab). The realistic, odds-maximizing home is **npj Computational Materials**
(Nature Portfolio) or **NeurIPS Datasets & Benchmarks / ICLR**, with *Nature
Communications* a stretch only if the finding is broad and clean. This paper is
written to fit those.

**Why this and not a discovery paper:** A discovery headline depends on DFT
results that do not exist yet and may not pan out, and the physics-verified-agent
method space is crowded. Betting the paper on an uncertain finding in a saturated
space lowers acceptance odds. The verifier/benchmark contribution does not depend
on a discovery and ships a reusable artifact. A discovery case study is kept as an
optional stretch in the runbook, not the headline.

---

---

## npj Computational Materials: submission specifics (verified)

This draft is prepared for **npj Computational Materials** (Nature Portfolio, Springer
Nature). Key points confirmed from the journal's current guidelines:

- **Structure** follows the Nature Portfolio Article format: Abstract, Introduction,
  **Results**, **Discussion**, **Methods**, then **Data availability**, **Code
  availability**, **Author contributions**, **Competing interests**,
  **Acknowledgements**, References. The paper already uses this structure.
- **References** are numbered, in order of appearance, cited as superscripts (Nature
  style). The LaTeX uses `natbib` with `[numbers,super,sort&compress]` and
  `unsrtnat`.
- **No strict length limits** (online-only, open access), but write concisely.
- **Formatting is required only at acceptance**, not at initial submission, so this
  self-contained LaTeX is acceptable for first submission; at acceptance you can drop
  the text into the official Springer Nature template (`sn-jnl.cls`).
- **AI-use policy:** LLMs are not authors; any LLM use must be documented in Methods.
  The manuscript includes a "Use of AI assistance" statement in Methods, and the
  authors take full responsibility. Keep this.
- **Cover letter** (`matpcr_cover_letter.txt`) is included and is confidential (not
  shared with referees). Use it to declare conflicts, related/in-press work, and
  suggested/excluded referees, and to provide both corresponding authors' ORCIDs (Hasan Kurban; Mustafa Kurban, mkurbanphys@gmail.com).
- **At peer review** you will be asked for the Nature Portfolio Reporting Summary and
  editorial policy checklist; prepare these.
- **Open access:** npj Computational Materials is fully OA; check the current article
  processing charge and any waiver eligibility before submitting.

Note: it is npj **Computational** Materials, so the DFT-grounded, fully computational
nature of MatPCR is a good fit; the experimental-validation gap that rules out core
Nature does not apply here.

**Theory.** The *novel* measurement theory is complete in the main text (Methods, "Measurement guarantees"): Proposition 1 (exact bias decomposition of measured vs. true PCR), Corollary 1 (one-sided guarantees and a bias bound that the positive control estimates), Proposition 2 (CGSV accounting and termination), and Proposition 3 (verifier-substitution bound). All proofs are short and complete, and every conditional claim states its assumption (e.g., Assumption A for CGSV non-harm). Standard background derivations (Bragg's law, scale-bar calibration, convex-hull stability, percentile bootstrap, exact McNemar) are in the Appendix. For npj you may move the Appendix to Supplementary Information if preferred.

**Template.** The manuscript is written for the official Springer Nature class, `\documentclass[pdflatex,sn-nature]{sn-jnl}`, which is the correct template for npj Computational Materials (a Nature Portfolio journal). The layout is single-column and content-first (peer-review-optimized); Springer applies the final published two-column layout at production. Journal metadata are placeholders and no logos are reproduced.

## 2. How to read and build the paper

Files: `matpcr_snjnl.tex` (manuscript source, official sn-jnl template),
`matpcr_refs.bib` (references; `% VERIFY` entries need checking),
`matpcr_snjnl.bbl` (precompiled bibliography), `matpcr_snjnl.pdf` (compiled proof),
`matpcr_submission.zip` (self-contained source).

Compile with the official Springer Nature template files present (see the
"Official npj / Springer Nature template" section below):
```
pdflatex matpcr_snjnl.tex
bibtex   matpcr_snjnl
pdflatex matpcr_snjnl.tex
pdflatex matpcr_snjnl.tex
```

Where each claim lives: framing in the Abstract + boxed Contributions (p.1);
geometric oracles §3.3; **DFT-grounded oracles §3.4**; label-free argument §3.5;
metric §4 (Eq. 1); CGSV §5 (Algorithm 1); **verifier §6**; every experiment and
empty results table §7–§8. Red `>>> TO RUN` tags mark experiments; blue
`[RESULT PLACEHOLDER]` cells are unmeasured numbers.

---

## 3. What the experiments are and how to run them

Full protocol in **`matpcr_runbook.txt`**. Short version:
- **Do Experiment 1 first** (positive control + manual oracle precision audit),
  including the DFT-grounded oracles. Have your co-author sign off on the DFT
  protocol and tolerances. If a checker is buggy, fix it before any model run.
- Then: PCR sweep (Exp 2), accuracy-vs-consistency gap (Exp 3), CGSV before/after
  (Exp 4), **verifier training + release** (Exp 5), detector AUC (Exp 6).

Promising vs negative, and what to do:
- **Promising:** PCR varies across models/modalities/constraint types, a real
  accuracy–consistency gap exists, CGSV raises PCR significantly, and the verifier
  generalizes. Keep the five-part framing.
- **Negative/weak:** PCR near 1.0 everywhere (add harder items, or narrow to
  benchmark+metric+verifier), or CGSV/verifier underperform (report honestly).
  A clean, honestly-reported negative is publishable and beats an overclaimed
  positive.

Fill tables only with measured numbers; reconcile abstract, title, contributions.

---

## 4. What the code computes and how to run it

`matpcr_metrics.py` (numpy only): geometric checkers (`xrd_peak_consistent`,
`sem_feature_size_consistent`, `spectrum_peak_exists`), **DFT-grounded checkers**
(`stability_claim_consistent`, `metallicity_claim_consistent`,
`property_sign_magnitude_consistent`), the metric (`physical_consistency_rate`,
`violation_rate_by_type`), `bootstrap_ci`, paired `mcnemar_exact`, `roc_auc`, and
**verifier evaluation** (`precision_recall_f1`, `expected_calibration_error`).

Run the smoke test (synthetic; demonstrates the estimators, **not** a result):
```
python3 matpcr_metrics.py
```
You should see all checkers pass their unit checks, PCR recover a planted rate,
McNemar return a tiny p on a planted improvement, AUC above 0.5, the DFT oracles
pass, and the verifier metrics come out strong. For the real analysis, replace the
synthetic items with `ItemResult` objects built from your model chains and oracle
outputs.

---

## 5. Integrity and next-steps checklist

- [ ] Fresh arXiv novelty search right before submission (neighbors above).
- [ ] Fill every `% VERIFY` citation by reading the source. Never invent authors.
- [ ] Co-author independently verifies all physics (Bragg, scale-bar geometry,
      DFT protocol, stability/metallicity/property oracles, the metric, CGSV).
      The assistant only drafted; the human authors are the authors.
- [ ] Run Experiment 1 and confirm oracle precision **before** trusting any PCR.
- [ ] Fill all tables with measured numbers; reconcile every claim; walk back
      anything the data does not support.
- [ ] Check the venue's AI-use/disclosure and reproducibility policy and comply.
- [ ] **Declare related author work to the editor** (npj policy): CrysMTM, R-CRYSTALS (under review), QuantumShellNet, HalluVerse25, IRIS. Confirm no significant text/result overlap; MatPCR's axis (reasoning-chain physical consistency) is distinct, but you must state this and provide copies on request.
- [ ] Get **2–3 independent human mock reviews** and resolve every issue.

This process maximizes the probability your research deserves; it cannot
manufacture it. The results are the ceiling, and they are yours to produce.

## Official npj / Springer Nature template (sn-jnl)
`matpcr_snjnl.tex` (in this directory) is written for the official Springer Nature class: `\documentclass[pdflatex,sn-nature]{sn-jnl}` with proper `\title/\author/\affil/\abstract/\keywords` macros. **However, per the SUPERSEDED banner above, this is NOT the file to submit.** The current, correct submission source is `VERSION2/matpcr_snjnl.tex` — use that one and its accompanying `VERSION2/matpcr_submission.zip`.

Recommended path:
1. Open the official **Springer Nature LaTeX template** on Overleaf (it ships the current, complete `sn-jnl.cls` and `sn-nature.bst`).
2. Replace the template main `.tex` with `matpcr_snjnl.tex`, add `matpcr_refs.bib`, and compile (pdflatex -> bibtex -> pdflatex x2). It compiles cleanly with the official files.
3. For peer review add the `[referee]` and `[lineno]` class options (double spacing + line numbers).

The bundled `matpcr_snjnl.pdf` is a local proof-of-compile only. It was built against a community GitHub mirror of the class/bst that I had to patch (the mirror omitted `manyfoot` and `amsmath` and had a buggy conference-entry formatter). Use Overleaf's official files for the real submission. `matpcr_snjnl` is the submission version: single-column and peer-review-optimized, intentionally not identical to the final two-column published layout, which Springer applies at production.
