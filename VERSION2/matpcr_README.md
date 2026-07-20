# MatPCR (DFT-grounded, cross-modal) — README (finalized draft, 2026-07-12)

Entry point to the finalized submission bundle for **npj Computational Materials**.
This version reflects a finalization pass over the results-in draft: claims reconciled
to the reported numbers, scaffolding stripped, the oracle-validity gate integrated,
citations verified, novelty re-checked against the latest arXiv, and every remaining gap
marked in red in the manuscript. The detailed experiment protocol is in
`matpcr_runbook.txt`; the list of items you must still fill is in `matpcr_REDFLAGS.txt`.

---

## 1. What the paper claims now (with the real results)

**One sentence:** Materials data carries its own physics, so we can check whether a
vision–language or language model's *reasoning chain* is physically consistent **without
human labels**, deepen that check with **DFT-computed references**, release a **verifier**
that predicts violations, and use the same signal to make models self-correct.

**Headline results as reported (verified for internal consistency; see §5 on provenance):**
- **Oracle-validity gate (Table 1).** The positive control recovered every planted
  violation for all six oracle families (false-negative rate 0.0000). Audited precision on
  real oracle-fired cases: XRD 77.2% (n=101), SEM 88.6% (n=105), Raman 72.8% (n=103). The
  three DFT-grounded families' precision audit is **pending** the co-author's DFT sign-off.
- **Physical-Consistency Rate (Table 2).** Overall PCR ranges 0.635 (Qwen2.5-VL-7B) to
  0.734 (Gemini 2.5 Flash Lite); microscopy easiest, diffraction and magnetism hardest.
- **Accuracy vs consistency.** Accuracy and PCR disagree on a mean 41.8% of items across
  12 cells — PCR is not answer accuracy under another name.
- **CGSV (Table 2, self-verification).** Never regressed a consistent item (b=0 in all 8
  cells); raised PCR significantly for 3 of 4 models (McNemar p from 4.9e-4 to 1.2e-7),
  Gemini directional but not significant (p=0.063), reported honestly.
- **Verifier (Table 3).** Useful in-distribution (AUC 0.858); cross-modality transfer is
  the paper's clearest negative result (5 of 6 held-out constraint types at or near
  chance), with magnetism the lone exception (AUC 0.867). Reported as a limitation, not
  hidden.

**The contribution (5 parts):** (1) reframe evaluation to physical consistency of the
reasoning chain, label-free, across image and structure inputs; (2) MatPCR programmatic
oracles (Bragg, scale bar, spectral peak) plus DFT-grounded oracles (stability,
metallicity, property sign/magnitude); (3) PCR with bootstrap CIs and an exact paired
McNemar test; (4) a released physical-consistency verifier; (5) CGSV, a label-free
self-verification loop. Novel measurement theory (Propositions 1–3) is in the main text;
standard derivations are in the Appendix.

## 2. What this finalization pass changed

- **Integrated the oracle-validity gate** (positive control + precision audit) into
  Results as past-tense reporting with a table, and tied it to Corollary 1 (planted
  recall d-hat = 1 implies measured PCR does not overstate true consistency). Previously
  this experiment lived only in a separate fragment and the theory referenced numbers the
  paper never reported.
- **Reconciled the model list** to the four models that actually appear in the tables
  (removed unsupported mentions of LLaVA-class / open-reasoning-LLM / MatterChat runs).
- **Stripped scaffolding macros** (`>>> TO RUN`, `tbd`) from the source.
- **Verified all citations** by arXiv/publisher search and replaced placeholder
  corporate authors with real first authors; corrected two wrong titles (Crystalyse,
  MAPPS) and one year/ID (VLM-R3). Added the two closest contemporaneous neighbors,
  **Mat-Pref** (arXiv 2606.21830) and **CrystalXRD-Bench** (arXiv 2605.29446), to the
  novelty delta.
- **Sharpened the novelty statement** to a precise multi-part delta (setting / signal /
  assumption / artifact), replacing any bare "first."
- **Strengthened the story and positioning against the mid-2026 SOTA** (51 references
  total): added the measurement guarantees and the "verifiable domain" framing to the
  contributions; added a chain-faithfulness motivation (why score the chain against
  external physics rather than trust an unfaithful trace or an outcome judge,
  arXiv 2605.24286); distinguished recent step-level science/structured-reasoning
  verifiers (Sci-PRM arXiv 2606.04579; "Beyond Outcome Verification"/VPRMs
  arXiv 2601.17223); and grounded CGSV's design in the finding that model self-checks are
  largely confirmatory (arXiv 2602.03485). None of these changes touched the experimental
  results.
- **Completed the measurement theory.** Added a main-body result (now Proposition 2,
  "Total error of the reported estimate") that combines the exact oracle-bias identity
  (Prop 1 / Cor 1) with a finite-sample concentration bound, so the reported PCR's total
  error as an estimate of the true consistency rate is bounded (oracle bias plus
  sampling), fully delivering the abstract's "exact guarantees." The novel results
  (Propositions 1-4 and Corollary 1) are all in the main body with proofs; the standard
  concentration inequality it rests on (Hoeffding) is in Appendix A.5 with the other
  standard derivations.
- **Fixed a code discrepancy**: `property_sign_magnitude_consistent` in
  `matpcr_metrics.py` now uses the absolute-tolerance zero check (`zero_atol`) that the
  Experiment-1 notes said was applied but that was missing from the shipped code.
- **Trimmed the abstract** toward the journal's ~150-word guideline.
- **Inserted red flags** for every author-supplied item still missing (see §4).

## 3. How to build

```
pdflatex matpcr_snjnl.tex
bibtex   matpcr_snjnl
pdflatex matpcr_snjnl.tex
pdflatex matpcr_snjnl.tex
```

Compiles cleanly with the bundled `sn-jnl.cls` and `sn-nature.bst` in the same directory
(pdflatex, bibtex, no errors, no undefined/multiply-defined citations, no bad overfull
boxes; 22 pages). A precompiled `matpcr_snjnl.bbl` is included so one `pdflatex` pass
resolves references even without running BibTeX. Where each claim lives: framing in the
Abstract + boxed Contributions; oracle-validity gate and PCR in Results; oracles and the
metric in Methods; Propositions 1–3 (novel theory) in "Measurement guarantees"; standard
derivations in the Appendix.

## 4. What you must still fill (red flags) and resolve (blocking)

See **`matpcr_REDFLAGS.txt`** for the full, itemized list. Summary:
- **Blocking B1:** run the DFT precision audit and obtain the co-author's DFT-protocol
  sign-off; the DFT/All numbers are provisional until then.
- **Blocking B2:** confirm the in-distribution verifier split is source-disjoint (else the
  0.858 AUC may be optimistic).
- **Red flags to fill:** DFT precision cells (Table 1); Supplementary Table S1; the DFT
  protocol settings; exact model versions + API snapshot dates + experiment date; decoding
  config and bootstrap B; funding + compute; cover-letter date and ORCIDs; repository DOIs
  at acceptance.
- **Reviewer risk (address in cover letter/rebuttal):** the four evaluated models are 1–2
  generations behind the mid-2026 frontier; consider adding a current-generation model and
  the current open baseline (Qwen3-VL-8B).

## 5. Provenance of the numbers (read this)

The bundle provided the metric code and the Experiment-1 gate fragment, **not** the raw
per-item model outputs or a results CSV. Every number in Tables 1–3 was therefore checked
for **internal** consistency (F1 recomputed from precision/recall; McNemar p recomputed
from b,c; CGSV per-model n reconciled to the stated 555 records; text ranges matched to
table cells — all consistent) but could **not** be reproduced from raw source. Treat the
headline numbers as "internally consistent, taken on trust for provenance." To make them
fully verifiable, deposit the per-item oracle outputs and rebuild Tables 1–3 from them.

## 6. Code

`matpcr_metrics.py` (numpy only): geometric and DFT-grounded checkers, the metric,
bootstrap CIs, exact McNemar, ROC AUC, and verifier evaluation (P/R/F1, ECE). Run the
smoke test (synthetic; demonstrates the estimators, **not** a result):

```
python3 matpcr_metrics.py
```

All checkers pass their unit checks; PCR recovers a planted rate; McNemar returns a tiny p
on a planted improvement; AUC > 0.5; the DFT oracles pass. For the real analysis, replace
the synthetic items with `ItemResult` objects built from the model chains and oracle
outputs.

## 7. Venue specifics (npj Computational Materials, verified 2026-07-12)

- Structure (Abstract, Introduction, Results, Discussion, Methods, Data availability, Code
  availability, Author contributions, Competing interests, Acknowledgements, References)
  matches the current Nature Portfolio format.
- References: numbered Nature style (limit ~60; the paper has 51).
- No strict length limits (online-only OA); abstract guideline ~150 words.
- Formatting required only at acceptance; this self-contained LaTeX is acceptable for first
  submission.
- **Single-anonymized (single-blind)** review: submit with author names visible; do NOT
  anonymize.
- AI-use policy: LLM use is documented in Methods; LLMs are not authors; authors take full
  responsibility. (Kept.)
- Reporting Summary is not required for computational materials; a Data availability
  statement is required at acceptance and code/data must be available to reviewers on
  request. APC (original research) is US$3,590 at acceptance.
- Declare related author work to the editor (npj policy): CrysMTM, R-CRYSTALS (under
  review), QuantumShellNet, HalluVerse25, IRIS. (Done in the cover letter.)

## 8. Integrity and next steps

- [ ] Co-author independently verifies all physics and the DFT protocol (blocking B1).
- [ ] Confirm the verifier split is source-disjoint (blocking B2).
- [ ] Independently re-derive Propositions 1–3.
- [ ] Fill every red-flag item (`matpcr_REDFLAGS.txt`).
- [ ] Re-run one focused novelty search the week of submission.
- [ ] Get 2–3 independent human mock reviews and resolve every issue.

This process raises the floor and removes self-inflicted rejection causes; it cannot make
the results stronger than they are. The results are the ceiling, and they are yours.
