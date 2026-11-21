# Review triage: KBS major revision (R1)

Each comment was checked against the submitted manuscript
(`original/submission/matpcr_snjnl.tex`, cited as `tex:line`) and, where it concerns
results, against the committed records and code in `experiments/`. New analyses written for
this triage are named `expNN`. Every number below comes from running one of them.

**Verdicts:**
- **Valid**: the issue is real and must be fixed.
- **Partial**: part of the comment is right and part is not.
- **Already**: the paper already does this.
- **Wrong**: the reviewer describes something the paper does not say.
- **Out of scope**: we disagree, for a stated reason.

## Summary

| Source | Comments | Valid | Partial | Already | Wrong | Out of scope |
|---|---|---|---|---|---|---|
| Editor | 7 | 7 | 0 | 0 | 0 | 0 |
| Reviewer 1 | 4 major + 2 minor | 6 | 0 | 0 | 0 | 0 |
| Reviewer 2 | 7 weaknesses | 4 | 3 | 0 | 0* | 0 |

\* R2.W4 contains one factually wrong premise (see below), so it is scored "Partial".
Neither reviewer hallucinated a number, section or reference. Every page-, figure- and
table-level pointer we could map to the source matches the manuscript.

**Problems we found ourselves** (no reviewer raised these; we will fix them):
- **A.** Code availability says the "released verifier weights" are online. They are not:
  `exp5_train_verifier.py` never saved the adapters (fixed in the code release; the weights
  must be retrained).
- **B.** "$n=30$ items per (model, constraint-type) cell per seed" (`tex:494`) is not true
  for diffraction. Only 64 of 90 attempted diffraction items per cell had an oracle
  reference (`exp22`).
- **C.** Methods gives the MP retrieval date as 2026-07-16 (`tex:1120`), but the Table 2
  DFT sweep used the batch retrieved 2026-08-05 (`mp_provenance.json`). The Half-B DFT
  audit used the 2026-07-16 pull. All 210 Half-B materials are present in the 2026-08-05
  batch.
- **D.** Template and format: the manuscript uses Springer `sn-jnl`, but KBS uses
  `elsarticle`. It runs about 29 pp against a ~20 pp guideline.

---

## Editor

| ID | Short quote | Verdict | Evidence | Proposed action |
|---|---|---|---|---|
| ED.1 | "use the English Language Editing service" | Valid | Some long, nested sentences (e.g. `tex:615`, `tex:1616`) | Full language pass by us. Using the paid Elsevier service is an author decision. |
| ED.2 | "point-by-point response to each comment" | Valid | n/a | `response/response_to_reviewers` (.docx + .tex) |
| ED.3 | "list of changes or a rebuttal against each point" | Valid | n/a | Change list in the response letter, plus a highlighted manuscript |
| ED.4 | cover letter, response, highlights, CRediT, author agreement, declaration in Word | Valid | n/a | Generate the .docx files. Author agreement and declaration need author signatures / Elsevier tool |
| ED.5 | "Source file ... Word or Latex", one final manuscript | Valid | n/a | LaTeX source, single manuscript file |
| ED.6 | tables/figures/equations editable; figures 300 dpi, not PDF | Valid | 4 TikZ figures + 3 PDF figures (`tex:201,423,770,1159,1420`) | Tables and equations already LaTeX. Export every figure as 300-dpi PNG/TIFF |
| ED.7 | include .bib for LaTeX | Valid | n/a | Ship `.bib` + `.bbl` in a flat folder |

## Reviewer 1

| ID | Short quote | Verdict | Evidence | Proposed action |
|---|---|---|---|---|
| R1.M1 | "Checking individual claims is not the same as evaluating a reasoning chain... one checkable claim (p. 18)"; accuracy–consistency partly reflects different tolerances | **Valid** | `tex:1371-1373` states $k_i=1$ for every item. The accuracy criteria are tighter tolerances or the MP `is_stable` label (`tex:561-567`), so part of the disagreement is by construction. | Rescope every claim from "reasoning-chain consistency" to "physical admissibility of the quantities a chain states" (title, abstract, contributions, Discussion). State that multi-claim chains are future work. Add an explicit "What PCR adds" paragraph: no labels; defined where no accuracy key exists (microscopy, magnetism); an admissibility floor is distinct from closeness. State that the accuracy–consistency gap is partly definitional. |
| R1.M2 | planted-violation recovery ≠ misses on real responses; dependence on criteria (XRD precision, ranking reversal p. 25); validate vs measurement uncertainty; guarantee must stay conditional | **Valid** | Half-A plants violations only (`tex:348-355`). Real-response recall is never estimated. `tex:1553-1555` already concedes $\hat f$ needs oracle-silent samples. Ranking reversal at `tex:1715-1722`. | (a) State plainly that real-response recall is unmeasured. Make Corollary use conditional everywhere (Results `tex:352-355`, abstract). (b) Human audit of a sample of oracle-silent real responses per family to estimate misses (**human labour, needs authors**). (c) New `exp27`: ground tolerances in measurement data (opXRD 2θ step and peak FWHM; RRUFF Raman sampling step and peak width). (d) Mark diffraction comparisons as tolerance-sensitive. |
| R1.M3 | PCR gains are scored by the same checks; "zero regressions also follow from the stopping rule"; "retreat" not supported by final accuracy < PCR; want paired correctness | **Valid** | Algorithm 1 breaks at the first consistent round (`tex:1401`; `exp4_cgsv.py:212`). A consistent item is never revised, so $b=0$ is structural, yet `tex:616-618,1042,1390` present it as a finding. The retreat claim (`tex:645-649`) compares unpaired aggregates. **New `exp25` (spectra, n=293)**: accuracy 0.058→0.099, 14 gained vs 2 lost, McNemar p=0.0042. Of 48 revised items that became consistent, 11 became accurate and 37 moved to an admissible but inaccurate value. Diffraction run pending (opXRD re-download). | Rewrite: $b=0$ is a property of the loop, not evidence. Replace the retreat claim with the paired correctness results (gained/lost, McNemar, corrected / admissible / unresolved, distance moved). Soften "attributing the gain to the oracle signal" accordingly. |
| R1.M4 | checkable share changes with wording; few stable structures; coverage/class balance/aggregation should be explicit | **Valid** | **New `exp22`**: coverage ≥0.93 in every cell except GPT-4o×spectra (0.489). The model order is stable across exclude/penalise/lenient conventions (Kendall τ 0.889 / 1.000), but GPT-4o drops 3rd→5th when silence counts as a violation. **New `exp26`**: pooled stability PCR is base-rate driven, e.g. Qwen2.5-VL-7B 0.744 pooled but 0.045 on near-hull (balanced 0.508); GPT-5.6-Terra lowest pooled (0.656) but highest balanced (0.689). | Add a coverage table + conventions (SI) and a sentence in Results. Add class-conditional and class-balanced PCR for the DFT types (SI table + Results). State that the DFT column ordering is not robust to class balancing. |
| R1.m1 | how DFT task info identifies the reference structure; same composition, different properties (p. 16) | **Valid** | Prompts give only `{formula}` (`pilot_dft.py` PROMPTS). The oracle scores against one specific `material_id`. In the 3,000-material batch, 540 of 1,869 formulas occur more than once. | State the formula-only design explicitly. Quantify polymorph ambiguity: how often polymorphs of one formula disagree on each oracle label. Within-batch analysis possible now. A full MP polymorph query (free API) would let us re-score against the formula's ground-state polymorph (**needs approval: new data pull**). |
| R1.m2 | pooled verifier performance gives limited insight; per-family results (p. 11) | **Valid** | **New `exp24`**: in-distribution AUC by family: SEM 0.922, stability 0.804, magnetism 0.728, XRD 0.696 (CI to 0.49), metallicity 0.582, spectra 0.513. A family-prior-only baseline already reaches pooled AUC 0.759 vs the verifier's 0.850. | Add a per-family table. State that the pooled 0.850 is partly family base-rate separation. Narrow the claimed in-distribution usefulness to the families where it holds. |

## Reviewer 2

| ID | Short quote | Verdict | Evidence | Proposed action |
|---|---|---|---|---|
| R2.S1–S3 | strengths | n/a | n/a | Thank the reviewer. Note that S3's "improvement is mostly retreat" is the statement R1.M3 asks us to revise: the response explains the change. |
| R2.W1 | manuscript narrates internal revision history; internal labels/paths (Fig. 4 caption, Acknowledgements, Statistics paragraph) | **Valid** | "supersede an earlier pass" `tex:495-501,569-570,577-579,615,700,704-711,721-731`; retraction narrative `tex:1053-1060`, Discussion `tex:1032-1034`; "Half-B" `tex:1352`; "Experiment 1--4" `tex:1838`; file names `tex:673,1780-1782`; internal audit reference `tex:1787-1789` | Report final-protocol results only. Move the audit trail to a short SI note. Remove internal labels and paths. |
| R2.W2 | incompatible accounts of which oracle version each audit was judged against | **Valid** | Fig. 1c note (`tex:331`) and Methods taxonomy (`tex:1745-1748`) say the spectrum/DFT reviews "predate" the final oracles. Table 1 caption (`tex:461-464`) and Results (`tex:366-382`) report audits under the corrected oracles. Project records: the spectrum (n=495) and DFT (107/114/115) audits were redone on 2026-08-06 under the corrected oracles; the taxonomy predates that redo. | Add an audit-provenance table (family, sampling oracle version, judging oracle version, audit date, n, reviewer). Fix the taxonomy statements: the taxonomy covers XRD/SEM because it was computed before the spectrum/DFT re-audit. Re-run the taxonomy on the new audits (**small API cost**) or keep XRD/SEM only with the corrected reason. |
| R2.W3 | single annotator; no agreement; unsure excluded; small samples; want 2nd annotator, κ, intervals, unsure sensitivity | **Partial (addressable except the 2nd annotator)** | Single annotator stated at `tex:1741-1744`. **New `exp21`**: Wilson 95% CIs, e.g. XRD 0.772 [0.681,0.843], SEM 0.886 [0.811,0.933], spectra 0.927 [0.901,0.947], DFT 0.953/0.947/0.922. Unsure cases exist only in spectra (2/495): bounds 0.923–0.927. | Add CIs + unsure sensitivity to Table 1. A second independent annotator on a subsample per family (`exp13` ready) is **human labour, needs authors**. |
| R2.W4 | models not compared on a common item set; interval-overlap reasoning; no multiplicity correction; diffraction ranking reverses | **Partial: one premise wrong** | **Wrong for image arms**: all nine models received the same 30 items per seed (builder seed 2000+100s; verified, item sets coincide across models). **Right for DFT arms**: each (model, seed) drew a disjoint 30-material block. **Right** that claims rest on CI overlap (`tex:507-515,1021-1027`). **New `exp23`** (paired McNemar on image arms, Fisher/bootstrap on DFT, Holm): Terra − GPT-4o +0.081 [0.026,0.137], Holm p=0.022. Opus−Sonnet, Thinking−Instruct, Sol−Terra all non-significant (MDE₈₀ 0.064–0.071). Microscopy: 6 of 7 pairs vs Qwen2.5-VL-7B significant after Holm, Qwen3-VL-Instruct not (p_Holm=0.12). 21 of 36 overall pairs significant after Holm. | Replace overlap reasoning with these tests (+ effect sizes, MDE). Explain the paired design of the image arms. Mark diffraction comparisons provisional. A common DFT item set needs **new API/GPU runs** (est. ~US$10 + ~2 GPU-h), or state DFT comparisons as unpaired. |
| R2.W5 | checkable share never reported; non-checkable excluded so a model can score by saying less | **Valid** | PCR over $\mathcal{C}$ only (`tex:1363-1367`). **`exp22`** as in R1.M4. | Same as R1.M4. Define the convention and report ordering under exclude/penalise/lenient. |
| R2.W6 | small differences discussed as findings; state smallest detectable difference; effect sizes; bound or move to future work | **Valid** | Tier/generation claims `tex:1020-1032`. **`exp23`**: overall MDE₈₀ = 0.064–0.078 per pair. Per-type MDE₈₀ is 0.11–0.20. | State the MDE. Report effect sizes with CIs. Recast the three null comparisons as "no difference larger than ~0.07 detectable" and move the tier/generation interpretation to limitations/future work. |
| R2.W7 | add and discuss four specific recent studies | **Partial** | All four exist (verified, `reference_check.md`). 2 (CoT-Evo) and 3 (FaithCoT-Bench) are directly relevant (the Introduction already raises faithfulness, `tex:142-146`). 1 (sarcasm in LVLMs) and 4 (legal knowledge infusion) are only loosely related and share an author (Hang Yu). | Add a short related-work paragraph on CoT faithfulness/scientific CoT (2, 3) and on evaluation beyond final answers / domain-knowledge checking. Including 1 and 4 is an **author decision**. |
