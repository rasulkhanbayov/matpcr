# Revision plan: KBS R1

Analyses come before the text that reports them. Status key: `[x]` done · `[ ]` to do · `[?]`
needs author approval (cost, GPU, human labour or author decision) · `[-]` not done (reason given).

**Types:**
- **ANA**: new analysis on existing data, no cost
- **EXP**: new experiment (API / GPU)
- **HUM**: human labour
- **TXT**: text edit
- **FIG/TAB**: figure or table
- **REF**: references
- **FMT**: format / template
- **DOC**: Word deliverables

## Phase A: analyses on existing data (no cost)

| # | Item | Answers | Type | Where | Effort | Status |
|---|---|---|---|---|---|---|
| A1 | Precision CIs (Wilson, Clopper-Pearson) + unsure sensitivity (`exp21`) | R2.W3 | ANA | Table 1 | done | [x] |
| A2 | Coverage per cell + exclude/penalise/lenient conventions + rank τ (`exp22`) | R1.M4, R2.W5 | ANA | Results + SI table | done | [x] |
| A3 | Paired/unpaired model comparisons, Holm, effect sizes, MDE (`exp23`) | R2.W4, R2.W6 | ANA | Results, Discussion, SI table | done | [x] |
| A4 | Verifier per-family in-distribution + family-prior baseline (`exp24`) | R1.m2 | ANA | Verifier section + table | done | [x] |
| A5 | CGSV paired correctness, spectra (`exp25`) | R1.M3 | ANA | CGSV section + table | done | [x] |
| A6 | CGSV paired correctness, diffraction (`exp25 --modalities xrd`) | R1.M3 | ANA | same | after opXRD re-download (free, in progress) | [x] diffraction: 22.9%->28.6%, 14 gained/0 lost, p=0.0001 (exp25) |
| A7 | Class-conditional / class-balanced DFT PCR (`exp26`) | R1.M4 | ANA | Results + SI table | done | [x] |
| A8 | Measurement-uncertainty grounding of tolerances: opXRD 2θ step + peak FWHM, RRUFF sampling step + peak width (`exp27`) | R1.M2 | ANA | Methods (oracles) | ~1 h, needs opXRD | [x] XRD FWHM 0.12 deg vs 0.5 tol (≈3-4 px of rendered plot); Raman FWHM 16.9 vs ±5 (exp27) |
| A9 | Polymorph ambiguity within the MP batch: share of formulas whose polymorphs disagree on each oracle label (`exp28`) | R1.m1 | ANA | Methods (DFT) | ~30 min | [x] 10.9/15.6/16.1% of polymorphic formulas disagree (exp28) |
| A10 | Audit-provenance table (family, sampling/judging oracle version, date, n, reviewer) from project records | R2.W2 | TAB | Table 1 companion | ~30 min | [x] merged into Table 1 (version/date/n columns) |

## Phase B: items needing approval

| # | Item | Answers | Type | Cost / labour | Status |
|---|---|---|---|---|---|
| B1 | Re-run the three DFT arms for all 9 models on ONE common, class-balanced material set (e.g. 90 materials, with the near-hull class over-sampled) for a paired comparison | R2.W4, R1.M4 | EXP | ~US$10 API + ~2 GPU-h (local Qwen2.5-VL-7B) | [x] 8 models on common class-balanced set (7 API, $6.43 incl. taxonomy; local on CPU fp32); Terra>GPT-4o replicates (+0.085, Holm p=0.038); 7/28 pairs differ; Qwen3-VL-Thinking withdrawn by provider |
| B2 | Second independent annotator on a stratified subsample (e.g. 30 cases × 6 families = 180), Cohen's κ (`exp13`) | R2.W3 | HUM | ~3–4 h of a co-author's time | [x] second annotator done: κ 1.00 metallicity, 0.71 SEM, 0.63 magnetism, 0.33 XRD, 0.13 spectra; stability 14/14 agree on scored cases (exp37, Table S8); adjudication of 24 disputed cases pending (human) |
| B3 | Human audit of oracle-SILENT real responses (e.g. 30 per family) to estimate real-response recall | R1.M2 | HUM | ~3–4 h | [x] oracle-silent audit done: miss rate 0-6.7%, implied recall 0.81 (SEM)-1.00 (exp36, Table S8) |
| B4 | Re-run the violation taxonomy on the corrected spectrum + DFT audits (`exp10`) | R2.W2 | EXP | < US$1 API | [x] done (exp30, ≈$0.05): Table S5 |
| B5 | Full MP polymorph query (free API, MP key on file) to re-score DFT claims against the formula's ground-state polymorph | R1.m1 | EXP (data pull) | free, ~30 min | [x] done (exp28): verdict changes 10.4% stability, 10.5% metallicity |
| B6 | Retrain + publish verifier adapters so Code availability is true, or reword the statement | issue A | EXP | ~0.5 GPU-h | [x] 13 adapters retrained + saved (P100 fp32); in-dist AUC 0.850 reproduced; held-out shifts ≤0.08 reported (exp35, SI Note 2); staged in matpcr_hf/matpcr-verifier for upload |
| B7 | Cite requested refs 1 (sarcasm) and 4 (legal survey) | R2.W7 | REF | decision | [x] decision: cite all four (Introduction) |
| B8 | Paid Elsevier language-editing service | ED.1 | decision | paid | [?] still an author decision |

## Phase C: manuscript text (in `revised/`, every change wrapped in `\rev{}`)

| # | Item | Answers | Type | Where | Status |
|---|---|---|---|---|---|
| C1 | Rescope "reasoning-chain consistency" to "physical admissibility of stated quantities"; single-claim limitation stated up front | R1.M1 | TXT | title?, abstract, contributions, Intro, PCR section, Discussion | [x] |
| C2 | "What PCR adds" paragraph; accuracy-consistency gap partly definitional | R1.M1 | TXT | Accuracy vs consistency | [x] |
| C3 | Real-response recall unmeasured; Corollary use conditional everywhere; tolerance grounding (A8) | R1.M2 | TXT | Oracle validity, Methods, What oracle error does | [x] |
| C4 | CGSV: $b=0$ is structural; paired-correctness results (A5/A6) replace the "retreat" claim; soften attribution | R1.M3, R2.S3 | TXT+TAB | Effect of self-verification, Discussion, Fig. 2b caption, Alg. 1 text | [x] |
| C5 | Coverage + conventions (A2), class-balanced DFT (A7), aggregation stated | R1.M4, R2.W5 | TXT+TAB | Physical consistency of current models, Methods (PCR), SI | [x] |
| C6 | DFT tasks: formula-only design + polymorph ambiguity (A9/B5) | R1.m1 | TXT | Methods (DFT) | [x] |
| C7 | Verifier per-family table + family-prior baseline (A4) | R1.m2 | TXT+TAB | Verifier section, Table 4 | [x] |
| C8 | Remove revision-history narration and internal labels/paths; move the audit trail to SI Note | R2.W1 | TXT | Results, Discussion, Methods, Fig. 4 caption, Acknowledgements, Statistics | [x] |
| C9 | Audit-provenance table (A10) + consistent statements on oracle versions | R2.W2 | TAB+TXT | Table 1, Fig. 1c note, Methods taxonomy | [x] |
| C10 | Precision CIs + unsure sensitivity in Table 1; single-annotator limitation (+ κ if B2) | R2.W3 | TAB+TXT | Table 1, Methods | [~] κ and two-annotator precision done; consensus after adjudication pending |
| C11 | Replace interval-overlap reasoning with paired tests, Holm, effect sizes; explain image-arm pairing; diffraction comparisons provisional | R2.W4 | TXT+TAB | Results, Methods protocol/Statistics, SI table | [x] |
| C12 | MDE statement; bound the tier/generation claims or move them to limitations | R2.W6 | TXT | Discussion, Results, Table 2 caption | [x] |
| C13 | Related-work paragraph: CoT faithfulness & scientific CoT (refs 2, 3; 1 and 4 per B7) | R2.W7 | TXT+REF | Introduction | [x] |
| C14 | Fix issue B ($n$ per cell), issue C (MP retrieval dates), issue A (Code availability wording) | own | TXT | Results, Methods, Code availability | [x] |
| C15 | Language pass over all edited prose | ED.1 | TXT | throughout | [ ] |

## Phase D: format and deliverables

| # | Item | Answers | Type | Status |
|---|---|---|---|---|
| D1 | Convert manuscript + SI to `elsarticle` (preprint, review, 12pt; `elsarticle-num`); flat folder | ED.5, ED.7, issue D | FMT | [-] not done: authors chose to keep sn-jnl |
| D2 | Elsevier sections: CRediT, funding wording, GenAI declaration (exact wording), Declaration of competing interest, Data availability; abstract ≤ 250 words | GFA | FMT/TXT | [x] (sn-jnl kept per author decision; Elsevier wording for CRediT, competing interest, funding, GenAI) |
| D3 | Export every figure (incl. TikZ) as separate ≥ 300-dpi PNG/TIFF named Figure_N | ED.6 | FIG | [x] 5 figures as separate PNGs at 550-610 dpi (scripts/export_figures.py) |
| D4 | Highlighted build (`\rev` = blue) + clean build; latexdiff if available; compile check | user Step 5 | FMT | [x] highlighted + clean + latexdiff PDFs; pdflatex clean, 0 undefined refs (scripts/build_all.sh) |
| D5 | Response to reviewers (.tex + .docx) with editor summary letter | ED.2, ED.3 | DOC | [~] 1 pending marker: adjudication result |
| D6 | Highlights (.docx, 3–5 bullets ≤ 85 chars), cover letter (.docx), CRediT (.docx), declaration-of-interest draft (.docx), author-agreement draft (.docx, needs signatures) | ED.4 | DOC | [x] drafted .docx (author agreement needs signatures; declaration needs Elsevier tool) |
| D7 | Length toward the ~20 pp guideline: move long method/audit notes to SI | GFA | TXT | [ ] |

## Phase E: correction found by the second annotation (2026-10-16)

| # | Item | Answers | Type | Status |
|---|---|---|---|---|
| E1 | Stability prompt–oracle conflict: the prompt says "treat borderline/metastable as UNSTABLE", but the oracle required STABLE for E_hull ≤ 0.05. Fixed with a near-hull abstention band (0 < E_hull ≤ 0.05 not scored), same principle as metallicity (author decision: option A) | R2.W3, R1.M4 | ORACLE | [x] `matpcr_metrics.stability_claim_consistent` (+ smoke test), `experiments/final_oracle.py` |
| E2 | Re-score every stability-dependent number from existing data, no API cost. Covers Table 1/2, S1–S8, paired tests, coverage, class balance, accuracy-vs-consistency, polymorphs, tolerance sensitivity, Half-A. Original-rule outputs archived in `experiments/original_stability_rule/` and reported in Table S7 | — | ANA | [x] (`experiments/final_rule_logs/`, exp38, exp40) |
| E3 | Manuscript, SI (Note 2, S7, S8), Figures 3 and 5 and the response updated. Main changes: overall PCR 0.556–0.778; Terra>GPT-4o +0.072 (Holm p=0.045), but not significant on the paired DFT set; accuracy–consistency stability gap was entirely the band | — | TXT | [x] |
| E4 | Adjudication of the 24 disputed non-stability cases (`human_review/adjudication_*.html`) | R2.W3 | HUM | [~] awaiting both annotators |
