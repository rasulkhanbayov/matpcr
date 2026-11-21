# Human review tasks for the KBS revision

**Read `LABELING_GUIDELINES.md` (or `.docx`) before starting.** It gives the exact criteria for each
oracle family.

Two independent labelling tasks remain. Both pages are self-contained HTML files: open them in a
browser, label every case, then press **Export my review** and save the JSON from the text box.
No internet connection is needed.

## Task 1: second annotator for the precision audit (Reviewer 2, W3)

**Who.** Anyone except R.K., who was the first annotator. A co-author is fine. Do **not** look at
the first annotator's exports (`xrd.txt`, `sem.txt`, `*_halfB_review_2026-08-06.txt`) before you
finish.

**Pages.** `second_annotator_{xrd,sem,spectrum,stability,metallicity,magnetism}.html`. Each has 30
cases sampled at random, stratified by the first annotator's verdict; the sample is listed in
`second_annotator_sample.json`. Every case is one the oracle flagged as inconsistent.

**What to decide.** Is it a genuine physical violation of the stated constraint (**Real**), or an
oracle or parsing artifact (**False positive**)? Use **Unsure** sparingly.

**Time.** About 3–4 hours in total.

**Save as.** `second_annotator_<family>_review.json` in this folder.

**Compute agreement** (from the repo root, once per family):
```bash
python experiments/exp13_second_reviewer_kappa.py --family xrd \
    --reviewer_a xrd.txt --reviewer_b KBS_revision_R1/human_review/second_annotator_xrd_review.json
```
First-annotator files by family:

| Family | First-annotator file |
|---|---|
| xrd | `xrd.txt` |
| sem | `sem.txt` |
| spectrum | `spectrum_halfB_review_2026-08-06.txt` |
| stability | `stability_halfB_review_2026-08-06.txt` |
| metallicity | `metallicity_halfB_review_2026-08-06.txt` |
| magnetism | `magnetism_halfB_review_2026-08-06.txt` |

The script compares only the 30 overlapping cases.

## Task 2: oracle-silent audit (Reviewer 1, M2)

**Who.** Any domain-competent annotator. Mustafa Kurban for the three DFT families would be ideal.

**Pages.** `oracle_silent_{xrd,sem,spectrum,stability,metallicity,magnetism}.html`. Each has 30
real responses that the oracle judged **consistent**, sampled at random; the sample is listed in
`oracle_silent_sample.json`.

**What to decide.** Did the oracle miss a genuine physical violation? Each page's header explains
the criterion for that family. "Imprecise" or "a different peak is stronger" is **not** a missed
violation; physically inadmissible is.

**Time.** About 3 hours in total.

**Save as.** `oracle_silent_<family>_review.json` in this folder.

**Summarize** (from the repo root):
```bash
python experiments/exp36_oracle_silent_summary.py --exports KBS_revision_R1/human_review
```
This gives the miss rate (Wilson 95% CI) and the implied real-response recall per family.

## After both tasks
Enter the results into `KBS_revision_R1/response/pending_values.json`. The keys are `R2W3_kappa`
and `R1M2_silent`. Then replace the two `\redflag{...}` placeholders in
`revised/submission/matpcr_snjnl.tex`: the Oracle validity paragraph and Methods (ii) human
agreement. Finally, run:
```bash
bash KBS_revision_R1/scripts/build_all.sh && bash KBS_revision_R1/scripts/make_package.sh
```


## Task 3: adjudication (both annotators together)

The two annotators disagree on 24 of the 150 subsampled cases outside stability (diffraction 9,
microscopy 2, spectra 11, magnetism 2; metallicity had none). The 13 stability disagreements need no
adjudication: they are all near-hull materials, which the final stability oracle does not score.

**Pages.** `adjudication_{xrd,sem,spectrum,magnetism}.html`. Each case is shown exactly as both
annotators saw it, with both labels.

**What to decide.** Discuss each case using `LABELING_GUIDELINES.md` and record one consensus label,
with a short reason if useful.

**Time.** About 1 hour.

**Save as.** `adjudication_<family>_review.json` in this folder. Then tell Claude, who will compute
the consensus precision and fill the last placeholder in the manuscript and the response.
