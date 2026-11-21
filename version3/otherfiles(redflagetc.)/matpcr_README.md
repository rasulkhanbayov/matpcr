# MatPCR — README (finalization pass, 2026-08-06)

Entry point to the submission bundle for **npj Computational Materials** (Article).
This pass reconciled every claim to the reported numbers, verified the numbers that could
be recomputed, corrected four venue-compliance failures and five factual or figure errors,
split the Supplementary Information into its own file, and put every remaining gap in red
in the manuscript. The itemised list is `matpcr_REDFLAGS.txt` — read that first.

---

## 1. What the paper claims now

**One sentence.** Materials data carries its own physics, so a model's *reasoning chain*
can be checked for physical consistency without human labels; DFT references extend that
check from geometry to computed physics; the same signal drives a self-verification loop
and trains a released verifier.

**Headline results** (all internally verified — see §5 on provenance):
- **Oracle validity (Table 1).** Positive control recovered every planted violation for all
  six oracle families at every planted rate (FN rate 0.0000). Audited precision 77.2% (XRD),
  88.6% (SEM), 95.3% (stability), 94.7% (metallicity), 92.2% (magnetism). The spectrum
  figure (72.8%) is from the *superseded* oracle; the revised oracle has no audit yet (red flag A1).
- **PCR across 8 models (Table 1).** Overall 0.555 (Qwen3-VL-8B-Instruct) to 0.774
  (GPT-5.6-Terra). Microscopy easiest (0.67–1.00); spectra and diffraction hardest and most
  model-dependent. DFT column tightly clustered (0.64–0.74).
- **Accuracy vs consistency.** Mean 22.2% item-level disagreement across 12 cells — PCR is
  not answer accuracy renamed. One model's near-ceiling raw stability accuracy is a
  base-rate artefact: balanced accuracy drops three of four models to near chance.
- **CGSV (Table 3).** Zero regressions (b=0) in every cell; significant for all four models,
  surviving Holm correction. Two mechanism-isolation controls (unaided self-refinement
  p=0.615, equal-compute re-prompting p=0.20) are null and both show regressions. This is
  the paper's strongest single result. Scope note: with one checkable claim per item, a gain
  cannot come from the model dropping a claim, but it can still come from retreating to a
  trivially admissible value; post-CGSV accuracy would separate the two (red flag A13).
- **Verifier (Table 2).** Useful in distribution (AUC 0.850, source-disjoint split).
  **Five** of six held-out constraint types are indistinguishable from chance; metallicity
  (AUC 0.582, CI [0.510, 0.652]) separates from chance only *before* correcting for the six
  comparisons, and not after (Bonferroni interval [0.486, 0.678]). The earlier "magnetism
  generalises" claim (AUC 0.867) is retracted as a record-level leak artefact; 0.503 corrected.

**Contribution (5 parts).** (1) Reframe evaluation to chain-level physical consistency,
label-free, across image and structure inputs. (2) MatPCR's programmatic and DFT-grounded
oracles. (3) PCR with bootstrap CIs, an exact paired test, and measurement guarantees.
(4) A released verifier, benchmarked against LLM-judge and self-confidence baselines.
(5) CGSV, with its mechanism isolated from generic self-reflection and extra compute.

## 2. What this pass changed

**Venue compliance** (verified against the journal's Content Types page, 2026-08-06):
title 21→12 words with the colon removed (limit 15, no punctuation); abstract 181→147 words
(limit 150); Supplementary Information split into `matpcr_SI.tex` as the journal requires;
the missing funding statement flagged where the journal requires it.

**Factual and figure errors** (each verified, not stylistic):
- "API models trained after mid-2026 (GPT-5.6-Terra, **Claude Opus 4.6**)" was false —
  Opus 4.6 shipped February 2026. Corrected, and the "current-generation" framing changed
  to "later-generation" throughout with an explicit currency caveat.
- Figure 2b's "all p < 1e-4" was false (Gemini p = 2.4e-4) → "all Holm-adjusted p < 1e-3".
- Figure 2a's heatmap shading followed a power law while its colour bar was linear, so
  every cell read wrong against the legend. All 40 fills recomputed on a matching scale.
- Figure 2c's "chance" label overprinted the Magnetism confidence interval. Moved.
- Figure 1's micrograph card had illegible white-on-light scale-bar text and a label
  painting over its own arrow. Both fixed.
- The CGSV table was 55 pt overfull; now inside the text block.

**Deep audit** (overclaim, hallucination, theory, notation, prose). The largest finding: the
paper claimed the verifier transfers to *none* of six held-out constraint types, while its own
Table 2 gives metallicity a 95% interval of [0.510, 0.652], which excludes chance — and the
Results paragraph said both things two sentences apart. Now resolved honestly (five at chance;
metallicity nominal only, gone after multiplicity correction), including a third colour state
in Fig. 2c. Also corrected: the CGSV correction-vs-retraction claim, an unsupported "well
below" margin, an implicitly paired MatterChat comparison, an unhedged negative existential,
an "assumption-light" claim that Proposition 2's independence assumption contradicts, a
shipped author-facing editing note, an undefined symbol in Proposition 4, and two em dashes.

**Figure 2 redesigned** for the venue: panel a now shows all six constraint types instead of
duplicating Table 1's pooled DFT column (revealing within-DFT divergence the table hides), panel b
draws the two mechanism-isolation controls alongside the CGSV slopes, and panel c adds the two
comparator baselines that appeared in no figure. Restructured to a stacked page-width layout sized
to the true 13.08 cm text width so nothing is downscaled, Wong colourblind-safe palette, a) b) c)
panel labels, horizontal headers and colour bar.

**A provenance contradiction was found and is now the top open item.** The Results said no human
reviewer had completed the DFT precision pass; Table 1 reports audited percentages with sample sizes
for exactly those three families, four lines away. Both cannot be true, and every DFT-grounded number
in the paper inherits the answer. Red flag A18, blocking. Also found: a second author-facing note that
had shipped into a caption, a Discussion parenthetical still asserting the retracted "does not
generalize at all", and a Discussion claim that both verifier baselines are "near or below chance"
when the LLM judge reaches 0.735 held out on microscopy — above anything the fine-tuned verifier
achieves out of distribution.

**Theory reduced to what is load-bearing.** The main body carried four propositions; three were
textbook results that were not carrying the argument, and one of them (the total-error bound) was
actually *looser* than the bootstrap intervals already reported. Proposition 1 and Corollary 1 — the
exact oracle-bias identity and its one-sided consequences — stay in the main body, because they are
the formal reason the validity gate runs first. The rest became one sentence each of Methods prose or
moved to Supplementary Note 1.7. Theory is now 6.5% of the manuscript with two proofs, and the
abstract and contributions were rewritten to match.

**Manuscript deep-audited again**: removed an unsupported "pre-registered" claim (contradicted by
the paper's own mid-project oracle revisions), an unsourced "roughly a fifth" figure pointing at a
Methods passage that does not contain it, a claim that six of seven models "substantially outperform"
the local model on microscopy when one interval overlaps, a contradiction with the Introduction's
MicroscopyGPT citation, and a mis-pointed item-count total. The authors' own-DFT claim is withdrawn
pending a statement, since this journal requires a full protocol if any own calculation entered a
result.

**Figures audited against the text**: Figure 1b showed the CGSV loop collecting a microscopy
violation, but CGSV runs on diffraction and spectra only; Figure 2c coloured two below-chance
baselines as "at chance"; Figure 3a implied all eight models entered the CGSV arm; and constraint
colours disagreed between Figures 1 and 3. All corrected. Every plotted value in all three figures
now traces to the manuscript, and Figure 2a's 48 cells and 8 overall values reconcile exactly to
Supplementary Table S1.

**Figure 1 redesigned**: panel b no longer duplicates the Figure 3 pipeline and instead shows the
claim-level audit (three claims, three oracles, three verdicts, clearly marked schematic); a new
panel c plots the violation taxonomy, the figure-level answer to "are these real physical errors";
and panel a's cards now state the rule that makes each quantity checkable. All figure text was
switched to sans-serif — 236 node font specifications were silently overriding the picture-level
`\sffamily` and rendering in the body serif face across all three figures.

**Figure 3 redesigned** and, more importantly, **cited**: it was previously an orphan with no
`\ref` anywhere in the text. Panel a now includes the oracle-validity gate (which appeared in no
figure at all) and names the real sources, oracles, sample and outputs; panel b's four quadrants
carry the empirical finding of which constraint type populates each; and a new panel c quantifies
the accuracy-consistency disagreement by constraint type against the 22.2% mean.

**Theory verified** symbolically (sympy) and numerically: Propositions 1–4, Corollary 1, and
the (1−π)(1−PCR) understatement identity all check out, with no error in any statement, proof
step, or assumption. Full list in `matpcr_REDFLAGS.txt` §C.

## 3. How to build

```
pdflatex matpcr_snjnl.tex
bibtex   matpcr_snjnl
pdflatex matpcr_snjnl.tex
pdflatex matpcr_snjnl.tex

pdflatex matpcr_SI.tex        # Supplementary Information, twice for the table refs
pdflatex matpcr_SI.tex
```

Compiles with the bundled `sn-jnl.cls` and `sn-nature.bst` in the same directory: **no
errors, no undefined or multiply-defined citations, worst overfull box 7.2 pt**, 27 pages
main + 3 pages SI. A precompiled `matpcr_snjnl.bbl` ships so one `pdflatex` pass resolves
references without BibTeX.

Where each claim lives: framing in the Abstract and the boxed Contributions; oracle-validity
gate and PCR in Results; oracles and the metric in Methods; Propositions 1–4 and Corollary 1
(the novel theory) in Methods → Measurement guarantees; standard derivations in
Supplementary Note 1.

## 4. What you must still do

`matpcr_REDFLAGS.txt` is authoritative. Summary:
- **19 red flags visible in the PDF** (pages 5, 7, 8, 9, 14, 18, 19, 21×2, 23×4). The two that
  affect a reported number are **A1** (no precision audit exists for the spectrum oracle
  actually used), **A3** (the 61/62 stability count does not reconcile with n=90 or with the
  reported balanced accuracy of 0.494), and **A13** (post-CGSV accuracy, needed to separate
  correction from retreat).
- **A11 is a compliance blocker**: funding must be declared in Acknowledgements.
- **Two bib entries carry `% VERIFY`** (Mat-Pref, VPRMs) — author lists unconfirmed.
- **One strategic decision, §E of the red-flag file: venue fit.** This is now the largest
  risk to the paper. A presubmission enquiry to the editor is the cheap way to resolve it.

## 5. Provenance of the numbers — read this

No raw per-item outputs or results CSV were supplied. Every number was therefore checked by
**independent recomputation from the manuscript's own data** and passed: Table 1's DFT and
All columns reconcile exactly to Supplementary Table S1's 48 cells; the record total
recomputes to 3,973; all six McNemar p-values, all six Holm-adjusted values, all six F1
values and every CGSV delta recompute; every audited-precision cell resolves to an integer
count at its stated n. That is strong internal evidence and **not** reproduction from source.
Treat the headline numbers as *internally verified, provenance taken on trust*. To close
this, deposit the per-item oracle outputs and rebuild Tables 1–3 from them.

## 6. Code

`matpcr_metrics.py` (numpy only): geometric and DFT-grounded checkers, PCR, bootstrap CIs,
exact McNemar, Holm and Benjamini–Hochberg correction, Cohen's kappa, ROC AUC, verifier
evaluation, and `pcr_total_error_bound()` implementing Proposition 2. Run the smoke test:

```
python3 matpcr_metrics.py
```

All checks pass. These are synthetic demonstrations of estimator behaviour, **not** results.

## 7. Venue specifics (npj Computational Materials, verified 2026-08-06)

- Article structure: Title page, Abstract, Introduction, Results (subheadings), Discussion
  (**no subheadings, no limitations or conclusions section**), Methods (subheadings, all in
  the main file), Data availability (mandatory), Code availability, Acknowledgements
  (**funding goes here; a separate Funding statement is not permitted**), Author
  contributions, Competing interests, References. The manuscript matches.
- Title ≤15 words, free of punctuation. Abstract ≤150 words. References ≤60 (51 cited).
  Figure legends ≤350 words (longest is 154). All now within limits.
- Supplementary Information must be a **single separate file, preferably PDF**. Now split out.
- No strict word or page limit (online-only, fully open access).
- **Single-anonymised review**: submit with author names visible; do NOT anonymise.
- AI use disclosed in Methods; LLMs are not authors; the human authors take responsibility.
- Related author work must be declared to the editor (see red-flag B5).

## 8. Integrity and next steps

- [ ] M.K. independently validates all physics and the DFT protocol (DFT/All columns are
      marked provisional until then).
- [ ] Independently re-derive Propositions 1–4 and Corollary 1.
- [ ] Fill or run every A-item and B-item in `matpcr_REDFLAGS.txt`.
- [ ] Resolve the venue-fit decision (§E) — presubmission enquiry recommended.
- [ ] Re-run one focused novelty search the week of submission.
- [ ] Get 2–3 independent human mock reviews and resolve every issue raised.

This process raises the floor and removes self-inflicted rejection causes. It cannot make
the results stronger than they are. The results are the ceiling, and they are yours.
