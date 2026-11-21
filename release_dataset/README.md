# MatPCR — data repository

This folder is the upload target for the manuscript's **Data availability**
statement (`version3/matpcr_snjnl.tex`): "The assembled MatPCR items, the
oracle reference values with their provenance, and the item-construction
code will be made available..." (the item-construction *code* lives in the
separate `release_code/` folder; this folder is the assembled items and
reference-value provenance themselves).

## Contents

- `experiments/*.jsonl` — every real model-call/oracle-check record
  produced across the study: pilot runs, Half-A/Half-B collection
  (`halfB_fired_cases.jsonl`, `halfB_dft_fired_cases.jsonl`), the main PCR
  sweep (`exp2_results*.jsonl`, including the Panther Tier 1/Tier 2 re-runs
  and the GPT-5.6-Sol flagship addendum), accuracy-vs-consistency
  (`exp3_results.jsonl`), CGSV before/after (`exp4_results.jsonl`,
  `exp7_results.jsonl`), the verifier's training dataset and per-item test
  scores (`exp5_verifier_dataset.jsonl`, `exp5_results*.jsonl`), and the
  verifier-baseline/prompt-sensitivity follow-ups (`exp8`–`exp18`).
- `experiments/mp_provenance.json` — the Materials Project pull's exact
  provenance record (database version, retrieval date, calculation type,
  and fields pulled) for every DFT-grounded reference value used.
- `xrd.txt`, `sem.txt`, `spectrum_halfB_review_2026-08-06.txt`,
  `stability_halfB_review_2026-08-06.txt`,
  `metallicity_halfB_review_2026-08-06.txt`,
  `magnetism_halfB_review_2026-08-06.txt` — the human manual-review
  exports underlying every precision number reported in Table 1
  (Experiment 1's Half-B gate), one file per oracle family, each a
  bare-token-quoted JSON export from the corresponding
  `experiments/halfB_review_*.html` review page. Spectrum's export
  (dated 2026-08-06, $n=495$, precision 92.7\%) supersedes an earlier
  pre-revision review done under the since-corrected oracle (archived at
  the repo root's `archive/spectrum_OBSOLETE_precorrection_oracle_2026-08-01.txt`,
  not included here).

## What is NOT here

The raw third-party corpora these items were built from (opXRD, 92,552
patterns; NFFA-EUROPE, 18,424 images; RRUFF Raman spectra; Materials
Project reference materials) are NOT re-hosted here — they remain available
from their own original public sources, cited in the manuscript's
References and Data availability sections. Re-distributing them here would
duplicate an existing, more authoritative public copy rather than add one.

## Provenance and reproducibility

Every record in every `.jsonl` file here carries a `source_file` or
`material_id`/`source_id` field pointing back to the specific item in the
original public dataset it was drawn from — this is what lets a record be
independently re-checked against the oracle in `release_code/` without
re-running any model.
