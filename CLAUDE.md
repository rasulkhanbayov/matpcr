# CLAUDE.md — MatPCR Project

Working notes for this repository. Captures the project, data, code, experiments,
and current status so any session can resume without re-briefing.

---

## 1. The project in one line
Build and prove a **label-free, physics-based** way to measure whether a
vision-language/language model's **reasoning** about materials data respects
physics — then measure it, improve it, and release the tool.

## 2. Topic / motivation
VLMs and LLMs are increasingly used to interpret materials data (XRD patterns,
SEM/TEM images, spectra). Existing evaluation only checks the **final answer**
against **human labels**, or (in discovery agents) verifies final proposals / DFT
execution. **None** measure whether the model's **reasoning chain** is physically
consistent. MatPCR fills that gap using **physics itself as the label** — no human
annotation.

## 3. The contribution (5 parts)
1. Reframe evaluation to **physical consistency of the reasoning chain**, across
   image and structure/text inputs.
2. **MatPCR**: programmatic oracles (Bragg, scale bar, spectral peak) + **DFT-grounded**
   oracles (stability vs convex hull, metallicity, property sign/magnitude) — all label-free.
3. **PCR** (Physical-Consistency Rate) metric, with bootstrap CIs and a paired
   significance test (exact McNemar).
4. A fine-tuned, **released physical-consistency verifier** (the citable artifact).
5. **CGSV**, a label-free agentic self-verification (self-correction) loop.

## 4. Venue
**npj Computational Materials** (Nature Portfolio). NOT core Nature — that requires
experimental wet-lab validation the team does not have. The folder name says
"Nature_submission" but the real target is npj Comp Mat. Fully open access;
check APC/waiver. Manuscript uses the official Springer Nature `sn-jnl` class.

## 5. People / roles
- **Hasan Kurban** — co-corresponding author, coordinator/PI (hkurban@hbku.edu.qa,
  Hamad Bin Khalifa University, Doha). Sends the assignment emails.
- **Mustafa Kurban** — co-corresponding author; **validates the DFT-grounded oracles**
  (functional, k-points, convergence, tolerances, hull & band-gap definitions;
  provides reference DFT values). (mkurbanphys@gmail.com, Ankara University)
- **Rasul** (the user, barhdadirayan01@gmail.com) — **runs the experiments**.

---

## 6. Files in this folder
| File | Role |
|------|------|
| `matpcr_README.md` | Project guide — read first. Claims, venue strategy, build/run, integrity checklist. |
| `matpcr_runbook.txt` | Experiment protocol in run order; gates, flag-back triggers, submission checklist. |
| `matpcr_metrics.py` | **The only code.** numpy-only oracles + metrics + synthetic smoke test. |
| `matpcr_snjnl.tex` | Manuscript source (official `sn-jnl` class). |
| `matpcr_snjnl.pdf` | Compiled proof (455 KB; built vs a PATCHED community mirror — recompile on Overleaf with official files for real submission). |
| `matpcr_snjnl.bbl` | Precompiled bibliography. |
| `matpcr_refs.bib` | References — contains `% VERIFY` entries that MUST be checked against sources. |
| `matpcr_cover_letter.txt` | Confidential editor cover letter. |
| `matpcr_submission.zip` | Self-contained source bundle. |
| `sn-jnl.cls`, `sn-nature.bst` | Third-party Springer Nature LaTeX template/style. |
| `opxrd/` | **Downloaded dataset** (see §9). |

Build the paper: `pdflatex → bibtex → pdflatex → pdflatex`.

## 7. The code — `matpcr_metrics.py` (numpy only)
- **Geometric oracles:** `two_theta_to_d`, `xrd_peak_consistent`,
  `sem_feature_size_consistent`, `spectrum_peak_exists`.
- **DFT-grounded oracles:** `stability_claim_consistent`, `metallicity_claim_consistent`,
  `property_sign_magnitude_consistent`.
- **Metric:** `physical_consistency_rate`, `violation_rate_by_type`.
- **Stats:** `bootstrap_ci`, `mcnemar_exact`, `roc_auc`.
- **Verifier eval:** `precision_recall_f1`, `expected_calibration_error`.
- `ItemResult` dataclass = one benchmark item after checking (consistent, n_checks,
  n_violations, constraint_type, flagged).
- **Smoke test** at bottom: SYNTHETIC data, demonstrates estimators recover planted
  values. It is a correctness demo, NOT a result. Run: `python matpcr_metrics.py`.

### Smoke-test status: PASSES ✅ (run this session)
- Bragg: 2θ=28.44° → d=3.1358 Å (expected ~3.13) ✓
- PCR recovered planted 0.70 → 0.699, CI [0.673, 0.726] ✓
- McNemar: fixes=172, regressions=22, p=5e-30 ✓
- AUC=0.778 ✓; verifier P/R/F1=1.0 ✓
- **Note:** ECE=0.254 (high) is EXPECTED — the smoke test plants probabilities that
  don't match its 100% accuracy. Not a bug. Perfect-F1-but-mediocre-ECE is by design.
- Cosmetic: violation-rate dict prints `np.str_('...')` wrappers — harmless numpy repr.

---

## 8. CRITICAL RULES (from README + runbook)
1. **THE ORACLE MUST BE RIGHT BEFORE ANY MODEL IS RUN.** The whole contribution
   rests on the checkers being correct. Do **Experiment 1** (the gate) first.
2. **EVERY NUMBER IN THE PAPER IS A PLACEHOLDER UNTIL MEASURED.** Never fill a table
   from intuition or the smoke test. Fill only from real runs; then reconcile
   abstract/title/contributions to what the data shows.
3. Fill every `% VERIFY` citation by reading the source — never invent authors.
4. Co-author independently verifies ALL physics. The assistant only drafted; the
   humans are the authors.
5. Get 2–3 independent human mock reviews before submission.
6. Declare related author work to the editor (CrysMTM, R-CRYSTALS, QuantumShellNet,
   HalluVerse25, IRIS).

---

## 9. Datasets

Specified in `matpcr_runbook.txt` RESOURCES block (lines ~32–34). **Every source is
tagged `[VERIFY]`** in the runbook — confirm existence/URL/license before relying.

| Modality | Oracle(s) | Dataset | Status |
|----------|-----------|---------|--------|
| Diffraction (real) | xrd_peak, spectrum_peak | **opXRD** | ✅ Downloaded, Half-A done (partial, see below) |
| Diffraction (simulated) | xrd_peak, spectrum_peak | **SimXRD-4M** | ✅ `val_binxrd` downloaded; schema/units unresolved |
| Microscopy | sem_feature_size | **NFFA-EUROPE** (18,424 images, downloaded+verified) | ✅ Downloaded; extractor built, 97.7% success on 300-image sample, not yet wired to oracle |
| Spectra | spectrum_peak | **RRUFF** (open Raman/IR) | ✅ Downloaded (Raman, `excellent_unoriented` grade), verified 2026-07-05 |
| DFT reference values | stability/metallicity/property | **Materials Project** via pymatgen API + own DFT | ✅ API access confirmed 2026-07-09; data pull not yet started |

### opXRD (downloaded) — `opxrd/`
- **92,552 JSON files**, real EXPERIMENTAL powder XRD patterns.
- 7 institution folders: CNRS, EMPA, HKUST (A/B), IKFT, INT, LBNL (A/B/C/D), USC.
- Each `pattern_N.json`:
  - `two_theta_values`: ~5,693-pt 2θ array → feeds `spectrum_peak_exists` DIRECTLY.
  - `intensities`: matching intensity array.
  - `label` (JSON string): `phases`, `xray_info`, `is_simulated`, `crystallite_size_nm`, `temp_K`.
    - `phases[i]`: `lattice` (a,b,c,α,β,γ), `basis` (atoms), `spacegroup`, `chemical_composition`, `phase_fraction`.
    - NOTE: some labels partial — sample had spacegroup/composition = None but lattice/basis populated. **Filter to patterns with enough structure info.**
  - `metadata` (JSON string): institution, contributor, original_file_format (pdCIF), date.
- **`xrd_peak_consistent` needs pymatgen** to turn lattice+basis → reference 2θ peak positions.
- **Encoding glitch** in some metadata (e.g. `Fran�ois`). Read JSON with
  `encoding='utf-8', errors='replace'`.

### SimXRD-4M (val split downloaded & verified 2026-07-04) — https://github.com/Bin-Cao/SimXRD
- **License: MIT** ✅
- Download (OneDrive): https://1drv.ms/f/c/5d8626238470b49e/EuwOU13P3bhHsbSiD14N7xYBfBLGBa1c_EaVHklfTj4qew?e=1kyibhX
  — **NOT scriptable**: link is SharePoint-backed (`migratedtospo=true`), curl/wget get 403,
  Graph anonymous-shares API gets 401. Downloaded manually via browser + `rsync` upload instead.
- Crystal structures (companion): Hugging Face `caobin/CrystDB` (public). A second HF mirror,
  `caobin/SimXRDreview` (Croissant-based), is **gated/private** — 401 without an approved
  access request.
- README claims 4M+ simulated patterns over 119,569 crystals, 33 conditions — **NOT verified**;
  see actual val-split count below.
- Files (ASE `.db` format): `train_binxrd` (×30), `val_binxrd`, `test_binxrd` (×2), `testNOtgt` (unlabeled).
- Install reader: `pip install ase tqdm` (done — `ase==3.29.0`).
- **`val_binxrd` verified 2026-07-04** at `/ephemeral/matpcr/val.db` (26GB decompressed from an
  8.5GB `val.db.gz`): gzip integrity OK, opens instantly via `ase.db.connect()`.
  - **Row count: 100,315** — trust this measured value over the README's 119,569 claim (unverified,
    possibly refers to the full crystal set or a different split/version).
  - **Actual schema differs from the README's example code** — the README's `test_binxrd` sample
    snippet does not match this file:
    - `latt_dis` and `intensity`: stored as **comma-separated strings**, not `eval()`-able Python
      literals. Parse with `[float(x) for x in row.latt_dis.split(',') if x.strip()]`. Each is a
      **3,500-point array**; `intensity` is normalized to 0–100.
    - **No `tager` field exists in this file.** `Label` is a single int (range seen: 0–2188+ across
      a 2,000-row sample) — too large to be a space group (1–230), so it is NOT `[spg, crysystem]`
      as the README implies. Meaning of `Label` in this file is **unconfirmed** — do not assume
      space group without checking against `simulation_param` or the SimXRD paper/code.
    - `simulation_param`: a 4-float list per row, meaning not yet decoded.
  - Load (verified working):
    ```python
    from ase.db import connect
    db = connect("./val.db")
    for row in db.select():
        atoms     = row.toatoms()
        element   = atoms.get_chemical_symbols()
        latt_dis  = [float(x) for x in row.latt_dis.split(',') if x.strip()]
        intensity = [float(x) for x in row.intensity.split(',') if x.strip()]
        label     = row.Label   # int; meaning unconfirmed, see above
    ```
- **OPEN QUESTION — units of `latt_dis`:** CLAUDE.md previously asserted SimXRD stores d-spacings
  (needing Bragg conversion to 2θ: 2θ = 2·arcsin(λ/2d)). But `latt_dis` values in this file range
  **10–80**, which reads like a 2θ scan range in degrees, not d-spacings in Å (typical d-spacings
  are ~0.5–10 Å). **Do not trust either claim until checked against the SimXRD paper/simulation
  code** — this determines whether the Bragg conversion is needed at all before feeding the XRD
  oracle. Flag to Mustafa before wiring this file into `xrd_peak_consistent`.

### RRUFF (downloaded & verified 2026-07-05) — `/ephemeral/matpcr/rruff/`
- Real domain is **rruff.net** (rruff.info redirects there). Bulk download is at
  `https://www.rruff.net/zipped_data_files/raman/` and `.../infrared/` — separate ZIPs
  per quality grade (excellent/fair/poor × oriented/unoriented) for Raman; a single
  `RAW.zip` for infrared. NOT a Zenodo/HF mirror — direct from rruff.net.
- Downloaded `excellent_unoriented.zip` (Raman, highest quality grade, ~230MB compressed,
  11,415 files after extraction — RAW + Processed pairs per sample/wavelength).
- **License — NO formal license exists, confirmed by independent research 2026-07-05.**
  Checked `/about/` and `/help/faq/` directly: only a generic copyright notice
  ("Copyright © 2026 RRUFF") and a mission statement to "openly share" data — no CC-BY/
  CC0/SPDX identifier anywhere. Citation is explicitly REQUIRED, not optional (Lafuente,
  Downs, Yang & Stone 2015, "The power of databases: the RRUFF project"; cite the
  external contributor too if the record names one). **Do not write "CC-BY" or any
  specific license in the paper for this dataset** — state it as "openly viewable/
  downloadable, citation-mandatory, no formal redistribution license located," or email
  RRUFF's contact page for written reuse confirmation if the venue requires a formal
  license line.
- **File format:** plain text, `##KEY=VALUE` metadata header block (mineral name, RRUFF ID,
  ideal chemistry, locality, cell parameters, crystal system, laser wavelength, etc.)
  followed by blank line then CSV data: `raman_shift_cm-1, intensity`. Filenames encode
  mineral name, sample ID, laser wavelength (nm), and RAW vs. Processed. Files use
  Windows CRLF line endings — harmless in Python text-mode reads (confirmed working),
  but a manual `\n`-only split in other tooling would leave stray `\r`. `##CHEMISTRY=`
  uses domain-specific notation (`_2_` for subscripts, `^3+^` for oxidation state) —
  don't treat it as a plain formula string.
- **Verified end-to-end 2026-07-05:** parsed one real file (Abelsonite, 2,312 points,
  x-range 153.6–1267.7 cm⁻¹), ran `spectrum_peak_exists` from `matpcr_metrics.py` —
  correctly returned `True` for a claim at a real peak (x=1146.7) and `False` for a claim
  in a flat/baseline region (x=200). Oracle plumbing works on real spectral data.
- **Known data-quality landmine (independent source, PMC6557180):** RRUFF entries for
  mackinawite, pyroxferroilite, and clinoferrosilite (**R060388, R141080, R141085**) are
  flagged by an independent comparison paper as suspiciously similar / possibly
  misidentified. If any test item touches these species, treat its ground truth as
  suspect, not authoritative. Same source also notes RRUFF generally lacks traceable
  instrument/calibration metadata per spectrum — don't assume cross-sample calibration
  consistency.
- Dataset size discrepancies exist across sources (4,216 vs. 32,940 vs. "14,000+ Raman
  entries" depending on what's being counted/when measured) — use what's actually on disk
  as ground truth, not any single cited total.
- IR coverage is much thinner than Raman (one 14MB `RAW.zip` vs. ~676MB combined across
  all Raman quality tiers) — expect the IR arm of any oracle test to be a much smaller N.
- Not yet done: bulk-run across many files, infrared data, Half-A injection harness for
  this oracle family (same pattern as the XRD one in `experiments/`).

### NFFA-EUROPE SEM dataset (fully downloaded & verified 2026-07-05) — `/ephemeral/matpcr/nffa/extracted/`
- Source: B2SHARE (EUDAT), record `19cc2afd23e34b92b36a1dfd0113a89f` (API id `qtq9v-ys023`).
  API confirmed live: `https://b2share.eudat.eu/api/records/qtq9v-ys023`. **License: CC-BY-4.0**
  (confirmed via API `metadata.rights`), public access, no embargo.
- **All 10 category `.tar` files downloaded, MD5-verified 10/10 against the API's published
  checksums (all matched exactly), extracted, and the `.tar` files deleted to save space.**
  Final on-disk dataset: **18,424 real SEM JPG images, 12GB**, in `extracted/<Category>/`:
  Biological (953), Films_Coated_Surface (308), MEMS_devices_and_electrodes (4158),
  Nanowires (3656), Particles (3412), Patterned_surface (3310), Porous_Sponge (171),
  Powder (895), Tips (1561), Fibres (153).
- **No separate annotation/metadata file anywhere** — confirms the earlier research finding:
  scale bar is **visually burned into the image only**, nothing structured to parse.
- **Instrument info-bar layout is NOT consistent across images — 3 real cases confirmed by
  direct visual inspection of 9 images across 6 categories (Fibres, Particles, MEMS_devices,
  Powder, Patterned_surface, Tips):**
  1. **Dominant "Zeiss-style" layout** (majority of images seen): red text, green scale-bar
     marker line, fields for EHT/WD/Mag/Signal A/Stage T/Stage Z/Brightness/Contrast/
     Aperture Size, plus either a "ZEISS" wordmark or a black-cube "TASC" logo badge
     (cosmetic variant within the same layout family — same field structure/color/position).
  2. **A second, distinct "black text" layout** (seen once in Fibres): black text, black
     marker line, "Signal A = SE2", "User Name" field, missing Brightness/Contrast/Aperture
     fields — a different SEM instrument/software entirely.
  3. **No info bar present at all** (seen once in Powder) — some images apparently had the
     info bar cropped out or were never captured with one. These images have NO extractable
     scale-bar information and must be filtered out before the oracle runs, not treated as
     an extraction failure to retry.
  **A single fixed-template/fixed-pixel-position extractor will NOT generalize across the
  dataset.** The extractor needs to be layout-robust (general OCR + line-detection for the
  scale-bar marker) and must also detect and skip images with no info bar at all, rather
  than hardcoding to one instrument's format or assuming every image is extractable.
### Scale-bar extractor (built & tested 2026-07-05) — `experiments/sem_scalebar_extractor.py`
General pipeline (NOT fixed-template, per the layout-variety finding above):
1. **Locate the info-bar band**: for each row in the bottom ~45% of the image, find its
   modal (most common) pixel value and what fraction of the row matches it. A genuine
   info-bar row is dominated by one flat background level (modal share > 0.65); text/marker
   pixels are always a minority. Group consecutive such rows into segments, splitting a
   segment when the modal level jumps by >20 (so a bright bar and an adjacent dark micrograph
   void — both independently "background-row" by the share test — are NOT merged into one).
   Among all segments found, the real bar is picked by whichever segment's background level
   is the STRONGEST OUTLIER vs. the image's own overall median gray level (not by raw length,
   and not by proximity to the bottom edge — both were tried and both picked the wrong region
   on real images; see the changelog below).
2. If no segment passes a minimum length, return `no_info_bar` — a real, expected outcome for
   some images, not a failure to retry.
3. **OCR the scale label**: restrict OCR to the LEFT THIRD of the located band only (every
   layout inspected puts the scale label there; other fields like "WD = 4 mm" elsewhere in
   the bar can falsely match the same regex if the whole bar is OCR'd — confirmed directly).
   Try multiple upscale factors (8x/6x/4x/3x) × PSM modes (11/6/7) × thresholded/grayscale,
   in that order, stopping at the first regex match — a single fixed config (3x + psm 6)
   missed real labels that 8x + psm 11 read correctly.
4. **Find the marker's pixel length**: within the same left-third crop, look for the row with
   the LONGEST SINGLE CONTIGUOUS RUN of marker-colored/high-contrast pixels (not the row with
   the most total matching pixels — text glyphs fragment into many short runs across letters
   and can out-count the one solid marker line if scored by total). Exclude the crop's own
   top/bottom edge rows (border-line artifacts can span the full crop width and get mistaken
   for an oversized marker).
5. Combine into `nm_per_px = scale_nm / marker_px`, ready to feed `sem_feature_size_consistent`.

**Bugs found and fixed during development (each confirmed by direct image inspection, kept
here so they aren't reintroduced):**
- Row-std-based band detection failed because text rows spike in std while pure-background
  rows don't — the band as a whole isn't low-std, individual rows alternate. Switched to
  modal-share (background-dominance), not row variance.
- Comparing each row only to the run's *start* level let slowly-drifting texture chain into
  one long false run. Fixed by tracking a per-segment reference level and cutting on
  departure from it.
- Selecting the longest background segment picked a large black micrograph VOID next to a
  thin SEM tip instead of the actual (much shorter) white info bar. Selecting by
  bottom-edge-proximity instead picked a DIFFERENT dark strip below the real bar. Both wrong;
  fixed by scoring segments by contrast-to-overall-image-level, which correctly identifies
  the true outlier band regardless of position or length.
- Marker-length detection picked the OCR text row (more total dark pixels, summed across
  fragmented letters) instead of the marker's own row (one solid ~45-50px run). Fixed by
  scoring rows by longest contiguous run, not total matching-pixel count.
- OCR-ing the full bar width let unrelated fields (e.g. "WD = 4 mm") satisfy the scale regex
  when the real label ("2 um") was misread — silently returned the WRONG field's value with
  no error. Fixed by restricting OCR to the left third structurally, not just improving regex.

**Result on a 300-image stratified sample (30/category × 10 categories), 2026-07-05:**
**97.7% end-to-end success** (293/300: band located, OCR read, marker measured, nm_per_px
computed). Remaining 2.3%: 5 genuine `no_info_bar` (visually confirmed — some NFFA images
really have no bar, e.g. edge-to-edge Powder micrographs), 1 `marker_not_found`, 1
`ocr_failed` — both on Tips images with very dark/tight crops; correctly reported as failures
rather than fabricating a value.
- **Not yet done:** run across the FULL 18,424 images (only a 300-image stratified sample so
  far); spot-check a larger random sample of "ok" results for correctness, not just
  non-crashing (only ~8 manually cross-checked against the actual image so far); wire results
  into `sem_feature_size_consistent`; Half-A/Half-B for this oracle family.
- Also identified but not pursued yet: **Voxel51/OD_MetalDAM** (HF, MIT license, 42 images,
  has structured scale-bar metadata instead of a burned-in bar) — smaller but cleaner
  ground truth; worth using as an independent cross-check once the NFFA extractor's output
  needs validating against a "known good" source. Other candidates (cigRockSEM — restrictive
  CC-BY-NC-ND; MicroNet/Aversa — no confirmed live bulk URL; various Kaggle sets —
  unverified) are lower priority.

### Materials Project (API access confirmed 2026-07-09) — unblocks the 3 DFT-grounded oracles
- Rasul created a free account at next-gen.materialsproject.org and generated an API key.
  Key lives at `/tmp/matpcr_secrets/.env` (as `MP_API_KEY=...`), NOT in the repo, NOT logged.
- **Client**: `mp-api` (the modern, actively-maintained client; `pymatgen.ext.matproj.MPRester`
  still works but is legacy). Installed via `pip install mp-api` (lands on `/ephemeral` per the
  earlier disk fix).
- **Compatibility bug hit and fixed**: the latest `mp-api` pulled in `emmet-core==0.86.0rc1` (a
  release candidate), which imports `NotRequired` from the stdlib `typing` module — only
  available in Python 3.11+. This machine runs Python 3.10, so `from mp_api.client import
  MPRester` raised `ImportError: cannot import name 'NotRequired' from 'typing'` even though
  `typing_extensions` (which HAS the Python-3.10-compatible backport) was already installed —
  the bug is emmet-core importing from the wrong module, not a missing dependency. **Fixed by
  pinning `emmet-core==0.85.1`** (latest actual stable release, pre-dates the broken import).
  If `mp-api` is ever reinstalled/upgraded, re-check this — a newer stable emmet-core release
  may fix it properly and make the pin unnecessary.
- **Verified working end-to-end** with a real query: `mp-149` (silicon) → band_gap=0.610 eV
  (real DFT/PBE value; underestimates the experimental 1.12 eV, which is the well-known,
  expected PBE band-gap-underestimation limitation, not a bug), energy_above_hull=0.0 (Si is
  the stable ground state, correct). Confirms the pipeline is real and the key works.
- **Fields available per material** (from one query's "not requested" list, i.e. confirmed to
  exist in the schema): `energy_above_hull`, `is_stable`, `formation_energy_per_atom` (→
  stability oracle); `band_gap`, `is_gap_direct`, `is_metal`, `cbm`/`vbm` (→ metallicity
  oracle); `bulk_modulus`, `shear_modulus`, `total_magnetization`, and many more (→ candidates
  for the property sign/magnitude oracle).
- **TARGET PROPERTY DECIDED (2026-07-09): `total_magnetization`.** Not specified anywhere in
  runbook/cover-letter/manuscript — all three just say "a target property," genuinely left as
  a team choice. Checked real coverage on a 500-material random MP sample before choosing:
  `bulk_modulus`/`shear_modulus` = **0/500 (0%)** — elastic properties are only computed for a
  small dedicated MP subset, would starve Half-A/Half-B of data. `total_magnetization` =
  **500/500 (100%)** coverage, AND a real, useful sign split (273 zero / 227 nonzero in the
  sample) — a model actually has to reason about whether a material is magnetic, not just
  repeat one answer. (`formation_energy_per_atom` also has 100% coverage but is a weak sign
  test: 498/500 negative in the sample, i.e. almost always the same answer — rejected for this
  reason even though it's already used for the STABILITY oracle's hull check, a different use.)
- **Mustafa's sign-off scope, decided 2026-07-09**: per CLAUDE.md §8 rule 1, the co-author
  validates DFT protocol/tolerances before any DFT oracle is TRUSTED — but Half-A (positive
  control: does the oracle's comparison logic correctly catch synthetic violations against
  known values) is pure software correctness and does not need his review. **Half-A for all 3
  DFT oracles can and will proceed now. Half-B (precision audit using real MP values as
  ground truth) is explicitly HELD pending his review** — that is exactly the risk his sign-off
  exists to catch (functional choice, whether MP's computed values are even the right
  reference for what a model would be reasoning about, tolerance choices). Do not run Half-B
  or report DFT precision numbers before he has reviewed.
- **OVERRIDE (2026-07-XX, per Hasan/PI instruction relayed by Rasul): proceed with DFT Half-B
  WITHOUT waiting for Mustafa's review.** This reverses the hold above. Hasan is the
  coordinating PI and has the standing to make this call; recorded here so future sessions
  don't silently re-impose the original hold as if it were still active. **This means DFT
  precision numbers in the paper are NOT YET independently validated by the domain co-author**
  — flag this explicitly in any manuscript text, cover letter, or supervisor-facing summary
  that reports these numbers, and get Mustafa's review before final submission regardless
  (per §8 rule 4, still standing: 2-3 independent human mock reviews before submission).
- **IMPORTANT DEFINITION MISMATCH found during Half-B collection (2026-07-XX):** Materials
  Project's own `is_stable` boolean field uses an essentially exact-zero threshold on
  `energy_above_hull`, NOT the oracle's 0.05 eV/atom tolerance. **571 of 3000 real materials
  (19%) are `is_stable=False` in MP's own labeling but WITHIN the oracle's 0.05 eV/atom
  tolerance** (e.g. hull=0.0234 eV/atom) — meaning the oracle's `stability_claim_consistent`
  correctly calls these "stable" while MP's own flag calls them "not stable." This is not a
  bug (the harness correctly calls the oracle on `energy_above_hull` directly, never on
  MP's `is_stable` field) but a real, substantive DFT-definition question: if a model's
  training data associates "stability" with MP's stricter labeling convention, it will
  systematically disagree with our looser tolerance on ~19% of real materials, independent
  of whether the model is "reasoning well." **This is exactly the kind of protocol nuance
  Mustafa's review is meant to catch — flag it to him explicitly even though Half-B is
  proceeding without waiting for his sign-off**, and consider whether 0.05 eV/atom is the
  right tolerance or whether it should be tightened/loosened/reported alongside MP's own
  label for transparency.
- [x] **DFT oracles Half-A (positive control) — DONE (2026-07-09).**
      Scripts: `experiments/mp_fetch_reference_data.py` (pulls real MP data via `mp-api`;
      hit and fixed a real Python-3.10 compatibility bug — the latest `mp-api` pulled in
      `emmet-core==0.86.0rc1`, a release candidate that imports `NotRequired` from the stdlib
      `typing` module, Python-3.11+-only; pinned `emmet-core==0.85.1` to fix) and
      `experiments/exp1_halfA_dft_injection.py` (injection harness, same pattern as
      XRD/SEM/spectrum). Data: 3000 real materials, all 3 target fields present
      (`energy_above_hull`, `band_gap`, `total_magnetization`) — real distribution: 181
      stable (6%), 1062 metallic (35%), 2234 magnetic (74%).
      - **Stability and metallicity oracles: 0% FN, 0% FP at all 3 planted rates immediately**
        — expected, both are simple boolean-flip injections against clean threshold
        comparisons (same reason SEM's Half-A was clean).
      - **Sign/magnitude oracle: found and fixed a REAL bug in `matpcr_metrics.py` itself**
        (not a harness bug this time — the oracle function). `property_sign_magnitude_consistent`
        used exact float equality (`reference_value == 0`) to detect a zero reference. Real
        DFT-computed `total_magnetization` values are essentially never exactly 0.0 due to
        numerical noise — confirmed directly: **82/3000 real materials had `0 < |total_magnetization|
        < 1e-6`** (e.g. `1e-07`, `6e-07`). Those fell through to the nonzero branch, where a
        near-zero reference makes the magnitude-ratio test reject almost any claim — this
        produced a 2.6-2.9% false-positive rate on real, correct clean claims. **Fixed** by
        adding a `zero_atol=1e-6` parameter and comparing `abs(reference_value) <= zero_atol`
        instead of exact equality. Confirmed smoke test (`python matpcr_metrics.py`) still
        passes after the change.
      - **Final result after the fix: 0% FN, 0% FP for all 3 DFT oracles at all 3 planted
        rates (0.10/0.30/0.50).** A genuinely clean, complete Half-A result.
      - This fix (exact-zero → tolerance-based zero) is real, DFT-oracle-affecting production
        code, not a harness-only change — but it is still Half-A/software-correctness scope
        (the function's own comparison logic), not a DFT-protocol/tolerance judgment call, so
        it did not require Mustafa's sign-off.
- [x] **DFT modality PILOT — DONE.** See "DFT modality PILOT" entry under §10b above:
      100% parse success across all 3 claim types × both models after prompt/parser fixes.
- [x] **DFT oracles Half-B data collection — DONE (2026-07-10), per Hasan's override.**
      Scripts: `experiments/halfB_collect_dft.py` (generates real model claims via
      `pilot_dft.py`'s prompts, checks each against the REAL Materials Project reference value
      for that exact material via the actual oracle function, loops per claim type until
      ≥100 real firings accumulate) and `experiments/halfB_report_dft.py` (renders each claim
      type's fired cases into a review page — no image needed for this modality, shows
      formula + model claim + real reference values + full reasoning chain).
      - **Collection result: 120 stability / 131 metallicity / 103 magnetism real fired cases**
        (406 total oracle-fired records), pulled from 3000 real Materials Project materials,
        both models (local Qwen2.5-VL-7B text-only + API Gemini 2.5 Flash Lite), **total API
        cost $0.0574**.
      - **Review pages**: `experiments/halfB_review_dft_{stability,metallicity,magnetism}.html`
        — small static files (0.3-0.4MB, no images), same review UI as the geometric families
        (Real/False-positive/Unsure radio buttons, live precision tally, Export button). Each
        page carries an explicit red-text banner: these DFT reference values have NOT been
        independently validated by Mustafa, and any "real violation" verdict from this review
        is provisional until that review happens.
- [x] **DFT oracles Half-B manual review — DONE (2026-07-10).** Rasul reviewed all 354
      fired cases across the 3 DFT families (exported via each review page, saved as
      `stability.txt`/`metallicity.txt`/`magnetism.txt` in repo root — note: these exports
      had UNQUOTED string values, e.g. `"verdict": real` instead of `"verdict": "real"`,
      invalid strict JSON; parsed with a regex pre-pass that quotes bare
      real/false_positive/unsure tokens before `json.loads`).
      - **Precision results (real / (real + false_positive); unsure excluded from the ratio):**
        | Family | Reviewed | Real | False positive | Unsure | Precision |
        |---|---|---|---|---|---|
        | Stability | 120 | 109 | 11 | 0 | **90.8%** |
        | Metallicity | 131 | 122 | 9 | 0 | **93.1%** |
        | Magnetism | 103 | 79 | 13 | 11 | **85.9%** |
      - **Stability false positives root-caused: 9 of 11 are the exact definition-mismatch
        effect flagged during collection.** Hull values cluster right at the 0.05 eV/atom
        boundary (0.031-0.047 just under, or 0.060-0.068 just over) — the model's claim likely
        tracks MP's own stricter `is_stable` convention or genuine hull-adjacent uncertainty,
        not a real reasoning failure. Reinforces that this tolerance choice is a real,
        pre-existing open question for Mustafa, not resolved by this review passing.
      - **Magnetism's 11 "unsure" cases share a real, specific pattern**: every one is the
        model claiming MAGNETIC on a composition containing a rare-earth/lanthanide-like
        element (Nd, Sm) plus a transition metal (Cu, Ti), where real total_magnetization is
        ~0 (0.0000-0.0194). Chemically plausible explanation: individual ions can carry local
        moments while the DFT-computed NET moment cancels (e.g. antiferromagnetic ordering) —
        a genuine "locally magnetic, net non-magnetic" distinction the oracle's binary check
        doesn't capture, not obviously a model error. Flagged as a real oracle-definition
        question (does "magnetic" mean net moment or ionic character?), not resolved here.
      - **This is exactly the kind of DFT-definition nuance Mustafa's review exists to
        catch — his review is still needed** despite Half-B now being numerically complete;
        the override let the team get a number, not skip the underlying validation.
      - Reminder: per the OVERRIDE entry above, these precision numbers are **NOT YET
        independently validated by the domain co-author** — say so explicitly in any
        manuscript text or supervisor-facing summary, and still get Mustafa's review before
        final submission (§8 rule 4 stands regardless of this override).
- [x] **Experiment 1 (the gate) — FULLY COMPLETE for all 6 oracle families (2026-07-10).**
      Half-A: 0% FN for all 6. Half-B: XRD 77.2%/SEM 88.6%/Spectrum 72.8% (Rasul's gate call,
      2026-07-07) and Stability 90.8%/Metallicity 93.1%/Magnetism 85.9% (2026-07-10, per
      Hasan's override — NOT yet Mustafa-validated). Proceed to Experiment 2 for all 6
      families, but carry the "DFT numbers not yet co-author-validated" caveat through every
      downstream table/section until Mustafa reviews.

---

## 10. The experiments (`matpcr_runbook.txt`, in run order)
- **PILOT (before Exp 1):** 50–100 items/modality through ONE local + ONE API model.
  Confirm chains EXPOSE checkable quantities and the parser extracts them; fix the
  PROMPT if not.
- **EXPERIMENT 1 — POSITIVE CONTROL + ORACLE PRECISION AUDIT (RUN FIRST; the GATE).**
  See §11.
- **EXPERIMENT 2 — PCR sweep:** PCR + ρ_t for all models × modalities × constraint
  types (incl. DFT), bootstrap 95% CIs, S seeds. Fills Table 1.
- **EXPERIMENT 3 — Accuracy vs consistency gap:** on labeled subset, show PCR ≠ accuracy.
- **EXPERIMENT 4 — CGSV effect:** PCR before/after CGSV; exact McNemar; report fixes c,
  regressions b, p, residual violations. Small/insignificant = valid outcome.
- **EXPERIMENT 5 — Verifier (released artifact):** fine-tune open model on ORACLE labels
  to predict violations; report P/R/F1, ROC AUC, ECE; held-out modality + constraint-type
  splits; release weights.
- **EXPERIMENT 6 — Detector analysis:** does verifier score predict a real violation?
  ROC AUC with bootstrap CI.
- **OPTIONAL STRETCH (NOT headline):** discovery case study — verifier pre-filters
  candidates before DFT. Report only if it holds; the angle is crowded.

### Models (runbook)
Open VLM (Qwen2.5-VL-class) + open reasoning LLM on cluster; 2–3 frontier API models.
PIN all versions and API snapshot dates.

### Flag-back triggers
Oracle precision low → fix checker/parser/DFT first. Models rarely expose checkable
quantities → prompt redesign. PCR ≈ 1.0 everywhere → add harder items or narrow scope
(say so honestly). CGSV regressions ≥ fixes → report honestly. Verifier doesn't
generalize → report the limit.

---

## 10b. PILOT stage — DONE (2026-07-06) — `experiments/pilot.py`
Per the runbook: run 50-100 items/modality through ONE local + ONE API model; confirm
chains EXPOSE checkable quantities and the parser extracts them; fix the PROMPT (or
parser) if not. This is NOT Experiment 1 — no injected violations, no PCR, not a paper
number. It is a feasibility check, and it passed.

**Models used:**
- **Local**: `Qwen/Qwen2.5-VL-7B-Instruct` via `transformers`, run on this machine's A100
  (bf16, `device_map="cuda:0"`). Weights at `/ephemeral/matpcr/hf_cache` (16GB).
- **API**: `google/gemini-2.5-flash-lite` via OpenRouter — chosen deliberately for cost:
  a small pre-funded OpenRouter key was provided with a limited balance (~$31 remaining
  of a $50 limit at the start of this work); this model is vision-capable and roughly
  $0.0002-0.0003 per call with an image, so the full pilot (90 calls) cost **$0.013 total**.
  API key lives in the session scratchpad `.env` file, NOT committed to the repo.

**Modalities piloted (n=15 each, 2 models = 90 total model calls):**
- **XRD**: real opXRD patterns (CNRS), rendered as a matplotlib diffractogram PNG
  (2theta vs intensity, with gridlines/ticks — added after v1 showed the model
  needed visual anchors to read peak position precisely). Model asked to state the
  strongest peak's 2theta position.
- **SEM**: real NFFA-EUROPE micrographs (mixed categories). Model asked to read the
  scale bar and estimate the largest visible feature's size.
- **Spectrum**: real RRUFF Raman spectra, rendered as a matplotlib plot. Model asked
  to state the strongest peak's Raman shift.

**Result — parser-extraction success rate (does the chain expose a checkable claim
AND does the parser pull it out), final numbers after fixes below:**

| Modality | Local (Qwen2.5-VL-7B) | API (Gemini 2.5 Flash Lite) |
|---|---|---|
| XRD | 15/15 (100%) | 15/15 (100%) |
| SEM | 15/15 (100%) | 14/15 (93%) |
| Spectrum | 15/15 (100%) | 15/15 (100%) |

**Real issues found and fixed this session (kept here so they aren't reintroduced):**
1. **XRD peak-position precision was poor initially** (models said "0 deg" / "0.5 deg"
   for peaks actually at ~4-5°) — the model was reading "near the y-axis" rather than
   the exact apex. Fixed by adding explicit x-axis gridlines/ticks to the rendered plot
   and instructing the model to reference them, not just eyeball proximity to the origin.
   After the fix, readings moved to a plausible ~3-5° range with real reasoning citing
   gridlines. **Note: still not validated against the TRUE peak position — this is a
   parse-success check, not a correctness check; correctness is Experiment 1's job.**
2. **Local model sometimes truncated mid-reasoning** before reaching `FINAL_ANSWER:`
   (self-correcting/re-deriving an estimate ate the token budget). Fixed by raising
   `max_new_tokens` 300→600.
3. **API model truncated 3/15 XRD responses** for the same reason at `max_tokens=400`;
   raising to 700 fixed all 3 (confirmed by isolated re-run: 15/15 after the fix).
4. **Parser was too strict on exact string match** (`FINAL_ANSWER:` literal) — real
   model output varied ("Final Answer:", space instead of underscore). Fixed with a
   `FINAL[_ ]ANSWER` pattern instead of forcing the model to hit one exact string.
5. **Model gave a range instead of a single number** ("800-1000 nm") — parser now
   accepts a range and takes the midpoint rather than failing outright (the model DID
   expose a checkable claim, just not in the single-number format asked).
6. **Model wrapped its answer in LaTeX** (`\[ \text{Final Answer: } 15 \, \mu\text{m} \]`)
   — parser now strips LaTeX control sequences, with a special case for `\mu` (must
   substitute to "u" BEFORE the generic strip, else the generic "\word" stripper deletes
   it as if it were inert formatting and leaves an unmatchable bare "m").

**Environment fixes made along the way (not pilot-specific, but blocking):**
- Root disk was at 98% full (2.7GB free) when this started, from RRUFF/earlier work.
  Root cause: `pip`/`~/.local` defaults to the root disk, which is small and stays
  perpetually near-full. **Fixed structurally**: moved `/home/ubuntu/.local` (4GB) to
  `/ephemeral/matpcr/local`, symlinked back — all future pip installs now land on
  `/ephemeral` (614GB free) automatically. This is also why `torch` was found broken
  (metadata present, package files missing — likely a prior partial-uninstall to free
  root-disk space) — reinstalled cleanly after the disk fix.
- `HF_HOME` had THREE different values in play across `~/.bashrc` (two conflicting
  exports from earlier sessions) and the actual shell env (a third, `/data/hf_cache`,
  pointing at a path that doesn't exist as a distinct mount) — cleaned up `.bashrc` to
  one correct value, and set `HF_HOME` explicitly inside `pilot.py` itself (before any
  `transformers`/`huggingface_hub` import) rather than relying on shell env at all, since
  shell state doesn't reliably persist across tool calls in this session.

**Not yet done:** larger N (only 15/modality, not the full 50-100 the runbook suggests).
This pilot's job (confirm chains are checkable) is satisfied for XRD/SEM/spectrum.

### DFT modality PILOT — DONE (2026-07-XX) — `experiments/pilot_dft.py`
Previously blocked ("no Materials Project/DFT data yet"); unblocked once MP access was
confirmed (see "Materials Project" section above). This is a TEXT (LLM) input, not image
(VLM) — the model reasons from a chemical formula alone (e.g. "CaMg(CO3)2"), matching the
manuscript's "structure or text (LLM) input" category, distinct from the image-based
XRD/SEM/spectrum pilot. 3 claim types: stability (STABLE/UNSTABLE), metallicity
(METALLIC/NONMETALLIC), magnetism (MAGNETIC/NONMAGNETIC) — one prompt each, real MP formulas.

**Final result (n=15/claim-type, both models): 100% parse success across all 6
(claim-type, model) combinations.**

**Real issues found and fixed this session:**
1. **Markdown bold broke the parser** — real model output wrote `**Final Answer:**
   UNSTABLE` (bold wraps the colon), which a plain `FINAL_ANSWER:\s*` regex missed because
   `*` is not whitespace. Fixed with a regex tolerant of `*`/`_` markdown markers around the
   label and the answer.
2. **Model invented a third answer ("METASTABLE")** outside the offered STABLE/UNSTABLE
   binary — traced to the prompt's own wording ("...or unstable/metastable?") inviting a
   3-way framing even though the FINAL_ANSWER instruction only offered 2. Fixed by rewording
   to force a strict binary choice and explicitly telling the model to fold "metastable"
   into UNSTABLE.
3. **Truncation, worse for `stability` specifically** — the model hedges much more on
   stability ("without a calculated phase diagram, it's difficult to say...") than on
   metallicity/magnetism, eating the token budget before reaching `FINAL_ANSWER:`. Raising
   `max_tokens` alone (400→700→1000) was not enough; also had to shorten the prompt's own
   reasoning request ("keep reasoning SHORT, 2-4 sentences, do not extensively hedge") to
   fix the root behavior, not just the budget.

Per the 2026-07-XX PI override (Hasan instructed proceeding without Mustafa's DFT-protocol
sign-off), this pilot result clears the way to build the DFT Half-B collection harness
immediately, same as the geometric modalities.

## 11. Experiment 1 detail (the GATE)
**Purpose:** prove the oracles actually measure real violations before trusting any
number. Two independent halves:

- **Half A — Positive control:** inject violations at a KNOWN rate per oracle family,
  run oracles, confirm recovered rate ≈ planted rate. Catches false negatives
  (missed violations). (The smoke test does this synthetically; Exp 1 does it on
  REAL data via pymatgen/CIFs, real micrographs, real DFT/MP energies.)
- **Half B — Precision audit (MANUAL, cannot be automated):** for each oracle family,
  manually inspect **≥100 oracle-FIRED cases**, record true-violation fraction =
  **precision**. Catches false positives (flagging correct reasoning).

**GATE decision:** if precision is low → **STOP**, fix checker/parser/DFT protocol
before anything else. No fixed threshold; team sets it per family. Mustafa must sign
off on DFT protocol before DFT oracles are trusted.

**Done =** per family: planted-vs-recovered rate (A) + precision over ≥100 fired
cases (B) + provenance for every reference value (public DB id or DFT job id).

### Why Claude cannot run Exp 1 end-to-end
- Missing real data (SEM images, RRUFF, MP/DFT values not in folder).
- Tools likely not installed (pymatgen, ASE, opencv...).
- **Half B is human work** + Mustafa's DFT sign-off — cannot be automated.
- Claude CAN build the Half-A injection harness now (pluggable data source).

### ETA (asked: "if I have GPU")
GPU speeds model inference (hours) but does NOT set the ETA — the gate is human-paced
(manual audit of 600+ cases, Mustafa's sign-off, data collection).
- **XRD-oracle-only Exp 1** (opXRD + SimXRD in hand, no DFT yet): **~2–3 days.**
- **Full Exp 1** (all 6 families, needs all data + Mustafa's DFT sign-off): **1–2 weeks.**
- Speed-ups: collect remaining datasets in parallel; schedule Mustafa's DFT review
  early (longest pole); build the harness now to take it off the critical path.

---

## 12. Current status / next steps
- [x] Smoke test passes.
- [x] opXRD re-downloaded from Zenodo (record 15298026, CC-BY-4.0) 2026-07-04 — original copy was
      truncated (missing HKUST + LBNL entirely, 8,181/92,552 files); fresh copy verified at full
      92,552 files, sample-validated (250 files/folder, 0 failures). Lives at `/ephemeral/matpcr/opxrd`
      (moved off the near-full root disk), symlinked from `nature_submission/opxrd`.
- [x] SimXRD-4M `val_binxrd` downloaded (manual browser + rsync, OneDrive link is not scriptable)
      and verified 2026-07-04 — see §9 for schema caveats (row count 100,315 not 119,569; no `tager`
      field; `Label` meaning unconfirmed; `latt_dis` units unconfirmed — 2θ vs d-spacing open question).
      File at `/ephemeral/matpcr/val.db` (26GB).
- [x] **ASE + pymatgen installed** (`ase==3.29.0`, `pymatgen==2025.10.7`). Both gating deps for
      the XRD datasets are now in.
- [x] **opXRD → XRD oracle validated end-to-end on real data (2026-07-04, exploratory, N=10 patterns).**
      Pipeline: parse `pattern_N.json` → `label.phases[0].lattice`+`.basis` (strip oxidation-state
      suffixes like `Ba0+`→`Ba`, note `lattice`/`basis`/`xray_info` fields are JSON-encoded as
      strings-of-strings, need nested `json.loads`/`ast.literal_eval`) → build a pymatgen `Structure`
      → `XRDCalculator(wavelength=...).get_pattern()` for reference 2θ peaks → find local-maxima
      peaks in the pattern's real measured `two_theta_values`/`intensities` via
      `scipy.signal.find_peaks` → check each against `xrd_peak_consistent` (tol=0.5°).
      **Result: 10/10 CNRS patterns with usable lattice+basis (8 of the 10 sampled; 2 skipped —
      no phase data, the known "partial labels" case) had ALL top measured peaks match a reference
      peak** (8/8, 7/7, 15/15, 15/15, 15/15, 5/5, 8/8, 5/5 across the 8 structures). This is a
      good sign for oracle correctness but is **NOT Experiment 1 Half-A** (no violations were
      injected — this only checks the positive/consistent case) and **NOT Half-B** (no manual
      precision audit) — it is a pipeline smoke check on real data, one institution folder only.
      Still need: run at larger N across all 7 institutions, and the actual Half-A injection
      harness (perturb claimed peaks away from true values, confirm the oracle catches it).
- [x] **Half-A (positive control) harness built and run on real opXRD data (2026-07-04).**
      Script: `experiments/exp1_halfA_xrd_injection.py`. Method: pull real measured peaks from
      opXRD patterns with usable `lattice`+`basis`, build the pymatgen reference pattern (as in
      the N=10 check above), then for each real measured peak either keep it as-is (clean) or
      inject a violation (shift 2θ by a random offset, verified >0.75° from EVERY reference AND
      every other real measured peak in that pattern before accepting it — if no such offset
      exists in the whole window, skip that peak rather than inject an unverified claim). Run
      `xrd_peak_consistent` on all claims; compare planted vs. recovered violation rate.
      - **Coverage is much narrower than opXRD's institution list suggests:** of the 7 institutions,
        only **CNRS (~90% hit rate) and HKUST (~10% hit rate)** yielded patterns with usable
        `lattice`+`basis` in this session's samples (200/institution checked). **EMPA, IKFT, INT,
        LBNL, USC returned ZERO** usable patterns — EMPA/USC have partial phase data (lattice
        without basis, or vice versa), IKFT/INT/LBNL patterns had no `phases` entries at all in
        the files sampled. This is a real dataset-coverage finding, not a parsing bug — confirmed
        by direct inspection of raw files. **The XRD oracle can currently only be positive-control-
        tested against ~2 of opXRD's 7 real sources.** Flag to the team: either the other 5 sources
        need a different structure-extraction path, or the paper's claims about opXRD coverage
        need to be scoped down to what's actually usable.
      - **Result across 81 usable patterns (60 CNRS + 21 HKUST), 918 real measured peaks, 3 planted
        rates:** false-negative rate = **0.0000 at all three rates** (0.10, 0.30, 0.50) — the oracle
        caught every injected violation, zero misses. Recovered rate tracked planted rate closely
        (0.1089/0.2934/0.4839 vs. 0.10/0.30/0.50). This is a genuinely good Half-A signal for the
        false-negative side.
      - **False-positive rate (clean/unperturbed real claims wrongly flagged): ~4-6% overall, but
        highly institution-dependent** — CNRS alone: **~0.5%** (3/646, isolated check). HKUST alone:
        **~17%** (37/220, isolated check) — much worse.
      - **ROOT CAUSE FOUND (2026-07-06) for the HKUST gap — peak-picking, not the oracle.**
        Re-investigated `HKUST-A/pattern_16` (elemental Ti, cubic a=3.282Å — this is actually a
        physically REASONABLE β-Ti-like bcc lattice, not suspect: pymatgen density comes out to
        4.50 g/cm³, matching real Ti's 4.51 g/cm³ almost exactly; earlier session's "looks suspect"
        note was wrong). The reference pattern has exactly ONE strong peak in range: (110) at
        38.870°. The REAL measured data has one broadened/tailing peak envelope spanning
        roughly 30-46° (real experimental peak broadening — crystallite size/strain — not noise).
        `scipy.signal.find_peaks(prominence=0.05, distance=5)` finds 52 local maxima across that
        one broadened envelope and its decaying tail, and the harness's "top 15 by intensity"
        selection grabs 15 of them as if they were 15 independent real peaks — only 6 of those 15
        are actually within 0.5° of the true (110) position; the rest are genuinely different
        points along the SAME peak's tail, correctly far from the apex. **The oracle is behaving
        correctly — `xrd_peak_consistent` is right to flag a claim at 2theta=37.74° (1.13° from
        the true 38.87° apex) as inconsistent.** The false positives are an artifact of the
        HARNESS's peak-selection: it's asking about points that were never real independent
        peaks in the first place. Tried widening `find_peaks`' `distance` param (15/30/50) —
        made it WORSE (drops to 1/15 consistent), because it starts admitting points further into
        the noisy baseline once the tight local cluster thins out, rather than isolating the one
        true peak. **This is not a fixed-parameter problem** — real broadened peaks need genuine
        peak-envelope resolution (find contiguous local maxima runs, keep only the global max per
        resolved envelope), not a single global `distance`/`prominence` tweak.
      - **FIX APPLIED (2026-07-06):** added `_resolve_peak_envelopes()` to
        `experiments/exp1_halfA_xrd_injection.py` — clusters raw `find_peaks` local maxima
        within 1° of each other and keeps only the single tallest point per cluster (one
        genuine peak per resolved envelope, not one per point-on-the-tail). Also added
        `MIN_RELATIVE_INTENSITY = 0.5`: a resolved peak must be ≥50% of the pattern's own
        max intensity to be treated as a genuine claim-worthy peak at all (filters out
        background bumps at 17-33% of max that `find_peaks` still registered as "peaks").
        **Confirmed on `pattern_16` directly: now correctly resolves to exactly 1 peak
        (38.64°, matching the true (110) reflection), consistent=True.**
      - **Full re-run after the fix, 81 patterns, same 3 planted rates:** total real measured
        peaks dropped from 918 → **171** (most of the original 918 were spurious tail/noise
        points, confirming the diagnosis). **FN rate still 0.0000 at all three rates** — fix
        didn't cost sensitivity. **FP rate improved to 2.5-4.6%** (from the earlier blended
        4-6%, but see the institution split below — the aggregate masks a still-real gap).
      - **CNRS-vs-HKUST re-measured after the envelope fix (isolated check, 60 patterns each):**
        CNRS FP rate **0.0%** (0/116) — fully resolved. HKUST FP rate **12.5%** (5/40, down
        from ~17%) — improved but a real gap remained.
      - **SECOND FIX APPLIED (2026-07-06) — multi-phase reference generation.** Root-caused
        the 5 remaining HKUST failures individually: **4 of 5 were multi-phase samples**
        (`pattern_17`: 2 phases, `pattern_5`: 3 phases, `pattern_15`: 4 phases) where the
        harness built the reference from `phases[0]` ONLY — real measured peaks from phase
        2/3/4 genuinely had no match in a phase-0-only reference (confirmed: `phase_fraction`
        is `None` in every sample checked, so no weighting info exists or is needed — fixed
        by using the UNION of ALL phases' reference peaks, since `xrd_peak_consistent` only
        needs "does this claim match ANY real reference peak"). **The 5th (`pattern_14`) is
        single-phase** (hexagonal, a=2.46Å/c=33.45Å, graphite-like) and remains genuinely
        unexplained — lower priority now at 1 case out of 40 (2.5%).
      - **Re-measured after BOTH fixes (isolated check, 60 patterns each):** CNRS FP rate
        **0.0%** (unchanged). HKUST FP rate **5.0%** (2/40, down from 12.5%) — the 2 remaining
        failures are `pattern_17` (now only 0.53° from its nearest reference peak, essentially
        AT the 0.5° tolerance boundary — reads as measurement/calibration noise, not a
        structural problem) and the still-unexplained `pattern_14`.
      - **FINAL full Half-A re-run after both fixes, 81 patterns, same 3 planted rates:**
        **FN rate 0.0000 at all three planted rates** (unchanged — both fixes preserved
        sensitivity). **FP rate improved to 0.8-2.3%** across the three rates (0.0132/0.0082/
        0.0227 at planted 0.10/0.30/0.50) — down from the original 4-6%. Recovered rate still
        tracks planted rate closely (0.0964/0.2531/0.4625 vs 0.10/0.30/0.50). **This is now a
        credible, defensible Half-A positive-control result for the XRD oracle on opXRD's
        CNRS+HKUST subset.**
      - **Two harness bugs found and fixed during the original (pre-envelope-fix) run, still
        worth remembering:** (1) real instrument scans include points outside the oracle's
        physically-realizable 5-90° window; treating those as "clean claims" without filtering
        produces spurious FPs that are a harness bug, not an oracle bug — now filtered. (2) the
        injection offset-search must be exhaustively verified against the ENTIRE window, not a
        small random-retry budget — a failed search must skip the peak, never fall back to an
        unverified offset.
- [ ] Root-cause the one remaining unexplained single-phase failure (`HKUST-A/pattern_14`,
      graphite-like hexagonal lattice) — lower priority, 2.5% residual rate, not urgent.
- [ ] Extend Half-A to larger N; consider whether EMPA/IKFT/INT/
      LBNL/USC need a different structure-extraction approach or should be excluded from XRD-oracle
      claims in the paper.
- [x] **SEM oracle Half-A (positive control) — DONE (2026-07-06).**
      Script: `experiments/exp1_halfA_sem_injection.py`. Reused the already-verified extractor
      output (`experiments/sem_scalebar_results.jsonl`, 293 `status=='ok'` real scale bars from
      NFFA-EUROPE) as ground truth for each image's field-of-view (FOV = scale_bar_nm /
      scale_bar_px × image_px_long_edge). For each real bar, planted a clean claim (1%-90% of
      FOV) or an injected violation (1.2x-3x FOV) at 3 planted rates.
      **Result: FN rate 0.0000 and FP rate 0.0000 at all three planted rates (0.10/0.30/0.50).**
      Also tested a TIGHT boundary case (0.99x FOV vs 1.01x FOV, not just the wide 1.2x-3x/
      1%-90% margins): still 0/293 wrong in both directions. `sem_feature_size_consistent` is a
      simple deterministic threshold with no tolerance ambiguity (unlike XRD's 0.5° window), so
      this clean result is expected, not surprising — the oracle's logic is exact floating-point
      comparison, nothing to mis-calibrate. **This IS a real Half-A result, but a much easier one
      than XRD's** — it validates the oracle's arithmetic is correct, not that real-world scale-bar
      extraction is reliable (that's the separate 97.7%-success extractor number, already measured).
- [x] **Spectrum oracle Half-A (positive control) — DONE (2026-07-06).**
      Script: `experiments/exp1_halfA_spectrum_injection.py`. 300 real RRUFF Raman spectra
      (`excellent_unoriented` grade), 2,272 real measured peaks found via
      `scipy.signal.find_peaks(prominence=0.05, distance=5)` on each spectrum (top 10 by
      intensity per file). Clean claims = real measured peaks; injected violations = an
      x-position verified to be >20cm⁻¹ from every known peak AND directly re-verified against
      `spectrum_peak_exists` itself (not just the abbreviated peak list) before being accepted.
      - **First run had a real harness bug**: verifying injected offsets only against the
        top-10 peak list (not the full signal) let ~10% of "violations" land on a genuine
        SECONDARY peak that simply wasn't in the top 10 by intensity — `spectrum_peak_exists`
        correctly said "consistent" for those, and the harness wrongly counted it as a miss.
        Confirmed directly on a real Abelsonite spectrum (x=900.75, a real bump with prominence
        805 against a required 657 — genuinely satisfies the oracle's own threshold). **Fixed**
        by re-verifying every injected candidate against `spectrum_peak_exists` directly before
        accepting it, exactly the same class of fix as the XRD harness's earlier offset-search bug.
      - **After the fix: FN rate 0.0000 at all three planted rates** (0.10/0.30/0.50).
        **FP rate ~3.0-3.8%** — real, and NOT a harness bug this time. Root cause: `find_peaks`'
        own prominence definition (relative to the normalized signal, scipy's algorithm) and
        `spectrum_peak_exists`'s definition (`local_max - median >= 5% of GLOBAL y-range`) are
        two different mathematical criteria for "significant peak" — confirmed directly, e.g. one
        real local maximum had prominence 464 by raw local contrast but the oracle requires 657
        (5% of that spectrum's full 0-13142 intensity range). **3.5% of scipy-found local maxima
        fail the oracle's own stricter global-threshold test.** This is a genuine, quantified
        finding about the oracle's specific definition, not something to loosen just to make
        Half-A look cleaner — flag to the team whether 5%-of-global-range is the right
        prominence definition for real (noisy, baseline-drifting) Raman data, or whether it
        should be local/windowed instead.
- [x] **Half-B data collection — DONE (2026-07-07).** Half-B (manual precision audit,
      ≥100 oracle-FIRED cases per family) is human work per the runbook, but generating the
      material to review is not — built that part. Scripts:
      `experiments/halfB_collect.py` (generates real model claims via the same
      pilot.py prompts/models, oracle-checks each one, loops per modality until ≥100
      real firings accumulate) and `experiments/halfB_report.py` (renders each modality's
      fired cases into a self-contained HTML review page: image/plot + full model
      reasoning chain + oracle verdict + radio-button review controls with a live
      running precision tally).
      - **Known landmine hit and guarded against**: opXRD contains at least one pattern
        (`CNRS/pattern_678`) with a 13,488-atom basis that hangs pymatgen's XRD symmetry
        analysis indefinitely (observed: >3hrs CPU time before being killed). Added
        `MAX_BASIS_ATOMS = 500` to skip any phase over that size — a permanent guard, not
        a one-off workaround, since more patterns like this likely exist in the full 92,552.
      - **SECOND landmine found 2026-07-11 (during Experiment 3 development):** atom count
        alone does NOT predict a hang. `CNRS/pattern_62.json` (276 atoms, well under the
        500-atom cap) hung `XRDCalculator.get_pattern()` indefinitely — confirmed directly.
        A separate, much smaller pattern (`pattern_735.json`, only 20 atoms) took 15s and
        produced a suspicious 9,742-peak reference pattern, indicating pymatgen's symmetry
        analysis time depends on the structure's actual (low/no) symmetry, not just its
        size. **Fixed properly** by adding a real wall-clock timeout (`signal.alarm`,
        20s) around the specific `calc.get_pattern()` call inside `xrd_reference_peaks`
        (`experiments/halfB_collect.py`) — a thread-based timeout would NOT work here,
        same root reason as the earlier network-hang incident (§13): pymatgen's
        C-extension-backed symmetry code doesn't yield to a thread join, only a genuine
        signal/process-level interrupt stops it. Confirmed fixed: `pattern_62.json` now
        returns `None` after ~20s instead of hanging forever; previously-working patterns
        (`pattern_735`, `pattern_259`) are unaffected, same results as before the fix.
        This function is shared by Half-B collection AND Experiment 3 — the fix benefits
        both, and any future script that imports `xrd_reference_peaks`.
      - **Collection run result**: 101 XRD / 105 SEM / 103 spectrum real fired cases,
        1,261 total model-call records, **total API cost $0.1355** (against the ~$31
        OpenRouter balance). Both models used (local Qwen2.5-VL-7B + API Gemini 2.5
        Flash Lite), same real data sources as the PILOT (opXRD, NFFA-EUROPE, RRUFF).
      - **Review pages**: `experiments/halfB_review_{xrd,sem,spectrum}.html` — each is a
        single static file (5-14MB, images downscaled to 800px/JPEG-82 to keep file size
        reasonable after SEM images alone pushed one page to 92MB at full resolution).
        Open directly in a browser; mark each case Real Violation / False Positive / Unsure;
        "Export My Review" dumps a JSON summary with a live precision tally.
      - **NOT done — this is the actual human step**: nobody has reviewed a single case yet.
        Precision numbers do not exist until someone opens these pages and judges each one.
- [x] **Half-B manual review — DONE (2026-07-07).** Rasul reviewed all 309 fired cases across
      all 3 families (exported via each review page's "Export My Review" button, saved as
      `sem.txt`/`spectrum.txt`/`xrd.txt` in repo root). Zero "unsure" verdicts — every case
      was judged either real or false positive.
      - **Precision results (real / (real + false_positive)):**
        | Family | Reviewed | Real | False positive | Precision |
        |---|---|---|---|---|
        | SEM | 105 | 93 | 12 | **88.6%** |
        | XRD | 101 | 78 | 23 | **77.2%** |
        | Spectrum | 103 | 75 | 28 | **72.8%** |
      - **GATE DECISION: Rasul judged this precision sufficient to proceed** (2026-07-07) —
        an explicit team call per the runbook's "no fixed threshold, team sets it per family"
        rule, not a number that happened to clear an implicit bar. Record this as a deliberate
        decision if it's referenced later, not as evidence the oracles are flawless.
      - **False-positive root-cause check (before the gate decision, for context):**
        - **XRD (23 FPs): mostly a TOLERANCE issue, not a correctness issue.** 16/23 (70%)
          are within 1.0° of a real reference peak, many clustering at 0.5-0.7° — just outside
          the current 0.5° `tol_deg`. Reads as the tolerance being tighter than a reasonable
          human "close enough" read of a plot, not a broken oracle. The other 7/23 are
          genuinely far off (2-6°).
        - **Spectrum (28 FPs): a bigger, less mechanical gap.** Only 5/28 (18%) were even
          near the oracle's 5%-of-global-range prominence threshold; the other 23 have very
          low or NEGATIVE computed prominence at the human-judged peak position — i.e. by the
          oracle's own math there's essentially nothing there. This is NOT simply a tolerance
          question like XRD's — it suggests the prominence definition itself (global range vs.
          local baseline) may not match human judgment of "is there a peak" for noisy,
          baseline-drifting real Raman data. Flagged, not fixed — Rasul's gate call means this
          is accepted as-is for now, but worth revisiting if spectrum PCR numbers look off
          later in Experiment 2.
        - **SEM (12 FPs): not individually root-caused** — smallest gap, lowest priority given
          the gate has already passed.
- [ ] Resolve `latt_dis` units question (2θ vs d-spacing) against the SimXRD paper/sim code before
      wiring `val.db` into the XRD oracle — flag to Mustafa.
- [ ] Decode `Label` and `simulation_param` meanings in `val.db` (README's `tager`/`spg`/`crysystem`
      fields don't exist in this file).
- [ ] Get remaining data: Materials Project (DFT reference values) — still not obtained, blocks
      all 3 DFT-grounded oracles entirely (no Half-A/Half-B possible without it).
- [ ] Clear all `[VERIFY]` dataset URL/license tags.
- [ ] Schedule Mustafa's DFT-protocol review early.
- [x] **PILOT + Experiment 1 (gate) — DONE for XRD/SEM/spectrum (2026-07-07).** Half-A and
      Half-B both complete for the 3 oracle families with real data in hand; Rasul made the
      explicit gate call to proceed on the measured precision (88.6%/77.2%/72.8%). DFT-grounded
      oracles remain fully blocked on Materials Project data — Experiment 1 is NOT complete
      for those 3 families, and per the runbook's own rule this means Experiments 2-6 can only
      proceed on the XRD/SEM/spectrum modalities for now, not DFT-grounded claims.

### Immediate suggested next action (superseded — see §13)
~~The gate has passed for XRD/SEM/spectrum...~~ Superseded 2026-07-10: Experiment 1 gate
passed for ALL 6 families (Hasan's override unblocked the 3 DFT families too), and
Experiment 2 (the full PCR sweep) is now DONE. See §13 below for results and next steps.

---

## 13. Experiment 2 (PCR sweep) — DONE (2026-07-10) — `experiments/exp2_pcr_sweep.py`
Fills the paper's Table 1: PCR with bootstrap 95% CI per (model, modality) cell. n=30
items/cell/seed, S=3 seeds, ALL 6 oracle families, 4 models (local Qwen2.5-VL-7B +
3 frontier API: Gemini 2.5 Flash Lite, GPT-4o, Claude Sonnet 4.5, all via OpenRouter).
Reuses every real data source/prompt/oracle already validated in Experiment 1 — Exp 2
does not redefine anything, it just runs more items through more models.

**Total: 2,026 checkable records aggregated, total API cost $3.42** (of the ~$31
starting OpenRouter balance — plenty of headroom left for Experiments 4-6).

### Two real incidents hit and fixed during this run (both real bugs, not flukes)
1. **A run hung for >1hr on a single OpenRouter call.** Diagnosed via `ss -tnp`: a socket
   sat in CLOSE-WAIT with unread bytes — `urllib.request.urlopen(timeout=60)`'s timeout was
   NOT reliably bounding a stalled response-body read in this environment (only the connect
   phase). First fix attempt (a daemon-thread + `join(timeout)` backstop) did NOT work either
   — the underlying blocking call ignores thread joins, so it just leaked 84 stuck daemon
   threads while the real hang continued. **Real fix**: switched `pilot.py`'s and
   `pilot_dft.py`'s OpenRouter callers from `urllib` to `requests` with an explicit
   `(connect, read)` timeout tuple — `requests` enforces its read timeout per socket
   `.recv()` call, which actually bounds a stalled read. Confirmed fixed: the exact cell
   that hung before (`xrd/gemini/seed=0`) completed cleanly on retry.
2. **Every single Claude call on the SEM modality failed with 400 Bad Request.** Root cause:
   `run_api_openrouter` hardcoded `data:image/png;base64,...` in the payload regardless of
   the real file type. NFFA-EUROPE SEM images are real JPEGs; Gemini/GPT-4o silently
   tolerated the MIME mismatch, but Claude correctly validates the declared type against the
   actual bytes and rejected every call. XRD/spectrum images are genuinely PNG (matplotlib-
   rendered), so this bug was invisible until the sweep reached Claude+SEM specifically.
   **Fixed** with `mimetypes.guess_type(image_path)` instead of a hardcoded type.
3. Added a `--resume` flag to `exp2_pcr_sweep.py` after incident #1 required killing a
   run that had already correctly completed 21 of 24 image-modality cells — resuming
   (skip any (modality, model, seed) cell with ≥50% of n_items already recorded, append
   rather than overwrite) avoided re-spending real API budget on data that was already good.

### Results (n = pooled across all 3 seeds per cell; see `experiments/exp2_aggregate.py`)

| Model | XRD | SEM | Spectrum | Stability* | Metallicity* | Magnetism* | **All** |
|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B (local) | 0.514 | 0.652 | 0.761 | 0.711 | 0.611 | 0.544 | **0.635** |
| Gemini 2.5 Flash Lite | 0.677 | 0.965 | 0.856 | 0.716 | 0.655 | 0.506 | **0.734** |
| GPT-4o | 0.622 | 0.966 | 0.625 | 0.689 | 0.678 | 0.567 | **0.699** |
| Claude Sonnet 4.5 | 0.568 | 0.979 | 0.844 | 0.733 | 0.700 | 0.500 | **0.727** |

*DFT-grounded modality — Materials Project values, NOT YET independently validated by
Mustafa. Report as provisional per the OVERRIDE note in §9.

**Real findings worth flagging (not yet interpreted for the manuscript, just observed):**
- **API models dramatically outperform local Qwen on SEM specifically** (~0.97-0.98 vs
  0.65) — a real, large, consistent gap across all 3 seeds for every API model, not noise.
  Worth investigating whether this is genuine scale-bar-reading skill or something about how
  the smaller local model handles the NFFA-EUROPE info-bar layout variety (see §9's SEM
  layout-variety notes).
- **Magnetism is the hardest modality for every model** (0.50-0.57 range, tightly clustered
  across all 4 models) — consistent with the earlier Half-B finding that the local-vs-net-
  magnetic-moment distinction is a genuinely subtle physics point models don't reliably get
  right, not a single model's weakness.
- **GPT-4o's spectrum cell has a real, much lower n** (48 checkable vs ~88-90 for every other
  model/modality combination) — a parse-rate gap specific to (GPT-4o × spectrum), not
  investigated yet. Do not read GPT-4o's spectrum PCR (0.625) as directly comparable to the
  other cells' PCR until this is understood; it's a smaller, potentially biased sample.
- XRD's overall PCR (0.51-0.68 range) is markedly lower than SEM/spectrum for every model —
  consistent with earlier Half-B findings that the XRD oracle's 0.5° tolerance is tighter
  than typical model precision when reading a peak off a plotted diffractogram.

### Not yet done
- Root-cause GPT-4o's low spectrum checkable-rate (48/90 vs ~88-90 elsewhere).
- Per-constraint-type violation rate ρ_t (matpcr_metrics.violation_rate_by_type) — only PCR
  has been computed so far, not the secondary rho_t breakdown the runbook also asks for.
- Manuscript Table 1 (`matpcr_snjnl.tex`) still has `\rplace{}` placeholders — fill with
  these real numbers, reconciling abstract/title/contributions to what the data shows
  per CLAUDE.md rule 2.
- Experiments 4-6 (CGSV effect, verifier, detector analysis) not started.

### Environment notes (2026-07-04)
- Root disk (`/`) is small and stays near-full (~90%+) — put large data on `/ephemeral`
  (738GB, ext4, root-owned at top level; `ubuntu` needs `sudo -n mkdir`+`chown` once per new
  subdir, then owns it). `/ephemeral/matpcr` holds opxrd + val.db now.
- GPU: NVIDIA A100 80GB PCIe confirmed present.

---

## 14. Experiment 3 (accuracy vs. consistency gap) — DONE (2026-07-11) —
`experiments/exp3_accuracy_vs_consistency.py` + `experiments/exp3_aggregate.py`

Fills the manuscript's "Accuracy versus consistency" subsection (currently a `\torun{}`
placeholder in `matpcr_snjnl.tex`). Goal: on the same items, measure a genuinely
different ACCURACY criterion alongside the existing PCR/consistency check, and report the
four-cell breakdown (correct+consistent / correct+inconsistent / wrong+consistent /
wrong+inconsistent) to show PCR is not just accuracy under another name.

**Scope (decided 2026-07-10):** only 3 of 6 oracle families have a genuine, non-circular
accuracy ground truth distinct from the oracle's own tolerance:
- **XRD**: accuracy = within a tight 0.1° window of the single nearest true reference peak;
  consistency = the existing loose 0.5° oracle tolerance.
- **Spectrum**: accuracy = within a tight 2 cm⁻¹ window of the nearest real measured peak
  (via `scipy.signal.find_peaks`); consistency = the existing prominence-based
  `spectrum_peak_exists` oracle — a genuinely different axis (position vs. prominence).
- **Stability**: accuracy = matches Materials Project's OWN strict `is_stable` label;
  consistency = the oracle's looser 0.05 eV/atom tolerance. Directly reuses the 19%
  definition-mismatch already found during DFT Half-B (§9) — turns that flagged-but-
  unresolved finding into a quantified per-model result.

SEM excluded (current prompt only elicits a feature-size claim, no structured scale-bar-
value claim — no non-circular accuracy ground truth without re-collecting data). Metallicity/
magnetism excluded (no equivalent strict-vs-loose threshold split characterized yet).

**Run:** n=30 items/cell/seed, 3 seeds, 4 models (local Qwen2.5-VL-7B + Gemini 2.5 Flash
Lite + GPT-4o + Claude Sonnet 4.5), 3 modalities × 4 models × 3 seeds = 36 cells, completed
cleanly with no incidents. **918 total checkable records.**

### Results (pooled across all 3 seeds per cell)

| Model | Modality | n | Accuracy | PCR | CC | CI | WC | WI | Gap |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | XRD | 62 | 0.210 | 0.565 | 13 | 0 | 22 | 27 | 0.355 |
| Gemini 2.5 Flash Lite | XRD | 57 | 0.211 | 0.649 | 12 | 0 | 25 | 20 | 0.439 |
| GPT-4o | XRD | 63 | 0.254 | 0.683 | 16 | 0 | 27 | 20 | 0.429 |
| Claude Sonnet 4.5 | XRD | 64 | 0.188 | 0.547 | 12 | 0 | 23 | 29 | 0.359 |
| Qwen2.5-VL-7B | Spectrum | 90 | 0.067 | 0.700 | 4 | 2 | 59 | 25 | 0.678 |
| Gemini 2.5 Flash Lite | Spectrum | 90 | 0.144 | 0.878 | 12 | 1 | 67 | 10 | 0.756 |
| GPT-4o | Spectrum | 42 | 0.071 | 0.571 | 3 | 0 | 21 | 18 | 0.500 |
| Claude Sonnet 4.5 | Spectrum | 90 | 0.067 | 0.756 | 6 | 0 | 62 | 22 | 0.689 |
| Qwen2.5-VL-7B | Stability* | 90 | 0.944 | 0.800 | 71 | 14 | 1 | 4 | 0.167 |
| Gemini 2.5 Flash Lite | Stability* | 90 | 0.689 | 0.633 | 51 | 11 | 6 | 22 | 0.189 |
| GPT-4o | Stability* | 90 | 0.867 | 0.744 | 64 | 14 | 3 | 9 | 0.189 |
| Claude Sonnet 4.5 | Stability* | 90 | 0.867 | 0.711 | 59 | 19 | 5 | 7 | 0.267 |

(CC/CI/WC/WI = raw counts, not fractions. Gap = (CI+WC)/n, the fraction where accuracy
and PCR disagree. *DFT-grounded, NOT YET independently validated by Mustafa.)

**Mean gap across all 12 cells: 41.8%.** This is the headline result: for a large fraction
of items, whether a claim is "accurate" (close to the single true value) and whether it is
"physically consistent" (within the oracle's tolerance) genuinely disagree — confirming
PCR is not accuracy under another name.

**Real findings:**
- **XRD and spectrum are dominated by WC (wrong-but-consistent)**, not CI: models are
  frequently "close enough" to satisfy the oracle's loose tolerance while being measurably
  far from the exact nearest peak. This is the strongest form of the paper's core claim —
  a strict accuracy check would fail these as wrong, but they are not physically incoherent.
- **Spectrum has the largest gaps of any modality (50-76%)** — consistent with the Half-B
  finding that `spectrum_peak_exists`'s prominence threshold is looser than a strict
  positional read, letting many positionally-imprecise claims through as "consistent."
- **Stability's gap is far smaller (17-27%) and inverts the pattern — dominated by CI, not
  WC.** This is exactly the previously-flagged MP `is_stable`-vs-0.05eV/atom-tolerance
  mismatch (§9), now quantified per model: the oracle's looser tolerance calls MORE claims
  consistent than MP's own strict label would call accurate, for every model. Qwen's
  stability accuracy (0.944) is a real, consistent finding across all 3 seeds (0.933/0.900/
  1.000) — not a fluke; likely reflects the sampled materials' real skew toward MP-labeled
  UNSTABLE and models defaulting toward that answer.
- **Gemini is a clear outlier on stability accuracy** (0.689 vs. 0.867-0.944 for the other
  3 models) — a real per-model gap, not yet investigated further.
- GPT-4o's spectrum cell again shows the low-n anomaly already flagged in Experiment 2
  (n=42 vs. 90 for every other model) — same unresolved parse-rate gap, reproduced
  independently in this experiment.

### Not yet done
- Root-cause GPT-4o's persistent low spectrum checkable-rate (now confirmed in 2 separate
  experiments).
- Investigate Gemini's stability-accuracy outlier gap.
- Fill the manuscript's "Accuracy versus consistency" subsection (`matpcr_snjnl.tex`,
  currently `\torun{}`) with this table and findings.

---

## 15. Experiment 4 (CGSV effect) — DONE (2026-07-11) —
`experiments/exp4_cgsv.py` + `experiments/exp4_aggregate.py`

Fills the manuscript's Table 2 (`tab:cgsv`, currently placeholders) and the
`\torun{CGSV before/after with McNemar p-values...}` line in the "Effect of
self-verification" subsection. Implements Algorithm 1 (CGSV) exactly: model
answers once, oracle checks, if a violation is found the model is shown a
non-answer-leaking violation message and revises, up to K rounds or until
consistent, on the SAME items/prompts/oracles already validated in Experiments
1-3 — no new data source or oracle definition introduced.

**Scope: XRD and spectrum only** (of the 6 oracle families). These are the two
modalities where the oracle's feedback is a genuine, actionable physical
constraint the model can re-examine without the message itself stating the
answer. SEM's feedback would effectively reveal the scale factor; the 3 DFT
claim types are single-shot binary classifications with no "look more
carefully" action available (excluded for the same structural reason,
independent of the standing Mustafa-validation caveat on DFT reference values).

**Violation message** (given only on failure, never reveals the correct value):
"Your FINAL_ANSWER does not pass a physical-consistency check: the position you
stated does not match any resolvable peak within tolerance. Look at the plot
again, reconsider the peak's exact apex position, and give a revised answer."

**Implementation note:** required NEW multi-turn model-calling code (pilot.py's
existing `run_local_qwen`/`run_api_openrouter` are single-turn only) —
`run_local_qwen_multiturn`/`run_api_openrouter_multiturn` in `exp4_cgsv.py`,
keeping the model's own prior turns in context with the image attached only to
the first user turn (matches a human re-examining the same plot across a
conversation, not re-sending the image every round). Smoke-tested on both the
local and API code paths (n=3, K=2) before the full run — confirmed the loop
genuinely revises (`rounds_used=2` on a case that stayed inconsistent) and can
genuinely fix a violation (one local spectrum item improved from inconsistent
to consistent across rounds), not a silent no-op.

**Run:** n=30 items/cell/seed, 3 seeds, K=2 max revision rounds, 4 models × 2
modalities × 3 seeds = 24 cells. Completed cleanly, no incidents. **555 total
checkable records, total API cost $1.93.**

### Results (pooled across all 3 seeds per cell; per-model totals pool both modalities)

| Model | Modality | n | PCR before | PCR after | b (regressions) | c (fixes) | p | residual |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | XRD | 68 | 0.647 | 0.706 | 0 | 4 | 0.125 | 20 |
| Gemini 2.5 Flash Lite | XRD | 46 | 0.783 | 0.870 | 0 | 4 | 0.125 | 6 |
| GPT-4o | XRD | 68 | 0.662 | 0.882 | 0 | 15 | 6.1e-05 | 8 |
| Claude Sonnet 4.5 | XRD | 68 | 0.721 | 0.838 | 0 | 8 | 7.8e-03 | 11 |
| Qwen2.5-VL-7B | Spectrum | 89 | 0.652 | 0.742 | 0 | 8 | 7.8e-03 | 23 |
| Gemini 2.5 Flash Lite | Spectrum | 87 | 0.828 | 0.839 | 0 | 1 | 1.00 | 14 |
| GPT-4o | Spectrum | 39 | 0.615 | 0.897 | 0 | 11 | 9.8e-04 | 4 |
| Claude Sonnet 4.5 | Spectrum | 90 | 0.767 | 0.944 | 0 | 16 | 3.1e-05 | 5 |

**Per-model (pooled across XRD+spectrum):**

| Model | n | PCR before [95% CI] | PCR after [95% CI] | b | c | p |
|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | 157 | 0.650 [0.573,0.726] | 0.726 [0.656,0.796] | 0 | 12 | 4.9e-04 |
| Gemini 2.5 Flash Lite | 133 | 0.812 [0.744,0.880] | 0.850 [0.789,0.910] | 0 | 5 | 6.3e-02 |
| GPT-4o | 107 | 0.645 [0.561,0.738] | 0.888 [0.822,0.944] | 0 | 26 | 3.0e-08 |
| Claude Sonnet 4.5 | 158 | 0.747 [0.677,0.816] | 0.899 [0.848,0.943] | 0 | 24 | 1.2e-07 |

**Real findings:**
- **b=0 (zero regressions) in every single cell, both per-cell and pooled.**
  CGSV never broke a previously-consistent claim across all 555 records — a
  genuinely clean, one-directional result, not a coincidence of small N (even
  GPT-4o and Claude's ~100+ record pools show zero regressions).
- **CGSV significantly improves PCR for every model except Gemini**, which is
  directionally positive (0.812→0.850) but does not clear p<0.05 pooled
  (p=0.063) or in either individual modality (p=0.125 XRD, p=1.00 spectrum —
  spectrum contributed only 1 fix). Gemini started from the highest baseline
  PCR of the 4 models, leaving less room for CGSV to fix.
  the standing runbook rule ("small/insignificant is a valid, reportable
  outcome") applies directly here — report honestly, do not overstate.
- **GPT-4o shows the largest, most significant effect** (0.645→0.888 pooled,
  p=3.0e-08) — notable given GPT-4o is the model with the persistent low-n
  parse-rate anomaly on spectrum in every prior experiment; CGSV's fix rate
  itself is not affected by that anomaly (n=39 here is consistent with the
  same ~40-48 pattern seen in Experiments 2-3, and the 11 fixes within that
  smaller pool are still highly significant).
- **Residual violations remain substantial after K=2 rounds** (4-23 per cell,
  roughly 10-35% of each cell) — CGSV reduces but does not eliminate
  violations, consistent with Proposition 1's framing (it's a positive control
  on the oracle, not a guarantee of full correction). Worth noting for the
  manuscript's Discussion: CGSV is a real, measurable improvement, not a fix.
- GPT-4o/spectrum's low-n anomaly (n=39 vs. ~87-90 for other models)
  reproduces yet again — now confirmed in Experiments 2, 3, AND 4. This is a
  strong, cross-experiment signal that it's a real (GPT-4o × spectrum) parse-
  rate property, not noise from any single run.

### Not yet done
- Root-cause GPT-4o's persistent low spectrum checkable-rate (now confirmed in
  3 separate experiments — highest-priority open item).
- Fill manuscript Table 2 (`tab:cgsv`) and the CGSV subsection's `\torun{}`
  placeholder with this table and findings.

---

## 16. Experiment 5 (verifier, the released artifact) — DONE (2026-07-11) —
`experiments/exp5_build_dataset.py` + `experiments/exp5_train_verifier.py` +
`experiments/exp5_aggregate.py`

Fills the manuscript's "Released physical-consistency verifier" subsection and
Table (currently placeholders/`\torun{}`). Fine-tunes an open model on ORACLE
labels only (no human annotation) to predict, from the input description +
reasoning chain text alone (no image), whether a physical violation is
present — exactly the manuscript's stated design.

**Base model (decided 2026-07-11, user choice among 3 options): Qwen2.5-0.5B-Instruct.**
Small enough to fine-tune/release/reproduce cheaply; sufficient capacity for a
binary classification task over structured chain text. LoRA fine-tune (peft,
r=16, alpha=32, target_modules=q/k/v/o_proj) with a sequence-classification
head, 4 epochs, on this A100.

**Training data: 2,416 real records, reused from Experiments 1/2/4's existing
collection files — no new model calls.** `halfB_fired_cases.jsonl` (despite its
name, contains BOTH consistent and inconsistent records, not just fired ones —
205 XRD / 481 SEM / 575 spectrum) + `halfB_dft_fired_cases.jsonl` (236
stability / 518 metallicity / 401 magnetism), each already carrying real
chain_text + oracle_consistent labels from Half-B collection. Each family has
a real, substantial minority class (~100+ examples each) — not a degenerate
label distribution.

**Three splits, each a genuinely separate trained model** (not one model
sliced three ways): (1) random 80/20 stratified split, all 6 families pooled
— in-distribution baseline; (2) held-out modality — train on the other 5,
test on 1 entirely unseen modality, rotated across all 6; (3) held-out
constraint type — same mechanism. **Confirmed empirically: in this benchmark
"modality" and "constraint type" are the SAME 6-way partition (each oracle
family is its own constraint type)** — every held-out-constraint run
reproduces its held-out-modality counterpart's AUC within CUDA-nondeterminism
noise (<0.01 apart). Reported as ONE generalization table, not duplicated.

**Pipeline validated before the full run**: smoke-tested on 40 records (1
epoch, confirms no crash) then 300 records (4 epochs, confirms real learning —
loss dropped 1.03→0.36, AUC=0.854) before committing to the full 13-run
sequence. Full run: 13 independent trainings (1 random + 6×held-out-modality +
6×held-out-constraint), completed cleanly, no incidents, GPU memory released
correctly after each run.

### Results

**In-distribution (random split, all 6 families pooled):** n_train=1933,
n_test=483 — precision=0.709, recall=0.553, F1=0.621, **AUC=0.858**, ECE=0.084.
A genuinely useful in-distribution verifier.

**Held-out generalization (train on other 5 families, test on 1 unseen):**

| Modality | n_test | Precision | Recall | F1 | AUC | ECE |
|---|---|---|---|---|---|---|
| XRD | 205 | 0.667 | 0.020 | 0.038 | 0.462 | 0.482 |
| SEM | 481 | 0.250 | 0.048 | 0.080 | 0.407 | 0.181 |
| Spectrum | 575 | 0.248 | 0.350 | 0.290 | 0.610 | 0.188 |
| Stability | 236 | 0.500 | 0.008 | 0.016 | 0.457 | 0.433 |
| Metallicity | 518 | 0.714 | 0.267 | 0.389 | 0.674 | 0.156 |
| Magnetism | 401 | 0.628 | 0.738 | 0.679 | **0.867** | 0.064 |

**Mean held-out AUC: 0.579** (vs. 0.858 in-distribution — a 0.278 gap).

**Real findings — this is a genuine, important limitation, not a bug:**
- **The verifier does NOT generalize across modalities for 5 of 6 families.**
  XRD (0.462), SEM (0.407), and stability (0.457) are AT OR BELOW CHANCE
  (AUC≈0.5) when held out entirely — the model trained on the other 5
  families has essentially no transferable signal for detecting violations in
  an unseen modality/constraint type. Spectrum (0.610) and metallicity (0.674)
  are weakly better than chance but far below in-distribution performance.
- **Magnetism is the one clear exception** — AUC=0.867 held-out, matching (even
  slightly exceeding) the in-distribution AUC=0.858. This is a real, notable
  anomaly worth investigating: possibly magnetism's chain-text surface
  features (hedging patterns, specific vocabulary around "net moment" /
  "antiferromagnetic" from the earlier Half-B "unsure" cases, §9) are similar
  enough to patterns in the other 5 families' chains that the classifier
  picks up a genuinely transferable signal, or possibly magnetism's chains
  have some other distinguishing lexical tell unrelated to physics reasoning
  quality. Not investigated further — flag as an open question.
- **This directly matches the runbook's own named flag-back trigger**
  ("Verifier does not generalize across modality/constraint → report the
  limit; it is still a useful in-distribution tool") — the correct response
  per the runbook is to report this honestly in the manuscript, not to keep
  tuning until it looks better. The verifier is a real, useful in-distribution
  tool (AUC=0.858) but should NOT be claimed as a general-purpose,
  modality-agnostic detector — that claim would be false given this data.
- ECE is generally worse (higher) on held-out sets than in-distribution
  (0.084 vs. 0.156-0.482), as expected — a model is typically both less
  accurate AND worse-calibrated on distribution shift.

### Not yet done
- Investigate WHY magnetism uniquely generalizes well (chain-text lexical
  analysis, not yet done).
- Release the weights (runbook explicitly asks for this) — LoRA adapters
  currently sit locally at `/ephemeral/matpcr/verifier_weights/`, not yet
  pushed anywhere public.
- Fill manuscript's verifier subsection/table with this real data, explicitly
  stating the generalization limitation rather than only reporting the
  strong in-distribution number.
- Root-cause GPT-4o's persistent low spectrum checkable-rate (still open,
  now confirmed in 3 separate experiments).

**Note (2026-07-11): Experiment 5 was rerun once**, identical in every setting
except the training script was patched to also persist each test item's raw
verifier probability + oracle label (`probs`/`labels` in
`experiments/exp5_results.jsonl`), needed as direct input for Experiment 6
below — no new training logic, same data/splits/hyperparameters. All 13 runs
reproduced their original numbers closely (exact matches on 4 runs, <0.01 AUC
drift on the rest from ordinary training stochasticity) — the findings above
are unchanged and confirmed reproducible.

---

## 17. Experiment 6 (detector analysis) — DONE (2026-07-11) —
`experiments/exp6_detector_analysis.py`

Fills the manuscript's detector-analysis result: does the verifier's predicted
score actually predict a real oracle violation, reported as ROC AUC with a
bootstrap 95% CI — supporting the "practical triage" framing (a released
verifier that ranks/flags likely-violating chains for review without needing
the oracle itself at inference time). Reuses Experiment 5's real per-item
verifier scores and real oracle labels directly (no new training, no new
model calls) — the held-out-modality runs are the correct basis for this
analysis (not the in-distribution run), since a detector's practical value is
in flagging violations in genuinely new data, which held-out-modality
simulates directly.

**Bootstrap method:** resample (score, label) pairs jointly with replacement,
5000 resamples, recompute AUC each time via `matpcr_metrics.roc_auc`, report
the 2.5/97.5 percentiles — the same percentile-bootstrap convention as
`matpcr_metrics.bootstrap_ci`, applied to AUC instead of a mean (a resample
landing on only one class is skipped, since AUC is undefined there; all 5000
resamples were valid in every run, confirming class balance was never that
extreme in these test sets).

### Results

**In-distribution (reference point, not the headline):** n=483, AUC=0.852,
95% CI=[0.811, 0.889].

**Held-out modality (the practical triage scenario):**

| Modality | n | AUC | 95% CI |
|---|---|---|---|
| XRD | 205 | 0.462 | [0.378, 0.543] |
| SEM | 481 | 0.407 | [0.350, 0.465] |
| Spectrum | 575 | 0.619 | [0.563, 0.675] |
| Stability | 236 | 0.457 | [0.381, 0.532] |
| Metallicity | 518 | 0.674 | [0.618, 0.733] |
| **Magnetism** | 401 | **0.867** | **[0.828, 0.904]** |

**Pooled across all 6 held-out modalities:** n=2416, AUC=0.553, 95%
CI=[0.526, 0.580] — the CI does not comfortably clear 0.5 by much; pooling
data this heterogeneous (one modality at 0.867, three near/below chance)
into one number is not very informative on its own and is reported mainly
for completeness, not as a headline claim.

**Practical triage interpretation:**
- **Usable as a triage signal (AUC≥0.7): magnetism only.**
- **Not reliably better than chance (AUC<0.6): XRD, SEM, stability** — their
  95% CIs all comfortably straddle 0.5 (e.g. XRD [0.378, 0.543]), meaning
  there is no statistically defensible claim that the held-out verifier
  detects violations in these modalities at all.
- Spectrum (0.619) and metallicity (0.674) sit in between — weak, uncertain
  signal, CIs excluding 0.5 but with real overlap toward chance-level.

**Bottom line (consistent with and reinforcing Experiment 5's finding):** the
released verifier is a genuine, usable detector in-distribution (AUC≈0.85)
and for magnetism specifically even out-of-distribution, but should **not**
be marketed or used as a general-purpose, modality-agnostic violation
detector — for most held-out modalities its score carries little to no real
signal, with bootstrap CIs that make this a statistically supported
conclusion, not just a point-estimate impression.

### Project status: Experiments 1-6 (matpcr_runbook.txt) are now ALL complete.

**Standing open items carried forward to the write-up/submission phase:**
1. **GPT-4o's low spectrum checkable-rate** — reproduced in 3 separate
   experiments (2, 3, 4) at a consistent ~40-48 n vs. ~87-90 for every other
   model. Never root-caused. Highest-priority remaining investigation before
   claiming GPT-4o's spectrum PCR numbers are directly comparable to other
   cells.
2. **Verifier weights not yet released.** LoRA adapters for all 13 runs sit
   locally at `/ephemeral/matpcr/verifier_weights/<run_name>/` — the runbook
   explicitly asks for public release; not yet pushed anywhere.
3. **Magnetism's anomalously good cross-modality generalization** (both
   Experiments 5 and 6) is unexplained — flagged as an open question, not
   investigated further (possible lexical/hedging-pattern tell in magnetism's
   chain text, per the earlier Half-B "unsure" cases finding in §9).
4. **Mustafa's DFT-protocol review is still pending** — per the standing
   OVERRIDE (§9), all 3 DFT-grounded oracles (stability/metallicity/
   magnetism) and every number derived from them across Experiments 1-6 are
   real, measured results but NOT YET independently validated by the domain
   co-author. This caveat must be carried into the manuscript, cover letter,
   and any supervisor-facing summary regardless of how complete the
   experiments now are — completing Experiments 1-6 does not substitute for
   this review, per §8 rule 4 (2-3 independent human mock reviews before
   submission, which also still stands).
5. Manuscript (`matpcr_snjnl.tex`) still needs every `\torun{}`/`\rplace{}`
   placeholder replaced with the real numbers now sitting in CLAUDE.md
   §§13-17 (Experiments 2-6), and the abstract/title/contributions reconciled
   to what the data actually shows (CLAUDE.md rule 2) — most notably, the
   verifier/detector sections need to state the generalization limitation
   explicitly rather than only the strong in-distribution numbers.

---

## 18. Manuscript placeholders filled — DONE (2026-07-11)

Every `\torun{}`/`\rplace{}` placeholder in `matpcr_snjnl.tex` is now replaced
with real measured numbers from Experiments 2-6 (CLAUDE.md §§13-17): the main
PCR table (already filled in a prior session, verified correct against §13),
accuracy-vs-consistency (§14), the CGSV effect (§15, with Table 2 rebuilt to
report PCR before/after + McNemar per model instead of the old placeholder
rows), the verifier (§16) and detector analysis (§17, new Table 3 for
precision/recall/F1/AUC + bootstrap CIs), and the Discussion section rewritten
from forward-looking "we expect to report" framing to past-tense actual
findings. Every DFT-grounded claim is explicitly flagged in the Results
preamble and the Discussion's closing paragraph as pending Mustafa's review,
per the standing OVERRIDE note (§9) — not just in one place, so a reader
can't miss it by skipping to any single section.

**Compiled clean**: `pdflatex` ×3 (no bibtex rerun needed, existing `.bbl` is
current), zero undefined references, zero errors, 17 pages, 460KB PDF.
Verified by rendering pages 4-8 to text and checking numbers against
CLAUDE.md's tables directly (Table 1's DFT column cross-checked as the
correct per-family average of stability/metallicity/magnetism from §13).

**Still NOT done before real submission** (per the submission checklist and
§8's standing rules, unaffected by this placeholder-filling pass):
- Mustafa's DFT-protocol review (§9's OVERRIDE is a green light to report
  provisional numbers now, not a substitute for the review before final
  submission).
- 2-3 independent human mock reviews (§8 rule 4).
- Every `% VERIFY` citation in `matpcr_refs.bib` read against its real source.
- Recompile on Overleaf with the OFFICIAL (non-patched) `sn-jnl` class before
  actual submission (per `matpcr_README.md`'s standing caveat).
- Author-side items: funding/grant numbers in Acknowledgements, final
  cover-letter pass, fresh arXiv novelty search right before submission.
- The still-open experimental items from §17's wrap-up (GPT-4o spectrum
  low-n, verifier weight public release, magnetism's generalization mystery)
  are referenced honestly in the manuscript text but remain unresolved as
  research questions, not just writing tasks.
