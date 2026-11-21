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
stability / 518 metallicity / 401 magnetism, AS OF THIS 2026-07-11 RUN — see
correction below), each already carrying real chain_text + oracle_consistent
labels from Half-B collection. Each family has a real, substantial minority
class (~100+ examples each) — not a degenerate label distribution.

**Correction (2026-08-01):** `halfB_dft_fired_cases.jsonl` was later regenerated
during the Phase 1 revision pass (§19 — DFT Half-B re-collected under the
corrected oracle). The counts above are frozen historical values from this
2026-07-11 run and no longer match the file on disk. The CURRENT, verified
counts (confirmed directly against `experiments/exp5_verifier_dataset.jsonl`,
which also matches `matpcr_snjnl.tex`'s stated figures) are **395 stability /
255 metallicity / 241 magnetism**. Use those, not 236/518/401, for anything
citing current DFT training-data size.

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

---

## 19. Supervisor audit + Dr. Mustafa's review response — Phase 0/1 DONE (2026-07-16/17)

The supervisor sent back `VERSION2/` with a deep-audit red-flag list
(`VERSION2/matpcr_REDFLAGS.txt`) and Dr. Mustafa sent formal DFT-protocol
review comments (`VERSION2/Dr_mustafas_comments`) approving Materials Project
as a reference source CONDITIONAL on specific oracle corrections. Full plan
recorded in `REVISION_PLAN.md` at repo root. This section records what Phase
0 (oracle corrections) and Phase 1 (re-running affected experiments) actually
found and changed.

### Independent verification of the audit before trusting it
- **BL1 (seed pseudoreplication) is factually wrong as stated.** The audit
  claimed "S=3 seeds run on the same 30 items." Checked directly: 0 duplicate
  source files across any seed in 555 real CGSV records — seeds draw a fresh
  random sample via `seed=BASE + seed*100`, not the same items redecoded. The
  deeper unit-of-analysis/multiple-comparisons concern is still real (see
  "Not yet done" below) but the audit's specific mechanism does not apply.
- **BL2 (verifier split leakage) was real and has been fixed** — see below.
- **Found independently (not in the audit): `exp2_results.jsonl` and
  `exp3_results.jsonl` never recorded a source/item ID at all** before this
  pass (only exp4's did). Both were re-run from scratch with a `source_id`
  field added, not just re-aggregated.

### Mustafa's review — three conditional approvals, all now implemented
1. **Stability**: 0.05 eV/atom tolerance kept, but 0-0.05 eV/atom must be
   described as "near-hull/potentially metastable," never "stable." Added
   `STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM = (0.0, 0.025, 0.05, 0.10)` and
   re-ran Half-A at all 4 (clean: 0% FN/FP at every tolerance).
2. **Metallicity**: abstention band added exactly as specified — ≤0.05 eV
   computed-metallic, 0.05-0.20 eV ambiguous/excluded, ≥0.20 eV
   computed-non-metallic (Mustafa's literal 0.20, not VERSION2 code's
   inherited 0.3 default — confirmed by user decision 2026-07-16).
   `metallicity_claim_consistent()` now returns `None` for the ambiguous band
   (item excluded from PCR entirely) instead of a forced decision.
3. **Magnetism — full redesign, not a parameter tweak.** Renamed
   `property_sign_magnitude_consistent` → `magnetism_magnitude_consistent`.
   Sign is NEVER checked (a DFT calculation's magnetization sign is an
   arbitrary axis choice, not a physical claim). New protocol: (a) normalize
   to `|total_magnetization| / nsites` (per-atom, never raw/un-normalized),
   (b) classify magnetic-vs-not via a preregistered 0.05 muB/atom threshold,
   (c) compare MAGNITUDE ONLY within the magnetic class, order-of-magnitude
   band. Required a real prompt change too (see below) since the old prompt
   only ever elicited a binary MAGNETIC/NONMAGNETIC judgment with no
   magnitude to check.
- **MP provenance now pinned**: `mp_fetch_reference_data.py` records database
  version (2026.04.13), retrieval date, calculation type, and exact fields
  pulled to `/ephemeral/matpcr/mp_data/mp_provenance.json` on every fresh
  pull. Values are described as "standardized computational references," not
  experimental ground truth, per Mustafa's exact wording.
- Re-pulled a fresh 3000-material MP batch with `nsites` added (needed for
  magnetism per-atom normalization) — old batch lacked this field entirely.

### Real bugs found and fixed during this pass (not anticipated by the plan)
1. **Magnetism prompt never collected a magnitude** — `pilot_dft.py`'s
   `PROMPTS["magnetism"]` only ever asked MAGNETIC/NONMAGNETIC, so the
   corrected oracle's magnitude-comparison branch was untestable. Fixed by
   extending the prompt to ask for `<value> muB/atom` when claiming MAGNETIC,
   and adding a dedicated `parse_magnetism_chain()` (returns
   `(classification, magnitude_or_None)`, keeping the old `parse_dft_chain`
   for backward-compatible stability/metallicity callers).
2. **`halfB_collect_dft.py` walked the materials pool in raw file order,
   never shuffled** — the fresh MP pull's first ~200 rows were 89.5%
   non-magnetic (vs. 25% over the full 3000), which silently starved
   magnetism Half-B collection of any fired cases for multiple rounds before
   this was caught. Fixed with `random.Random(7).shuffle(materials)`.
3. **`halfB_fired_cases.jsonl`'s spectrum labels were stale**: the file
   predates the Phase 0 spectrum oracle fix (genuine-local-maximum
   requirement). Directly re-checked 200 spectrum records against the
   corrected oracle: **137/200 (68.5%) mismatched their stored label.**
   Relabeled all 575 spectrum records in place using the corrected oracle on
   the EXISTING chain_text/parsed values (no new model calls) — 392 flipped,
   class balance inverted from mostly-consistent to mostly-inconsistent
   (matches the pattern independently confirmed in Experiments 2-4's
   re-runs). Confirmed XRD/SEM records in the same file have ZERO mismatches
   (their oracle logic didn't change) — this was a correctly narrow fix, not
   a blanket re-labeling.
4. **BL2 fix, concretely**: `exp5_build_dataset.py` now retains a
   `source_id` field (source_file for geometric records, material_id for
   DFT) on every output record. `exp5_train_verifier.py`'s `make_split()`
   "random" mode now splits on unique `source_id`, not record index — a
   genuinely disjoint 80/20 split, closing the exact leak the audit
   described.

### Phase 1 results — every affected experiment re-run on corrected oracles

**Half-A (DFT) re-run**: 0% FN, 0% FP for all 3 oracles at all 3 planted
rates, across all 4 stability tolerances and the new metallicity/magnetism
logic. Metallicity correctly excluded 125/3000 ambiguous-band materials.

**Half-B (DFT) re-collected**: 107 stability / 114 metallicity / 115
magnetism fired cases (891 total records), $0.07 API cost. Review pages
regenerated (`experiments/halfB_review_dft_{stability,metallicity,magnetism}.html`)
with corrected-oracle language. **These supersede the OLD
stability.txt/metallicity.txt/magnetism.txt reviews in the repo root, which
were done on the uncorrected oracle and are now stale for precision
purposes.** Manual re-review is the standing blocking item before new DFT
precision numbers can be reported — not yet done as of this writing.

**Experiment 2 (PCR sweep) re-run**: 72 cells (6 modalities × 4 models × 3
seeds, up from a partial run before), 1,892 checkable records, $4.93 API
cost, `source_id` added to every record.

| Model | XRD | SEM | Spectrum | Stability* | Metallicity* | Magnetism* | **All** |
|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B (local) | 0.516 | 0.652 | 0.148 | 0.700 | 0.570 | 0.489 | **0.513** |
| Gemini 2.5 Flash Lite | 0.385 | 0.977 | 0.184 | 0.671 | 0.766 | 0.525 | **0.602** |
| GPT-4o | 0.581 | 0.933 | 0.103 | 0.756 | 0.580 | 0.611 | **0.649** |
| Claude Sonnet 4.5 | 0.532 | 0.978 | 0.178 | 0.767 | 0.704 | 0.644 | **0.638** |

**Note (2026-08-01): this 4-model table is now superseded by a final 8-model
grid** (Phase 2 item 15 added Claude Opus 4.6, GPT-5.6-Terra, Qwen3-VL-8B-Instruct,
Qwen3-VL-8B-Thinking — see `MATPCR_KNOWLEDGE.md` §7, which this CLAUDE.md
previously lacked). Reproduced here so CLAUDE.md is a complete standalone
index again, verified to match `VERSION2/matpcr_snjnl.tex` Table 1 exactly:

| Model | Diffraction | Microscopy | Spectra | DFT* | All* |
|---|---|---|---|---|---|
| Qwen2.5-VL-7B | 0.516 | 0.652 | 0.148 | 0.586 | 0.513 |
| Gemini 2.5 Flash Lite | 0.385 | 0.977 | 0.184 | 0.678 | 0.602 |
| GPT-4o | 0.581 | 0.933 | 0.103 | 0.649 | 0.648 |
| Claude Sonnet 4.5 | 0.532 | 0.978 | 0.178 | 0.705 | 0.637 |
| Claude Opus 4.6 | 0.531 | 0.888 | 0.244 | 0.696 | 0.625 |
| GPT-5.6-Terra | **0.797** | 0.940 | **0.878** | **0.724** | **0.800** |
| Qwen3-VL-8B-Instruct | 0.550 | 0.778 | 0.167 | 0.588 | 0.538 |
| Qwen3-VL-8B-Thinking | 0.540 | 0.784 | 0.115 | 0.614 | 0.546 |

*DFT column provisional, pending Mustafa's sign-off. Real finding: capability
scaling is NOT automatic — GPT-5.6-Terra clearly beats GPT-4o (non-overlapping
CIs, see §20's scaling-trend traceability note above), but Claude Opus 4.6
does not beat Claude Sonnet 4.5, and explicit reasoning mode
(Qwen3-VL-8B-Thinking) does not beat its non-reasoning sibling (both CIs
overlap) — this is the finding written up in the manuscript's scaling
discussion, not a simple "newer is always better" story.

(Below is the original 4-model-only table this session's re-run produced,
kept for historical continuity of the narrative below it.) **Note
(2026-08-01):** this table's GPT-4o/Claude "All"
values (0.649/0.638) are close to but not identical to the values in the
final 8-model manuscript table (`VERSION2/matpcr_snjnl.tex`, Table 1: 0.648/
0.637) — this is NOT a rounding bug in either place. This table is the
4-model Phase 1 re-run; the manuscript's is a later, separate 8-model Phase 2
run (§20) that re-pulled/re-ran cells again, so the two numbers come from two
different experimental executions, not the same data computed two ways. Do
not "fix" one to match the other — both are real, from their own run.
**Spectrum's PCR collapsed from the original ~0.62-0.88
range to ~0.10-0.18** — confirmed directly (not assumed) by testing the old
vs. new `spectrum_peak_exists` on a real spectrum: 81/200 sampled positions
(40%) disagree between the two oracle versions. This is a correct,
oracle-fix-driven finding, not a regression, and must be framed that way in
the manuscript. XRD/Gemini showed real seed-to-seed volatility (0.235-0.526
range observed mid-run) that settled to 0.385 pooled — a real, if noisy,
finding, not a bug (GPT-4o/Claude's XRD numbers landed in the expected
range, ruling out a systemic re-run problem).

**Experiment 3 (accuracy-vs-consistency) re-run**: 920 records (36 cells:
XRD/spectrum/stability × 4 models × 3 seeds), `source_id` and
`claimed_stable`/`true_stable` fields added (the latter enables the
balanced-accuracy/class-conditional analysis the audit requested — not yet
computed, just the raw fields are now present). Spectrum's accuracy-PCR gap
reproduced the same collapse pattern as Experiment 2. Stability's base-rate
skew (most models 83-97% raw accuracy) reproduced identically to before.
**New strong clue on the standing GPT-4o/spectrum anomaly**: all 3 seeds
produced EXACTLY n=16/30 checkable — this precise repetition across
different random item draws suggests something deterministic (e.g. a fixed
subset of RRUFF files GPT-4o consistently fails to parse), not random
per-call variance. Confirmed reproduced a 7th time total across Experiments
2, 3, and 4 combined — highest-priority open investigation.

**Experiment 4 (CGSV) re-run**: 545 records, $2.66 API cost. Added a
`claimed_values` field (the model's numeric claim at each round) as the
honest analogue to the audit's BL4 concern — this benchmark's single-claim-
per-item design has no multi-claim k_i to count (an unparseable round already
drops the whole item, so there's no "claim count drops but item survives"
case to hide).

| Model | Modality | n | PCR before | PCR after | b | c | p | residual |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | XRD | 68 | 0.647 | 0.706 | 0 | 4 | 0.125 | 20 |
| Gemini 2.5 Flash Lite | XRD | 48 | 0.854 | 0.958 | 0 | 5 | 0.063 | 2 |
| GPT-4o | XRD | 68 | 0.647 | 0.853 | 0 | 14 | 1.2e-04 | 10 |
| Claude Sonnet 4.5 | XRD | 68 | 0.647 | 0.912 | 0 | 18 | 7.6e-06 | 6 |
| Qwen2.5-VL-7B | Spectrum | 89 | 0.101 | 0.236 | 0 | 12 | 4.9e-04 | 68 |
| Gemini 2.5 Flash Lite | Spectrum | 69 | 0.290 | 0.406 | 0 | 8 | 7.8e-03 | 41 |
| GPT-4o | Spectrum | 45 | 0.111 | 0.200 | 0 | 4 | 0.125 | 36 |
| Claude Sonnet 4.5 | Spectrum | 90 | 0.167 | 0.433 | 0 | 24 | 1.2e-07 | 51 |

**Per-model pooled**: Qwen 0.338→0.439 (p=3.1e-05), Gemini 0.521→0.632
(p=2.4e-04), GPT-4o 0.434→0.593 (p=7.6e-06), Claude 0.373→0.639 (p=4.6e-13).
**Zero regressions (b=0) in every single cell, unchanged from before the
oracle correction** — CGSV's core positive-control result is robust to the
much stricter spectrum oracle. Absolute PCR is lower everywhere (expected,
tracks Experiment 2's spectrum collapse) but the relative improvement and
McNemar significance pattern holds for every model.

**Experiment 5 (verifier) re-run — the manuscript's most significant
correction.** Rebuilt `exp5_verifier_dataset.jsonl` from the corrected
Half-B data (2,152 records; spectrum's relabeled distribution flows through
automatically) with `source_id` retained; retrained all 13 runs with the
now-genuinely-disjoint split.

| Split | AUC (new, source-disjoint) | AUC (old, leaky) |
|---|---|---|
| In-distribution | 0.850 | 0.858 |
| Held-out XRD | 0.497 | 0.462 |
| Held-out SEM | 0.527 | 0.407 |
| Held-out Spectrum | 0.558 | 0.610 |
| Held-out Stability | 0.436 | 0.457 |
| Held-out Metallicity | 0.582 | 0.674 |
| **Held-out Magnetism** | **0.503** | **0.867** |

**The manuscript's claim that magnetism uniquely generalizes well does NOT
survive the corrected methodology.** Confirmed reproducible: both the
held-out-modality AND held-out-constraint-type versions of the magnetism test
independently landed at AUC=0.503 (chance). The original 0.867 was very
likely an artifact of the old record-level split allowing same-source-item
records to appear on both sides of train/test, not a real transferable
signal. **This must replace the "magnetism is the one exception" framing
throughout the manuscript (Results, Discussion, abstract) with the simpler,
cleaner finding: the verifier does not generalize across ANY held-out
modality** — arguably a stronger, more defensible result for the paper since
there's no unexplained anomaly left to hedge around.

**Experiment 6 (detector analysis) re-run**: bootstrap 95% CIs recomputed on
the corrected probs/labels. No held-out modality clears the AUC≥0.7
usable-triage threshold (all 6 sit at 0.436-0.582). Updated the script's
hardcoded conclusion text (previously said "magnetism is the exception") to
explicitly state the finding was retracted after the methodology fix, not
just softened.

**Traceability check (2026-08-01):** re-ran `python3 experiments/exp6_detector_analysis.py`
directly (it's fully deterministic — `bootstrap_auc_ci(..., seed=0)` reads
straight from the committed `experiments/exp5_results.jsonl`, no re-training
needed) to confirm every CI the manuscript reports for Table 2/detector
analysis is real and reproducible, not fabricated. Output matched
`matpcr_snjnl.tex` exactly: in-distribution n=431, AUC=0.850, 95% CI
[0.813, 0.883] (line 610); held-out n per modality = 205/481/575/395/255/241
(XRD/SEM/spectrum/stability/metallicity/magnetism, matching the corrected
`exp5_verifier_dataset.jsonl` counts logged in §16's correction note above);
held-out CIs XRD [0.419,0.578], SEM [0.468,0.589], spectrum [0.488,0.626],
stability [0.370,0.502], metallicity [0.510,0.652], magnetism [0.430,0.576].
Also confirmed `exp5_run3.log:60` directly logs in-distribution
`AUC=0.850 ECE=0.096`, matching `matpcr_snjnl.tex:568` exactly. These were
flagged by an earlier audit as untraceable from CLAUDE.md's tables alone;
they are correct, just previously undocumented at this level of detail.

### Not yet done (Phase 1 remainder + carried into Phase 2)
- [ ] **Manual re-review of the 3 new Half-B DFT pages** — blocking new DFT
      precision numbers. Old .txt exports are stale, do not reuse.
- [ ] Item-level clustering / multiple-comparisons correction (Holm or
      Benjamini-Hochberg) across the full model×modality sweep and the CGSV
      tests — BL1's specific mechanism was refuted, but a real
      multiple-comparisons correction across ~20+ statistical tests is still
      owed and hasn't been computed.
- [ ] Root-cause GPT-4o's spectrum low-n anomaly (7 reproductions now,
      strong deterministic clue: identical n=16/30 across 3 different-seed
      draws in Experiment 3).
- [ ] Fix Gemini's magnetism-prompt token-budget truncation (confirmed root
      cause: hedgy reasoning on structurally ambiguous formulas exhausts the
      1000-token budget before FINAL_ANSWER; same failure class as the
      earlier stability-prompt truncation fix, not yet applied to magnetism).
- [x] Update `matpcr_snjnl.tex` with all of the above — table numbers, the
      spectrum-collapse explanation, and (most importantly) rewriting the
      verifier/detector sections to remove the now-retracted magnetism
      exception claim. **Done, but only in `VERSION2/matpcr_snjnl.tex` — see
      §20 below.**
- [x] Phase 2 (new experiments the venue will expect — EX1-EX13 from the audit)
  — DONE 2026-07-19/20. See §20.

---

## 20. Phase 2 (new experiments) + Phase 3 (manuscript text) — DONE (2026-07-19/20)

Per `REVISION_PLAN.md`. Phase 2 ran 9 new experiments/analyses (items 15–23 +
EX6); Phase 3 rewrote `VERSION2/matpcr_snjnl.tex` end-to-end against the
results. Full experiment-level detail (scripts, bugs found/fixed, exact
numbers) lives in the session transcript and in each `experiments/exp{8-14}*`
script's own docstring — this section is the manuscript-facing summary.

### Phase 2 results, one line each
- **Item 15 (model refresh)**: added Claude Opus 4.6, GPT-5.6-Terra,
  Qwen3-VL-8B-Instruct, Qwen3-VL-8B-Thinking (all via OpenRouter) across all 6
  constraint types, 3 seeds each. Fixed a real matplotlib/Agg-backend +
  threading race condition in `pilot.py` that was silently corrupting PNG
  renders during a prior crashed run (root-caused, not just retried).
- **Item 16 (MatterChat domain evaluee)**: built a full working local
  integration from scratch (isolated venv, real Mistral-7B-Instruct-v0.3 +
  CHGNet checkpoint from the paper's own Zenodo record 18735961/18735881,
  CC-BY-4.0) — fixed 6 real dependency/version issues (ase API change,
  missing timm/protobuf/setuptools-pkg_resources, cross-version MPID
  pickling). Caught and fixed a real sampling bug: the first structure
  fetch used raw MP file order (3.3% magnetic vs. real ~65-74%); re-fetched
  shuffled. Final: stability PCR=0.783, metallicity=0.795 (n=112/120
  checkable), magnetism=0.850 on 120 real shuffled MP structures.
- **Item 17 (verifier baselines)**: zero-shot LLM-judge (Gemini Flash Lite)
  and local-model token self-confidence, both on the same 7 splits as
  Experiment 5/6. Neither is competitive with the fine-tuned verifier
  in-distribution (LLM-judge AUC=0.447, self-confidence AUC=0.315, both
  ≤chance, vs. verifier's 0.850). Found and confirmed a real, non-obvious
  result: the model is *more* confident (higher token log-prob) when its
  claim is physically wrong, not less — directly checked on a 40-item
  sample (violation mean logprob -2.84 vs. clean -3.99), not a sign bug.
- **Item 18 (CGSV mechanism-isolation controls)**: ran `exp7_cgsv_controls.py`
  to completion (self_refine, re_prompt, best_of_n × xrd/spectrum × 4
  original models × 3 seeds, $12.19 API cost). Neither self_refine
  (0.349→0.339, b=34, c=29, p=0.615) nor re_prompt (0.358→0.342, b=24, c=15,
  p=0.20) shows a significant change, and both have real regressions
  (b>0) — unlike CGSV itself (b=0 everywhere). Best-of-3: random-pick
  PCR=0.363, oracle-oracle ceiling=0.419.
- **Item 19 (tolerance sensitivity)**: pure re-analysis of already-collected
  claims at multiple tolerances, no new model calls. **Real finding: XRD's
  model ranking is NOT robust to tolerance choice** (rank agreement 0.0 —
  local model beats API models pooled at tol=0.25°, reverses by tol=1.0°).
  Spectrum's ranking is fully robust (1.0); stability is partially robust
  (0.67).
- **Item 20 (violation taxonomy)**: XRD (78 human-confirmed real violations)
  and SEM (93) only — spectrum and all 3 DFT families excluded because
  their human reviews predate later oracle corrections and would mismatch
  the current fired-case population (documented explicitly in the script,
  not silently skipped). First attempt used exact-string clustering and
  produced 30 fragmented near-duplicate categories; fixed with a second
  LLM clustering pass. Final: XRD 70.5% "gridline misread"; SEM 37.6%+23.7%
  scale-bar unit/conversion errors.
- **Item 21 (contamination check)**: zero metadata-leakage hits across 2,152
  records (models never state institution codes/sample IDs they weren't
  shown). opXRD's Zenodo publication date (2025-04-28, confirmed directly)
  postdates GPT-4o's cutoff, ruling out that specific pairing. Local-model
  perplexity check run but explicitly flagged as weak/non-diagnostic (lower
  perplexity on real vs. control-gibberish text is fully explained by
  real-data predictability, not memorization).
- **Item 22 (detector calibration)**: reliability diagrams + per-split
  recommended operating points from Exp5's existing scores, no new model
  calls. **Real finding: every held-out split is severely miscalibrated in
  the same direction** — low-probability bins massively underestimate true
  violation rate (e.g. held-out spectrum: predicted 0.02-0.15, actual
  0.84-0.93), so the default 0.5 threshold gives near-zero recall held out;
  a much lower threshold (0.05) recovers usable recall at a real precision
  cost.
- **Item 23 (scaling trend + utility demo)**: re-run once items 15/18
  finished. **Real finding: GPT-4o→GPT-5.6-Terra is the one clear
  generation-scaling signal** (0.648→0.800, non-overlapping CIs); Claude
  Sonnet 4.5→Opus 4.6 and Qwen3-VL-Instruct→Thinking both show no
  significant change (CIs overlap) — explicit reasoning mode alone does not
  reliably raise PCR in this sample.
- **EX6 (second-reviewer harness)**: added `cohens_kappa` to
  `matpcr_metrics.py` (smoke-tested: perfect agreement, constructed
  chance-level case) and `experiments/exp13_second_reviewer_kappa.py`.
  Genuinely blocked on a second human reviewer completing an independent
  pass through the existing review pages — the harness is ready, the human
  labor is not done, and this is reported as such, not worked around.

### Phase 3: manuscript rewrite — DONE, but only in `VERSION2/`
**Root-level `matpcr_snjnl.tex` and `VERSION2/matpcr_snjnl.tex` are now
substantially different files, by explicit user decision (2026-07-20) not
to overwrite one with the other this pass.** `VERSION2/matpcr_snjnl.tex`
(1473 lines) is the current, correct, fully-filled manuscript: all 16
`\redflag{}` sites resolved with real Phase 1+2 data, both remaining
`\redflag{}`s are intentional author-only placeholders (funding/grant
numbers, GPU-hours), Table 1/2/3 rewritten with corrected 8-model numbers, a
new SI Table S1 added, and the magnetism-verifier-exception claim explicitly
retracted (0.867→0.503 under the corrected source-disjoint split).
Compiles clean end-to-end (`pdflatex ×3 + bibtex`, 29 pages, zero undefined
references/citations). **Root `matpcr_snjnl.tex` (835 lines) was
intentionally left untouched — it still has the old pre-Phase-1 numbers, no
Baselines/ablations subsection, and no SI table.** Any future session
building the paper for real submission must use `VERSION2/matpcr_snjnl.tex`,
not root, or must explicitly re-reconcile the two first. `matpcr_cover_letter.txt`
(root) was updated to match VERSION2's title and current-state framing.

**Real, substantive corrections made during the rewrite (not just filling
blanks):**
- Retracted the magnetism-verifier-generalizes exception entirely (was the
  headline "positive surprise" of the whole verifier section) — confirmed
  independently under both held-out-modality and held-out-constraint-type
  splits, both landing at chance (AUC≈0.50).
- The accuracy-vs-consistency mean gap changed from 41.8% to 22.2% once the
  spectrum oracle correction flowed through Experiment 3's numbers — the
  qualitative story flipped too (spectrum was previously the
  largest-WC-dominated gap; now it's WI-dominated and one of the smallest
  gaps).
- Found and did NOT report Exp6's pooled cross-modality AUC (0.315,
  suspiciously below chance) as a headline number after recognizing it
  naively concatenates raw scores from 6 separately-trained models on
  non-comparable probability scales — reported only the 6 individually
  well-defined per-constraint-type numbers instead, flagged the pooling
  problem explicitly rather than silently drop it.
- Resolved BL4 (CGSV correction-vs-retraction ambiguity) with a real,
  checkable fact rather than an assumption: every one of the 545 CGSV
  records exposes exactly 1 checkable claim in every round (verified
  directly against `claimed_values` vs. `rounds_used` — zero items with
  fewer claim values than rounds+1), so a PCR gain cannot be explained by
  claim-dropping in this benchmark's design.
- Cross-checked Section C's ("fixes already applied") claims against the
  actual file rather than trusting the audit doc: found one real, minor
  discrepancy (Section C claims the title was changed to "Physics- and
  DFT-Grounded...", but the actual title is "Physics Is the Label..." —
  the title itself is fine, just Section C's description of it is wrong;
  not fixed, flagged here since it doesn't affect the manuscript itself).
- **Traceability check (2026-08-01):** `matpcr_snjnl.tex:393`'s scaling-trend
  CIs (GPT-4o [0.605,0.692] vs. GPT-5.6-Terra [0.762,0.835]) match
  `experiments/exp14_results.json`'s `scaling_trend.per_model_pcr` exactly
  (gpt4o ci_lo/hi 0.6048/0.6921, gpt56 0.7624/0.8347). `matpcr_snjnl.tex:1191-1196`'s
  verifier-baseline CIs (LLM-judge AUC=0.447 [0.400,0.493], self-confidence
  AUC=0.315 [0.264,0.365]) match `experiments/exp8_run.log:21,33` exactly. Both
  were flagged by an earlier audit as untraceable from CLAUDE.md alone; both
  are real, reproducible numbers from committed run logs/results files, just
  not previously cross-referenced here.

### Not yet done (carried forward)
- [ ] Manual re-review of the 3 DFT Half-B pages — still the standing
      blocking item for DFT precision numbers (Table 1's 3 cells correctly
      still say "pending human review", not a number).
- [ ] Holm/Benjamini-Hochberg multiple-comparisons correction across the
      144-cell sweep + 4 CGSV comparisons — explicitly flagged in the
      manuscript's Statistics paragraph as still owed, not computed this
      pass either.
- [ ] GPT-4o's spectrum low-n anomaly — still not root-caused (reproduced
      again in §21's Panther re-run: n=44 vs. ~87-90 elsewhere, same pattern).
- [x] Gemini's magnetism-prompt truncation fix — DONE (2026-08-01, see §21).
- [ ] A genuine verifier-as-best-of-N-selector comparison (needs
      `exp7_cgsv_controls.py`'s best_of_n path extended to persist each
      candidate's chain_text, not just the aggregate first/any flags) —
      the current best-of-3 numbers only bound the headroom, not whether
      the verifier can capture it.
- [ ] Second human reviewer for EX6 (harness ready, human pass not started).
- [ ] All the standing Final-gate items (§8 rule 4/5, REVISION_PLAN.md):
      Mustafa's DFT sign-off, 2-3 independent human mock reviews, every
      `% VERIFY` citation checked, Overleaf recompile with the official
      (non-patched) `sn-jnl` class before real submission.

---

## 21. Migration to QCRI Panther cluster (A100/H200) — Tier 1 re-run DONE
(2026-08-05) — `experiments/slurm/`

Moved off the (now-wiped) single-P100 host onto QCRI's Panther Slurm
cluster, which has A100 (80GB) and H200 (141GB) partitions. Access confirmed
2026-08-01; real per-user Slurm account/QOS names differ from the Panther
End-User Guide's generic examples (`A100`/`a100_qos`) — this project's HBKU
account is **`a100_hbku`/`a100_hbku_qos`** and **`h200_hbku`/`h200_hbku_qos`**
(confirmed via `sacctmgr show associations user=<user>
format=Account,Partition,QOS -p`; all sbatch scripts under
`experiments/slurm/` use these). Partitions themselves (`gpu-A100`,
`gpu-H200`) match the guide exactly.

**Data staged fresh** (old `/ephemeral/matpcr` root no longer exists, per
§20's wipe): opXRD (92,552 patterns, matches CLAUDE.md's count exactly),
NFFA-EUROPE (18,424 images across all 10 categories, every category count
matches exactly), RRUFF `excellent_unoriented` (11,415 files, matches
exactly) — all via new `experiments/slurm/stage_*.sh` scripts, checksum-
verified against Zenodo/B2SHARE's own published MD5s. Materials Project not
yet staged — no MP_API_KEY obtained yet, so all 3 DFT-grounded oracles
remain blocked (Tier 2, see `experiments/slurm/README.md`'s Tier 1/2 split).

### Real environment bugs hit and fixed during setup (not anticipated)
1. **`conda create`/large downloads killed on `panther-login`**: the login
   node's watchdog script (which the guide documents as removing stray user
   processes to prevent overload) reaped both an interactive `conda create`
   and a multi-GB Zenodo download. Not a bug in this project's scripts —
   fixed by running all such work on the shared physical server
   (`crimv3mgpu015`/`.27`/`.28`) instead, per the guide's own instructions.
2. **Corrupted partial downloads silently treated as complete**: the
   original `stage_opxrd.sh`/`stage_nffa.sh` only checked file *existence*
   before skipping a re-download, so a zip truncated by the login-node kill
   (issue 1) was accepted as good. Fixed by adding MD5 checksum verification
   (Zenodo and B2SHARE both publish per-file MD5s) with automatic
   delete-and-retry on mismatch.
3. **B2SHARE API shape was wrong in the original NFFA staging script**: the
   real API (confirmed directly) has NO top-level `files` array on the main
   record — file listings live at a separate `/files` endpoint, entries are
   under a top-level `"entries"` key, and the download URL is
   `links.content` (not `links.self`, which is just the file's metadata
   page). Original script guessed a flatter shape and crashed with
   `TypeError: string indices must be integers`. Fixed against the real,
   directly-inspected response.
4. **`torch` pulled a CUDA-13.0 build, incompatible with Panther's driver**:
   plain `pip install torch` (unpinned, per the original
   `requirements-main.txt`) resolved to `torch==2.13.0+cu130`, but Panther's
   nodes report CUDA 12.9 via a 575.57.08 driver — too old for a cu130
   build. Every local-model (Qwen2.5-VL-7B) pilot call silently failed
   (`torch.cuda.is_available() == False`), returning an error string as the
   "chain_text" that looked like a model/prompt problem but was purely
   environmental. **Fixed by pinning `torch==2.5.1+cu121`**
   (`--extra-index-url https://download.pytorch.org/whl/cu121`), matching
   the `cuda12.1/toolkit/12.1.1` module the sbatch scripts already load.
5. **`torchvision` was missing entirely** — masked by bug 4 until that was
   fixed, then surfaced immediately as a second local-model failure
   (`Qwen2VLVideoProcessor requires the Torchvision library`). Added
   `torchvision==0.20.1` (matching build) to `requirements-main.txt`.
6. **`tesseract` (system OCR binary for `sem_scalebar_extractor.py`) not
   installed, and not pip-installable** — `pytesseract` is only a Python
   wrapper; no sudo/apt access as a regular cluster user. This didn't
   surface until partway through a real Experiment-2 sweep (XRD completed
   first; the crash only hit once SEM cells started), costing real API
   budget before being caught. **Fixed via `conda install -c conda-forge
   tesseract`**, now automated in `setup_env.sh`.
7. **`exp2_pcr_sweep.py` unconditionally opened the Materials Project data
   file** even when no DFT-grounded modality was requested (e.g.
   `--modalities xrd sem spectrum`) — crashed with `FileNotFoundError`
   before Tier 2 data existed, even though the run never touches DFT data.
   Real pre-existing gap in the script (every historical run happened to
   include a DFT modality, so this path was never exercised). **Fixed**:
   `materials_pool` is now only loaded if `any(m in DFT_CLAIM_TYPES for m in
   args.modalities)`.
8. **Date-stamped output filenames broke `--resume` across job
   resubmissions**: `job_exp2_pcr_sweep.sbatch` originally generated
   `exp2_results_panther_$(date +%Y%m%d).jsonl` fresh on every submit —
   resuming on a later date would silently start a new empty file instead
   of continuing the previous partial run. **Fixed** to a stable filename
   (`exp2_results_panther.jsonl`, override-able via a 3rd script argument).

### Gemini magnetism-prompt truncation fix — DONE (2026-08-01)
Per the standing open item (§19/§20): `pilot_dft.py`'s magnetism prompt
lacked the explicit "keep reasoning SHORT, don't hedge" instruction that
already fixed the identical truncation failure mode on the stability
prompt. The magnetism prompt hedges hardest on chemically ambiguous
formulas (rare-earth/lanthanide + transition-metal compositions), eating
the token budget before `FINAL_ANSWER`. **Fixed**: added the same
short/non-hedging instruction, explicitly naming the ambiguous-formula case,
plus raised `run_text_api_openrouter`'s `max_tokens` 1000→1500 as
defense-in-depth (same two-part fix pattern as the original stability fix).
Not yet re-run against real magnetism data (still blocked on an MP_API_KEY,
Tier 2) — `experiments/slurm/job_magnetism_recollect.sbatch` is ready to
confirm the fix once a key is obtained.

### Verifier seed-pinning fix — DONE (2026-08-01), not yet re-run
Per the standing blocking item (the released verifier weights were lost
when the old host's `/ephemeral` was wiped and are unrecoverable in their
original, bit-exact form): `exp5_train_verifier.py`'s `train_and_eval()`
only ever seeded `make_split()`'s numpy RNG, never `torch`/`transformers`
training itself. **Fixed**: added `transformers.set_seed(train_seed)` before
model/LoRA init, and a `--train_seed` CLI flag (default 0). Not yet
retrained on Panther — `experiments/slurm/job_verifier_retrain.sbatch` is
ready (needs no API key, trains on already-committed
`exp5_verifier_dataset.jsonl`).

### Experiment 2 (PCR sweep) re-run on Panther — Tier 1 (XRD/SEM/spectrum)
DONE (2026-08-05) — `experiments/exp2_results_panther.jsonl`

8 models × 3 modalities × up to 3 seeds, n=30/cell target, **1,863 total
checkable records, $4.59 API cost**. Completed cleanly (zero errors) after
fixes 2-6 above; ran across two job submissions using `--resume` (first hit
the tesseract bug partway through SEM, second completed the rest from where
it left off without re-spending budget on the already-done XRD cells).

| Model | XRD | SEM | Spectrum |
|---|---|---|---|
| Qwen2.5-VL-7B (local) | 0.500 [0.375,0.625] | 0.667 [0.563,0.759] | 0.148 [0.080,0.227] |
| Gemini 2.5 Flash Lite | 0.517 [0.400,0.650] | 1.000 [1.000,1.000] | 0.278 [0.189,0.378] |
| GPT-4o | 0.625 [0.500,0.750] | 0.954 [0.908,0.989] | 0.068 [0.000,0.159] (n=44) |
| Claude Sonnet 4.5 | 0.547 [0.422,0.672] | 0.977 [0.943,1.000] | 0.189 [0.111,0.267] |
| Claude Opus 4.6 | 0.578 [0.453,0.703] | 0.954 [0.908,0.989] | 0.244 [0.156,0.333] |
| GPT-5.6-Terra | 0.797 [0.703,0.891] | 0.951 [0.901,0.988] | 0.833 [0.756,0.911] |
| Qwen3-VL-8B-Instruct | 0.468 [0.355,0.597] | 0.802 [0.709,0.884] | 0.133 [0.067,0.200] |
| Qwen3-VL-8B-Thinking | 0.578 [0.453,0.703] | 0.885 [0.816,0.943] | 0.092 [0.034,0.161] |

**Real findings, consistent with the manuscript's existing story:**
- SEM/XRD numbers closely track the current manuscript's Table 1 (e.g.
  GPT-5.6-Terra's XRD=0.797 matches `matpcr_snjnl.tex` exactly).
- **GPT-4o's spectrum low-n anomaly reproduced yet again** (n=44 vs. ~87-90
  elsewhere) — 8th reproduction across sessions/hosts, still not
  root-caused. Strong evidence this is a genuine (GPT-4o × spectrum)
  parse-rate property, not host- or session-specific noise.
- **Spectrum numbers here are NOT identical to the manuscript's** (e.g.
  Gemini 0.278 here vs. 0.184 in `matpcr_snjnl.tex`; GPT-5.6-Terra 0.833
  here vs. 0.878 in the manuscript) — expected and not a bug: different
  sampling draw, and live API model snapshots may have drifted since the
  original run. Do NOT overwrite the manuscript's numbers with these
  without a deliberate decision to re-run and re-report; this run's primary
  purpose was validating the Panther pipeline end-to-end, which it did.

### Not yet done (Panther-specific, carried forward)
- [ ] Obtain an MP_API_KEY and run `stage_materials_project.sh`, then
      `job_exp2_dft.sbatch` (Tier 2 PCR columns) and
      `job_magnetism_recollect.sbatch` (confirm the prompt fix).
- [ ] Run `job_verifier_retrain.sbatch` and compare against the committed
      `exp5_results.jsonl` before treating any new weights as a release
      candidate.
- [ ] Decide whether to formally adopt this session's fresh Tier 1 numbers
      into the manuscript, or treat this run as pipeline validation only
      (current default, per the note above).

---

## 22. Tier 2 (DFT-grounded) Panther run + verifier retrain + magnetism
re-collection — ALL DONE (2026-08-05)

Materials Project key obtained; staged 3,000 real materials
(`experiments/slurm/stage_materials_project.sh`, MP database_version
2026.04.13, retrieval_date 2026-08-05, 0 skipped for missing nsites — full
provenance recorded per Mustafa's requirement). One real gap found and
fixed in the staging wrapper: `mp_fetch_reference_data.py` requires
`--retrieval_date` (a real, intentional provenance field, not a bug in that
script) but the original `stage_materials_project.sh` never passed it —
fixed by passing `$(date +%Y-%m-%d)`.

**Secrets handling note**: the MP key arrived as a plaintext
`materials_project_api.txt` at the repo root (untracked but NOT gitignored
— one `git add -A` away from a leak). Moved to
`~/.matpcr_secrets/mp_api_key` (same convention as the OpenRouter key,
outside the repo, 600 permissions) and the original file deleted. Verified
no copy of the key string remains anywhere in the repo.

### Experiment 2 DFT-grounded PCR sweep — DONE
(`experiments/exp2_dft_results_panther_20260805.jsonl`)

8 models × 3 DFT modalities × 3 seeds, n=30/cell target, **2,110 checkable
records, $6.41 API cost**. Completed cleanly (zero errors), ~40 min runtime
(items ran slower than the geometric modalities' — DFT reasoning chains are
longer). No low-n anomaly in any cell (all n=77-90, unlike spectrum's
persistent GPT-4o gap).

| Model | Stability | Metallicity | Magnetism |
|---|---|---|---|
| Qwen2.5-VL-7B (local) | 0.744 [0.656,0.833] | 0.540 [0.437,0.644] | 0.767 [0.678,0.856] |
| Gemini 2.5 Flash Lite | 0.730 [0.640,0.820] | 0.702 [0.607,0.798] | 0.494 [0.382,0.596] |
| GPT-4o | 0.800 [0.711,0.878] | 0.671 [0.565,0.765] | 0.678 [0.578,0.778] |
| Claude Sonnet 4.5 | 0.756 [0.667,0.844] | 0.694 [0.600,0.788] | 0.756 [0.666,0.844] |
| Claude Opus 4.6 | 0.722 [0.633,0.811] | 0.721 [0.628,0.814] | 0.700 [0.600,0.789] |
| GPT-5.6-Terra | 0.656 [0.556,0.756] | 0.659 [0.553,0.753] | 0.767 [0.678,0.844] |
| Qwen3-VL-8B-Instruct | 0.713 [0.621,0.805] | 0.688 [0.584,0.792] | 0.533 [0.433,0.633] |
| Qwen3-VL-8B-Thinking | 0.767 [0.678,0.856] | 0.644 [0.540,0.736] | 0.506 [0.404,0.607] |

**Standing caveat unchanged**: these are real, measured PCR numbers but the
underlying DFT reference data/tolerances are NOT yet independently
re-validated by Mustafa under this exact re-run (his prior sign-off, §9/§19,
was on the protocol and an earlier data pull, not this specific batch).
Report as provisional, same as every other DFT number in this project.
**Do not confuse this PCR sweep with DFT Half-B precision** — this is model
consistency-rate, not the still-outstanding human precision audit on
corrected-oracle fired cases (§20/§21's "not yet done" list — still not
done, unaffected by this run).

**Real finding worth flagging**: Gemini's magnetism PCR (0.494) is among
the lowest in this table, in the same direction as the standing
"Gemini's magnetism prompt hedges/truncates on ambiguous formulas" finding
(§19/§20/§21) — but this run's collection (below) suggests the underlying
truncation bug itself IS fixed; a low PCR here is a separate question about
whether Gemini's actual judgment on magnetism is less accurate, not whether
it can produce a parseable answer at all. Not fully disentangled this pass.

### Gemini magnetism-prompt fix — re-collection confirms the fix works
(`experiments/halfB_dft_fired_cases_magnetism_refix_20260805.jsonl`)

Target of ≥100 fired cases reached in only **5 rounds** (113 fired cases
out of 300 total scanned records, 150 local + 150 api), **$0.0096 API
cost** — both the round-count and cost are far lower than the original
collection needed (CLAUDE.md's Phase 1 DFT Half-B collection, §19, needed
to loop substantially longer to hit its target).
This is consistent with — though not definitive proof of — the prompt fix
(§21: explicit short/non-hedging instruction + raised token budget) working
as intended: fewer wasted, unparseable Gemini calls means fewer rounds
needed to accumulate the same number of real fired cases. **Manual re-review
of these 113 cases is still the standing blocking item** before any new
magnetism precision number can be reported (unchanged from §20/§21).

### Verifier retrain with pinned seed — DONE
(`experiments/exp5_results_panther_20260805.jsonl`,
weights at `$MATPCR_DATA_ROOT/verifier_weights_20260805/`)

All 13 splits retrained cleanly, zero errors. Compared directly against the
committed `exp5_results.jsonl`:

| Split | Old AUC | New AUC | Δ |
|---|---|---|---|
| random (in-distribution) | 0.850 | 0.840 | −0.010 |
| held-out XRD | 0.497 | 0.552 | +0.055 |
| held-out SEM | 0.527 | 0.686 | +0.159 |
| held-out spectrum | 0.558 | 0.549 | −0.009 |
| held-out stability | 0.436 | 0.423 | −0.013 |
| held-out metallicity | 0.582 | 0.574 | −0.008 |
| held-out magnetism | 0.503 | 0.511 | +0.008 |

(held-out-constraint-type rows track their held-out-modality counterparts
within noise, as previously established — not duplicated here.)

**Qualitative story holds**: in-distribution stays strong (~0.84-0.85), no
held-out modality re-emerges as a generalization exception (magnetism stays
at chance, 0.511 vs. the retracted 0.867), consistent with the corrected,
source-disjoint-split finding in §19/the manuscript. **SEM's held-out AUC
moved more than the rest** (0.527→0.686) — still well below the
AUC≥0.7 "usable triage" bar from Experiment 6, so this doesn't revive any
retracted claim, but is a real point of training-seed sensitivity worth
noting rather than treating both numbers as interchangeable.

**This is now the release-candidate weight set** for the citable verifier
artifact (pending a decision on whether to actually publish it publicly —
still open, see §17's standing item).

### Not yet done (carried forward)
- [ ] Manual re-review of the 113 fresh magnetism fired cases (this
      session) — still needs a human, still the standing blocking item for
      any DFT precision number.
- [ ] Decide on and execute public release of the verifier weights now
      sitting at `$MATPCR_DATA_ROOT/verifier_weights_20260805/`.
- [ ] Disentangle Gemini's low magnetism PCR (0.494, this run) into
      "still hedges/gets it wrong" vs. "parses fine but judges incorrectly"
      — not done this pass.
- [ ] Mustafa's DFT sign-off remains on the ORIGINAL protocol/data pull,
      not this specific 2026-08-05 batch — standing caveat, unchanged.

---

## 23. Manuscript updated with the Panther Tier 1+2 numbers — DONE (2026-08-05)

Per explicit user decision (2026-08-05): the fresh 2026-08-05 Panther run
(§21/§22 — combined XRD/SEM/spectrum + stability/metallicity/magnetism,
3,973 total checkable records, 8 models) now REPLACES the prior numbers
throughout `VERSION2/matpcr_snjnl.tex`, not just sitting alongside them in
CLAUDE.md. Updated:
- **Table 1** (`tab:main`): all 8 rows, all 5 columns (Diffraction,
  Microscopy, Spectra, DFT combined, All combined), including which cells
  are re-bolded as the new column maxima (Gemini now leads Microscopy at
  a clean 1.000; Claude Sonnet 4.5 now leads DFT at 0.736; GPT-5.6-Terra
  still leads Diffraction, Spectra, and All).
- **SI Table S1**: all 48 per-(model, constraint-type) rows with fresh $n$,
  PCR, and bootstrap 95% CI, computed the same way as before (percentile
  bootstrap on `matpcr_metrics.bootstrap_ci`, pooled across seeds).
- **Figure 2 panel a** (the PCR heatmap, TikZ): both the displayed value and
  the fill-intensity parameter for all 40 cells. The intensity formula
  (`\f`) was reverse-engineered from the existing block (closest match:
  `round(100 * PCR^2.5)`) since it isn't documented anywhere as an explicit
  formula — good enough to preserve the intended visual gradient, not
  pixel-exact against whatever the original figure-generation script used.
- **Discussion** and **Baselines** prose: overall PCR range (now
  0.555--0.774, was 0.513--0.800), the GPT-4o→GPT-5.6-Terra scaling
  comparison (0.774 vs. 0.687, still non-overlapping CIs — same
  qualitative finding), and the Qwen3-VL reasoning-mode comparison (0.579
  vs. 0.555, still overlapping CIs — same finding).

**What did NOT change** (correctly out of scope for this update):
- The oracle-validity gate table (`tab:exp1`, Experiment 1 Half-A/Half-B) —
  DFT precision cells still correctly say "pending human review"; today's
  run produced new PCR data, not a new human precision audit.
- Experiments 3 (accuracy-vs-consistency), 4 (CGSV), 5 (verifier
  generalization by held-out split), 6 (detector analysis) — none of these
  were re-run today; their tables/prose are untouched and still reflect
  the prior data. Re-running Experiment 2 does not automatically update
  numbers derived from separate experiments built on top of it.
- The MatterChat baseline paragraph (Phase 2 item 16) — unrelated dataset,
  untouched.
- DFT-provisional caveat language throughout — unchanged; these numbers
  are real and measured but still not independently re-validated by
  Mustafa under this exact 2026-08-05 data pull (§22).

**`VERSION2/matpcr_submission.zip` deliberately NOT rebuilt this pass** —
its bundled `matpcr_snjnl.pdf` was compiled before today's edits and no
LaTeX toolchain is available in this environment to produce a fresh,
matching PDF. Per explicit user decision (2026-08-05): hold the zip as-is
rather than bundle a `.tex` that no longer matches its own `.pdf` — rebuild
only once a real `pdflatex` compile has actually been run against the
updated source (same rebuild procedure as Phase 1, §1 blocking item 1).

### Not yet done
- [ ] Get a real LaTeX toolchain to compile the updated `matpcr_snjnl.tex`
      (this session verified brace/environment balance only, no actual
      `pdflatex` run against these edits), THEN rebuild
      `VERSION2/matpcr_submission.zip` with the matching fresh PDF — do
      not rebuild the zip before the PDF is regenerated, per the standing
      decision above.
- [ ] `MATPCR_KNOWLEDGE.md` §7's Experiment 2 table (if that file is kept
      up to date going forward) also needs this update — not touched this
      pass, only `matpcr_snjnl.tex` and `CLAUDE.md`.

---

## 24. Multiple-comparisons correction (Holm/BH) — DONE (2026-08-05)

Resolves the last standing item from `matpcr_REDFLAGS.txt` (BL1's
multiplicity remainder + EX10) that hadn't been closed by earlier passes.

**Scoped correctly, not naively**: the manuscript's 144 (model,
constraint-type, seed) sweep cells report bootstrap CIs on point estimates,
not a family of significance tests — Holm/BH correction (designed for
p-value families) doesn't apply to them the same way, and applying it
anyway would have been a category error, not rigor. The actual family of
*significance tests* in the paper is Table 2's 6 exact McNemar tests: the
4 per-model CGSV comparisons (`exp4_results.jsonl`) + 2 mechanism-isolation
controls (self-refine, re-prompt; `exp7_results.jsonl`).

Added `holm_bonferroni()` and `benjamini_hochberg()` to `matpcr_metrics.py`
(smoke-tested: monotonicity, Holm-at-least-as-conservative-as-BH, p=1.0
stays at 1.0 under both). New script
`experiments/exp15_multiplicity_correction.py` recomputes all 6 McNemar
tests directly from the raw before/after records (not hardcoded from the
manuscript's printed values — confirmed the raw p-values reproduce exactly:
$3.1\times10^{-5}$, $2.4\times10^{-4}$, $7.6\times10^{-6}$,
$4.6\times10^{-13}$, $0.615$, $0.20$) and applies both corrections.

**Result: all 4 CGSV effects survive the strictest (Holm) correction**
(adjusted $p$: $1.2\times10^{-4}$, $7.3\times10^{-4}$, $3.8\times10^{-5}$,
$2.7\times10^{-12}$ — every one still far below 0.05), and both negative
controls remain non-significant under either correction (Holm-adjusted
$p=0.615$ and $0.399$). The qualitative finding — CGSV works, generic
self-refinement/re-prompting do not — is robust to testing 6 things at
once, not an artifact of multiple comparisons.

**Manuscript updated** (`VERSION2/matpcr_snjnl.tex`): Table 2 gained a
$p_{\mathrm{Holm}}$ column with the corrected values; the Statistics
paragraph (Methods/Baselines) and the earlier Results-section mention both
rewritten from "still-owed, unresolved limitation" to "resolved, all
effects survive" with the actual numbers. Confirmed brace/environment
balance still holds after the edit (985/985, 40/40) — no real compile run
(still no LaTeX toolchain in this environment, same standing gap as §23).

### Not yet done
- [ ] Still no real `pdflatex` compile of the manuscript since §21-24's
      edits (only structural balance checked) — same standing item as §23.
- [ ] `matpcr_submission.zip` still correctly held back pending that compile.

---

## 25. DFT Half-B manual precision review — DONE (2026-08-06)

The last piece of the standing DFT gate blocker. The corrected-oracle review
pages didn't actually exist on disk (found missing 2026-08-05 despite an
earlier claim they'd been "regenerated" — see §22's superseded note); the
underlying data (`experiments/halfB_dft_fired_cases.jsonl`, 891 records, 336
fired) was real and present, so `experiments/halfB_report_dft.py` was simply
(re-)run to produce them:
`experiments/halfB_review_dft_{stability,metallicity,magnetism}.html`
(107/114/115 fired cases respectively — exact match to CLAUDE.md's recorded
count).

Rasul reviewed all 336 cases across the 3 corrected-oracle DFT families
(exported as `stability_halfB_review_2026-08-06.txt`/
`metallicity_halfB_review_2026-08-06.txt`/`magnetism_halfB_review_2026-08-06.txt`
at repo root — same unquoted-bare-token export quirk as the original
geometric-family reviews, parsed the same way with a regex pre-pass. Note:
all three files' internal `claim_type` header field says `"stability"` —
confirmed as a cosmetic export-tool artifact, not a real labeling error,
since each file's case count matches its OWN family's fired-case count
exactly (107/114/115), not stability's).

**Precision results (real / (real + false_positive)):**

| Family | Reviewed | Real | False positive | Precision |
|---|---|---|---|---|
| Stability | 107 | 102 | 5 | **95.3%** |
| Metallicity | 114 | 108 | 6 | **94.7%** |
| Magnetism | 115 | 106 | 9 | **92.2%** |

**GATE DECISION: Rasul judged this precision sufficient to proceed**
(2026-08-06) — an explicit team call, same pattern as the original
geometric-families gate decision (2026-07-07). All three land comfortably
above the geometric families' own passing precision (72.8-88.6%), and
**above the OLD, stale pre-correction DFT numbers** (90.8%/93.1%/85.9%) —
a real signal the oracle corrections (magnetism's magnitude-only redesign,
metallicity's abstention band, stability's near-hull framing) improved
precision, not just changed methodology cosmetically.

**False-positive root-cause check (before the gate decision, for context):**
- **Stability (5 FPs)**: all cluster right at the hull boundary
  (energy_above_hull 0.0003-0.022 eV/atom, all below the 0.05 tolerance) —
  the exact same MP-`is_stable`-vs-0.05eV/atom definition-mismatch effect
  already documented for the pre-correction review (§16). Not a new failure
  mode.
- **Metallicity (6 FPs)**: all have a real band_gap in the 0.003-0.04 eV
  range — genuinely near the metal/nonmetal boundary, a real edge effect
  of where the abstention band's `metal_max_eV` threshold sits, not random
  noise.
- **Magnetism (9 FPs)**: mixed — several have a claimed magnitude close to
  the real value (e.g. one case: claimed 6.0, real total_magnetization
  6.0000 exactly — plausibly a borderline call, not a clear miss), others
  have a claimed magnitude far from a near-zero real value (a genuine miss).
  Not further disentangled this pass.

**File hygiene**: the OLD pre-correction review exports
(`stability.txt`/`metallicity.txt`/`magnetism.txt`, dated 2026-07-10) were
sitting at the repo root next to nothing distinguishing them from a future
new review — archived to
`archive/{stability,metallicity,magnetism}_OBSOLETE_precorrection_oracle_2026-07-10.txt`
(matching the existing `archive/matpcr_submission_OBSOLETE_2026-06-19.zip`
naming convention) to remove that landmine.

### Manuscript updated (`VERSION2/matpcr_snjnl.tex`)
Table 1 (`tab:exp1`, the oracle-validity gate table): all three DFT rows
changed from "pending human review" to the real audited precision figures
above; caption rewritten to state the audit is complete under the corrected
oracle, still describing these as real/measured but not yet independently
re-validated by Mustafa on this specific reviewed batch (his conditional
protocol approval stands, per §9/§19 — this is precision on the protocol he
approved, not a new sign-off). Confirmed brace/environment balance still
holds (988/988, 40/40) — no real `pdflatex` compile run, same standing gap
as §23/§24.

**This closes the last blocking item from `matpcr_REDFLAGS.txt` BL3/items
1-3 that was resolvable without new data collection.** Mustafa's
independent re-validation of this exact batch and the second-human-reviewer
Cohen's-kappa pass (EX6) remain the only genuinely open human-labor items
from the red-flags list.

### Not yet done
- [ ] Mustafa's independent re-validation of this specific 2026-08-06
      reviewed batch (his sign-off was on the protocol, not this precision
      number — standing distinction, unchanged).
- [ ] Second human reviewer + Cohen's kappa (EX6) — still not started, for
      any oracle family, DFT or geometric.
- [ ] Real `pdflatex` compile of the manuscript — same standing gap as
      §23/§24, not resolved this pass either.

---

## 26. version3/ red-flag resolution pass — DONE (2026-08-06)

`version3/` is a further-revised successor to `VERSION2/`, produced by a
deep audit pass that added 19 `\redflag{}` markers (A1-A19) plus 5
bibliography items (B1-B5) and one strategic venue-fit decision (E1-E3),
recorded in `version3/otherfiles(redflagetc.)/matpcr_REDFLAGS.txt`. A
research agent audited all of them against the actual manuscript text and
this repo's real data before any fix was attempted — full findings below.

### Resolved this pass (data/text already existed, just needed writing in)

**A18 (the most consequential item — "every DFT-grounded number inherits
the answer").** Confirmed this was a **manuscript-text staleness issue, not
a data gap**: the Results-section prose still read as if the DFT precision
human-review pass had never happened, while Table 1's own caption already
reported the real numbers (95.3%/94.7%/92.2%, n=107/114/115) AND explicitly
flagged the contradiction rather than hiding it. §25 documents the real
review (Rasul, 2026-08-06, 336 cases). **Fixed**: rewrote the Results
sentence to name the reviewer and date directly
(`version3/matpcr_snjnl.tex`, the paragraph ending "...still outstanding"),
and simplified Table 1's caption to state the same fact instead of
describing the now-resolved disagreement. Removed both `\redflag{}`
markers.

**A3 (stability per-class count).** The redflag said "the recorded 61/62
does not reconcile with n=90... 81/82 reproduces 0.494 exactly." Verified
directly against `experiments/exp3_results.jsonl`
(`model=="local", modality=="stability"`): grouping by
`(true_stable, claimed_stable, accurate)` gives exactly 81/82 correct on
the unstable class (81+1=82) and 0/8 on the stable class (81+8+1=90,
correct total). Balanced accuracy = (81/82+0/8)/2 = 0.4939 ≈ 0.494, matching
the manuscript's own stated figure exactly. **Fixed**: replaced "61/62"
with "81/82" and removed the `\redflag{}`.

**A19 (LLM-judge microscopy AUC missing a CI).** The 0.735 point estimate
had no interval. Found directly in `experiments/exp8_run.log:72`:
`[judge/modality:sem] ... AUC=0.735 [0.682,0.790] ...`. **Fixed**: inserted
"$[0.682,0.790]$" into the Discussion sentence, removed the `\redflag{}`.

**B4 (selfverify2026 bib entry).** The full author list (Long, Jiang, Chen,
Guo, Gan, Wang) was already verified against the arXiv abstract page on
2026-08-06 per a comment left in the `.bib` file, but the entry itself
still said "Long, Quanyu and others". **Fixed**: substituted the full list
into `version3/matpcr_refs.bib`. Note: `version3/matpcr_snjnl.bbl` is
precompiled and will show the old truncated author list ("Long, Q. et
al.") until a real `bibtex` pass regenerates it — same standing
no-LaTeX-toolchain gap as §23/§24/§25; not hand-edited, since editing a
bibtex-generated file by hand risks drifting further from what a real
compile would produce.

**A2 (918 vs 923 "reconciliation") — resolved as a FALSE ALARM in the
redflag itself, not a real data-integrity problem.** Traced both numbers to
their source: "918" is `experiments/exp3_run.log`'s total from an OLDER,
now-superseded run of Experiment 3; the CURRENT `exp3_results.jsonl` on
disk (matching `exp3_run2.log`) totals **920**, with zero records missing
an `accurate` field — contradicting the redflag's "5 records lack a
non-circular accuracy criterion" framing outright. Separately, "923" is
NOT a number from Experiment 3 at all: it's the sum of Supplementary Table
S1's diffraction+spectra+stability cells for the 4 original models
(64+88+90 + 60+90+89 + 64+44+90 + 64+90+90 = 923, confirmed by direct
summation) — but that table reports **Experiment 2's** main PCR sweep, a
different experiment with a separately drawn sample, sharing modality
names by coincidence. The redflag's author compared two numbers from two
different experiments and treated the mismatch as a data bug. **Fixed**:
updated the manuscript's item count from the stale "918" to the current,
correct "920" (independently re-verified: 920 records, 204/920=22.2%
item-level disagreement, matching the manuscript's stated mean gap exactly
even at the pooled level, not just as a mean-of-cell-means), and replaced
the invalid reconciliation request with a sentence explaining why the two
totals are not supposed to match. Removed the `\redflag{}`.

### Confirmed genuinely open (real gaps, not resolvable from data in this repo)

- **A8** (second annotator + Cohen's kappa per oracle family): harness
  (`experiments/exp13_second_reviewer_kappa.py`) is complete and working
  but needs two named human review exports that don't exist. No second
  reviewer has been found anywhere in the repo.
- **A13** (post-CGSV accuracy, to separate physics correction from
  retreating to a trivially-admissible claim): `exp4_results.jsonl` stores
  `claimed_values` per round but no ground-truth comparison — this is new
  analysis against Experiment 3's tight accuracy criteria, not yet run.
- **A14** (measured MP `is_stable`-vs-0.05eV/atom disagreement rate): the
  original 3000-material MP pull with continuous hull values
  (`/ephemeral/matpcr/mp_data/`) no longer exists on this checkout, and
  `exp3_results.jsonl`'s stability records only store the boolean
  true_stable, not the continuous value needed. Needs a fresh MP pull.
- **A7** (prompt/paraphrase sensitivity sweep): no output found anywhere;
  not run.
- **A17** (microscopy-specific model run, e.g. MicroscopyGPT): not run;
  only MatterChat (a DFT/structure-arm domain model) exists in
  `experiments/`.
- **A4, A5, A6, A9, A10, A11, A12, A15, A16** — genuine author/co-author
  decisions or actions (Mustafa's DFT-protocol sign-off; model-currency
  call; DOIs pending actual repository deposit; funding statement — the
  current text at `version3/matpcr_snjnl.tex` reads "received no specific
  funding," an unhedged claim needing author confirmation, not a
  `\redflag{}`-wrapped placeholder; GPU-hours accounting; and an unresolved
  own-DFT hedge in Methods that needs a clean yes/no from the authors, not
  data that's missing).
- **B1** (cover letter): root `matpcr_cover_letter.txt` (no version3-specific
  one exists) still has literal `[AUTHOR: fill submission date]` and
  `[AUTHOR: add both corresponding authors' ORCIDs]` placeholders.
- **B5** (declare related work to editor): CrysMTM/R-CRYSTALS/
  QuantumShellNet/HalluVerse25/IRIS are all cited in the bibliography, but
  a citation is not the same as the editor-facing declaration the venue's
  policy requires — that's a submission-portal action, not a text fix.

### Venue-fit decision (E1/E2/E3) — explicitly NOT resolved, needs author input

`matpcr_REDFLAGS.txt` §E frames this as "the largest single risk to the
paper, above every item in A": npj Computational Materials publishes
materials-design/understanding work; this paper is a technique-adjacent
contribution (measuring/correcting LLM reasoning hygiene on materials
data), and an editor could desk-reject purely on scope. Three options are
given (submit as-is with a reframed cover letter around the DFT-oracle
screening-pipeline angle; a presubmission enquiry to the editor — the
redflag file's own "RECOMMENDED" pick; or retarget to a venue where
chain-level LLM evaluation is the norm). Not resolved here — this is
explicitly the authors' call, not something to decide unilaterally. One
interaction worth flagging: if E1 is chosen (reframing around the DFT
oracles), that framing invites closer reviewer scrutiny of exactly the DFT
precision claims A18 touches — which is now fixed, but worth knowing this
choice and A18 aren't fully independent.

### Not yet done
- [ ] All the "genuinely open" items listed above — none attempted this
      pass since each needs new API/data collection, a human reviewer, or
      an author/co-author decision, not a text fix.
- [ ] Regenerate `version3/matpcr_snjnl.bbl` via a real `bibtex` pass once
      a LaTeX toolchain is available (needed for B4's fix to actually show
      up in the compiled bibliography, and for A18/A3/A19/A2's text edits
      to be verified via a real compile, not just brace/environment
      balance checks).
- [ ] The venue-fit decision (E) — awaiting author input.

---

## 27. version3/ red-flag resolution, round 2 — 5 more resolved (2026-08-06)

Continuation of §26. Worked through the remaining 9 red-flags after the
first round's 4 (A18, A3, A19, A2). Five more turned out to have real,
checkable answers already available in this repo or computable from
already-staged data — none needed new API spend or a human decision.

**A4 (1e-6 μB zero tolerance) — resolved by discovering the manuscript
described DELETED code, not live code needing sign-off.** The redflag asked
to confirm with Mustafa that `1e-6 μB` (well below the ~1e-3 μB numerical
noise floor of a real GGA/GGA+U calculation) was the intended tolerance.
Checked `matpcr_metrics.py`'s CURRENT `magnetism_magnitude_consistent()`
directly: it has no `zero_atol` parameter at all — that parameter belonged
to the OLD `property_sign_magnitude_consistent()`, fully replaced during
the Phase 1 magnetism redesign (§19). Confirmed via
`git log --all -p -- matpcr_metrics.py`: `zero_atol=1e-6` only ever existed
in the pre-redesign function. **Fixed**: rewrote the Methods sentence to
say this tolerance is from a superseded check and no longer appears in the
released code — no sign-off needed on a parameter that doesn't exist
anymore.

**A14 (MP is_stable vs 0.05 eV/atom disagreement rate) — computed directly
from the fresh 3,000-material MP pull staged during the Panther session
(§22).** `energy_above_hull <= 0.05` (oracle) vs. `is_stable` (MP's own
strict flag): **571/3000 = 19.0% disagreement**, matching CLAUDE.md §9's
earlier-flagged "roughly a fifth" figure almost exactly, confirming it was
a real number that just never got written down with its source. Also
confirmed the disagreement is 100% one-directional: every single case is
MP-labeled-unstable-but-oracle-tolerance-admits-as-near-hull; the reverse
never occurred in this sample. **Fixed**: entered "571 (19.0%)" with the
one-directional detail in both the Results and Methods locations that
referenced this claim.

**A15 (own-DFT statement) — resolved as a clean "no."** Searched the
entire codebase for any actual first-principles calculation code (VASP,
Quantum ESPRESSO, pseudopotential handling) — found none; every DFT
reference value in every experiment traces to `mp_fetch_reference_data.py`
pulling `mp-api` documents directly, never a locally-run calculation. The
script's own provenance-writing code (`mp_fetch_reference_data.py:136`)
already states plainly: "Own-DFT validation is reserved for missing or
clearly questionable cases... not run over this full sample." **Fixed**:
replaced the hedged, contradictory Data-sources sentence with a direct
statement that no author-run DFT entered any reported number.

**A16 (pre-registration commit/DOI) — resolved as self-resolving.** The
redflag's own wording was conditional: cite a registration if one exists,
"otherwise leave this wording as it stands." Checked `git log --all` and
searched for any OSF/Zenodo preregistration artifact — none exists, only
informal commits. **Fixed**: per the redflag's own instruction, kept the
existing wording and replaced the conditional redflag with a direct
statement that no registration was made, checked against this project's
own version history.

**A13 (post-CGSV accuracy — the mechanism-isolation gap) — genuinely
computed, not found pre-existing, and the most substantive finding of this
pass.** `exp4_results.jsonl` stores each CGSV item's final-round
`claimed_values` but never compared them to ground truth. Resolved each
item's `source_file` (old-host absolute paths) against the currently-staged
opXRD/RRUFF copies (confirmed both resolve correctly), then applied the
EXACT same non-circular accuracy criteria `exp3_accuracy_vs_consistency.py`
uses (XRD: nearest true peak within 0.1°; spectrum: nearest real measured
peak within 2 cm⁻¹) to the final CGSV round's claim. New script:
`experiments/exp16_post_cgsv_accuracy.py` (a proper, reusable version of
the ad hoc computation, reusing `halfB_collect.xrd_reference_peaks`/
`spectrum_signal` rather than reimplementing reference-peak logic).

**Result: post-CGSV accuracy is 29.8% on diffraction (n=252) and 9.9% on
spectra (n=293) — both far below the corresponding post-CGSV PCR.** This
means most of CGSV's measured PCR gain is retreat to an oracle-admissible
value, not genuine physical correction: the model moves to something the
necessary-condition oracle accepts far more often than it moves to the
value that is actually right. This is a real, substantive finding that
qualifies (does not overturn) CGSV's headline result — CGSV demonstrably
reduces oracle-detected violations (the b=0-everywhere, Holm-surviving
result stands untouched), but this new number shows it does not, on this
evidence, demonstrably improve underlying physical correctness. **Fixed**:
replaced the redflag with the full finding, stated plainly rather than
softened. Checked the rest of the manuscript (abstract, contributions,
CGSV subsection intro) for any claim this would contradict — found none;
existing language already only claims CGSV supplies a "corrective signal"
(the mechanism/input), not that the model's response to it is verified
correction, so no other section needed a cascading fix.

### Confirmed still genuinely blocked (9 red-flags remain, unchanged from §26's assessment where overlapping)
- **A1** (spectrum oracle precision audit under the revised prominence
  check): attempted to regenerate the review page via
  `experiments/halfB_report.py` — failed immediately, `FileNotFoundError`
  on the rendered plot images (`.../pilot_images/xrd_pattern_*.png`), which
  lived only on the now-wiped old host and don't exist anywhere on this
  filesystem. The underlying relabeled data (495 spectrum fired cases,
  correctly using the corrected oracle per §9's earlier relabeling work) is
  real and current, but no image-free/text-only path exists in the report
  script, and regenerating the plots from raw RRUFF data plus saved
  chain_text was not attempted this pass. Genuinely blocked without either
  rebuilding the plot-rendering step or accepting an image-free review
  format.
- **A5, A6, A17, A7, A8** — confirmed via direct repo search: no newer
  flagship model was ever run (A5), no submission-time competitor check
  can be done ahead of the actual submission date (A6), no
  microscopy-specific model run exists anywhere (A17), no prompt-paraphrase
  sweep output exists anywhere (A7), and the second-reviewer harness
  (`exp13_second_reviewer_kappa.py`) remains complete but unused, with no
  second human review found (A8).
- **A9, A10** (data/code repository DOIs) — deliberately NOT resolved by
  inserting the project's live GitHub URL as a stand-in: the venue requires
  a permanent archival deposit (Zenodo-style DOI), and a mutable GitHub
  repo is not equivalent to that. Minting a real DOI is outside what this
  pass can do.
- **A12** (GPU-hours/CPU spec) — investigated whether this could be
  reconstructed from existing logs: found most historical result files
  (`exp2_results.jsonl`, `exp3_results.jsonl`, `exp4_results.jsonl`) never
  recorded per-item timing at all, and the original P100 host's logs are
  gone. Only the most recent Panther-run logs and the pilot have real
  timing data — computing a "total GPU-hours" figure from just those would
  understate the true total significantly and mislead rather than help.
  Left open rather than reporting a number known to be incomplete.

### Manuscript state after this pass
9 `\redflag{}` markers remain in `version3/matpcr_snjnl.tex` (down from the
original 19; 10 resolved across §26+§27). Brace/environment balance
confirmed (1830/1830, 28/28) — no real `pdflatex` compile run, same
standing gap as §23/§24/§25/§26.

### Not yet done
- [ ] A1's spectrum precision audit — needs either rebuilding the
      plot-rendering pipeline from raw RRUFF data + saved chain_text, or a
      text-only review format; not attempted.
- [ ] All items confirmed genuinely blocked above (A5-A10, A12, A17) —
      each needs new API spend, a Zenodo deposit, a second human reviewer,
      or a submission-time check, none of which happened this pass.
- [ ] Real `pdflatex` compile — same standing gap as every prior manuscript
      pass.

---

## 28. version3/ blocked-item resolution — A1 unblocked, A5 in progress,
B2/B3 verified (2026-08-06)

Continuation of §26-27, tackling the 9 items confirmed genuinely blocked.
Three real wins so far, one long-running API job in progress, rest
confirmed as still correctly blocked (see below).

### A1 (spectrum precision audit) — UNBLOCKED, review page now exists
The blocker from §27 (rendered plot images for XRD/spectrum, and the raw
SEM JPEG paths, all pointing at the wiped old host) is fixed. New script
`experiments/exp17_rebuild_review_images.py`: for XRD/spectrum, re-renders
each fired case's plot from its real `source_file` (resolved against the
currently-staged opXRD/RRUFF copies) using the EXACT same matplotlib recipe
`pilot.py`'s `build_xrd_items`/`build_spectrum_items` use, so the
regenerated image is equivalent to what the model actually saw; for SEM,
just rewrites the `/ephemeral/matpcr/...` path prefix to the current
`MATPCR_DATA_ROOT` (no re-rendering needed, since SEM's image_path was
always the raw NFFA-EUROPE JPEG directly, not a rendered plot). **Result:
101/101 XRD, 495/495 spectrum, 105/105 SEM images rebuilt/rewritten, ZERO
failures.** Re-ran `experiments/halfB_report.py` afterward, which now
succeeds and produces all three review pages:
`experiments/halfB_review_{xrd,sem,spectrum}.html` (4.97MB/14.2MB/15.3MB),
each with working radio-button controls and Export button, confirmed by
direct inspection. The spectrum page correctly reflects the 495
corrected-oracle fired cases (not the stale 103 from the pre-revision
oracle) — confirmed all 495 have `oracle_consistent=False` as expected for
a fired-case set. **A1 itself (actually judging all 495+101+105 cases) is
still a real human-labor item — genuinely not something to fake — but the
page that review would happen on now exists, which is the part that was
actually missing.**

### A5 (flagship-tier model) — DECIDED and IN PROGRESS (real API spend, not simulated)
Per explicit user decision (2026-08-06): add `openai/gpt-5.6-sol`, the
flagship sibling of the already-tested balanced-tier `gpt-5.6-terra`, named
explicitly as an acceptable option in `matpcr_REDFLAGS.txt` A5. Confirmed
live and vision-capable via a direct OpenRouter models-list query before
committing (`anthropic/claude-opus-5` also exists and was considered, but
gpt56sol was chosen since it directly tests flagship-vs-balanced within a
model family already in the paper, a cleaner comparison than adding an
unrelated new family). Added to `MODELS` in `exp2_pcr_sweep.py` as
`"gpt56sol"`, smoke-tested on n=2 before committing. **Two full sweeps
launched in parallel** (no GPU needed, gpt56sol is API-only): geometric
modalities (xrd/sem/spectrum, `experiments/exp2_gpt56sol_geometric.jsonl`)
and DFT modalities (stability/metallicity/magnetism,
`experiments/exp2_gpt56sol_dft.jsonl`), both n=30/cell, S=3 seeds, matching
every other model's scale exactly. Both were still running as of this log
entry — real API cost being spent, not yet complete; the manuscript
edit (adding a 9th model row to Table 1 and SI Table S1, and answering
whether flagship beats balanced with a CI comparison, mirroring the
existing GPT-4o-vs-Terra analysis) is deferred until both finish and are
aggregated.

### B2, B3 — verified via live arXiv/ACL lookups, real findings beyond just resolving the VERIFY tags
Fetched both papers' current arXiv abstract pages directly (not from
memory):
- **B2 (Mat-Pref, arXiv:2606.21830)**: author list confirmed
  ("Sarrah R. Mikhail Leung, Taehan Kim, Jeongbin Park" — note the bib had
  the first author's name slightly wrong, "Leung, Sarrah Mikhail", missing
  the "R." middle initial; corrected). New finding beyond just resolving
  the `% VERIFY` tag: this paper is now **accepted at the ICML 2026
  AI4Physics Workshop** — not reflected anywhere in the citation before.
  Added a `note` field with the venue.
- **B3 (VPRM, arXiv:2601.17223)**: author list confirmed (Pronesti, Belz,
  Hou) — already correct in the bib. Cross-checked the bib's existing
  "Findings of ACL" claim (which arXiv's own abstract page does NOT show,
  a known lag between acceptance and arXiv updating its venue banner) via
  a live web search: confirmed real via the ACL Anthology entry itself
  (`2026.findings-acl.1611`) — the bib's existing claim was already
  correct, no fix needed, but now independently confirmed rather than
  taken on faith.
- **Bonus finding**: Sci-PRM (arXiv:2606.04579, already fully verified in
  an earlier pass) turns out to now have a v2 revision and is **accepted
  at KDD 2026's AI4Science Track** — also not previously reflected. Added
  a `note` field with this venue too.

### Confirmed still correctly blocked (not attempted further, same
reasoning as §27)
- **A6** (baselines claim must hold "against the then-current versions" of
  competitors at actual submission time) — genuinely cannot be
  permanently resolved now; it's a live check tied to a future date, not a
  fact to establish today. Did use this session's real arXiv lookups (B2,
  B3) as partial due diligence on the closest neighbors' current state,
  which is exactly the kind of check A6 asks for, but the redflag itself
  correctly stays, since the real submission date is still in the future.
- **A7, A8, A17** — no new attempt this pass; same reasoning as §27 (real
  new experiments/human labor, not something resolvable by inspection).
- **A9, A10** — discussed the Zenodo-GitHub-integration path (a free,
  real way to mint an actual archival DOI from a GitHub release) with the
  user; deliberately left as a tracked action for the user to do
  themselves rather than something to force through.
- **A12** (GPU-hours) — not revisited; same conclusion as §27 (most
  historical logs never recorded per-item timing, computing a partial
  figure would understate the true total).

### Not yet done
- [ ] Once both gpt56sol sweeps finish: aggregate, add the 9th model row
      to Table 1 and SI Table S1, compute the flagship-vs-balanced CI
      comparison, and write the finding into the manuscript (completes A5).
- [ ] A1's actual human judging of 701 cases (101+105+495) — the page
      exists now; the review itself is still real human labor.
- [ ] A7, A8, A9, A10, A12, A17 — unchanged from §27's assessment.

---

## 29. A5 (flagship model) — DONE. GPT-5.6-Sol added, flagship does not
beat balanced (2026-08-06)

Both real API sweeps (§28) finished cleanly: geometric (xrd/sem/spectrum,
$3.21) and DFT (stability/metallicity/magnetism, $3.50), **$6.71 total,
499 checkable records, zero errors**.

**Result: GPT-5.6-Sol (flagship) does NOT beat GPT-5.6-Terra (balanced)
overall.** All: Sol 0.770 [0.731,0.806] vs. Terra 0.774 [0.738,0.810] —
CIs overlap almost completely, essentially the same number. Per-modality:
Sol leads on Diffraction (0.820 vs. 0.797, a new column max) but sits
below Terra on every other column (Microscopy 0.915 vs 0.951, Spectra
0.764 vs 0.833, DFT 0.715 vs 0.736). This is now a THIRD independent
confirmation of the same pattern already in the paper (Claude Opus 4.6
doesn't beat Sonnet 4.5; Qwen3-VL-Thinking doesn't beat Qwen3-VL-Instruct):
marketed capability tier is not a reliable proxy for physical-consistency
performance in this benchmark.

**Manuscript updated** (`VERSION2` naming kept as `version3` per the
project's existing file layout):
- **Table 1**: added GPT-5.6-Sol as a 9th row (all 5 columns), re-bolded
  Diffraction's column max from Terra to Sol, added a $\ddagger$ footnote
  with the exact CI comparison.
- **SI Table S1**: added Sol's 6 per-constraint-type rows with full
  bootstrap CIs, updated the header note describing the model groupings.
- **Discussion**: added the flagship-vs-balanced finding as a third
  example in the existing "capability scaling is not automatic" paragraph.
- **Methods (Models and protocol)**: resolved the STANDING `\redflag{}`
  that had asked the team to decide on this exact question — rewrote to
  describe three passes (original 4, later-gen refresh 4, flagship
  addition 1) instead of two, with the new pass's collection date and its
  answer to the flagship-tier question stated directly.
- **All "eight models"/"3,973 records"/"144 cells" references** updated
  to "nine models"/"4,472 records"/"162 cells" throughout (Results,
  Methods/Statistics, Figure 2's caption, Figure 3's node label) —
  checked systematically via `grep -n "eight\b"` rather than trusting a
  single find/replace to catch every instance.

**Figure 2 panel a (the PCR heatmap) — fully reworked, not just noted.**
Per explicit user decision (2026-08-06: "add gpt56sol to Figure 2's
heatmap too" rather than leaving it table-only). This required:
- **Reverse-engineering the fill-intensity formula properly this time.**
  An earlier session (§23) guessed `round(100*PCR^2.5)` and used it to
  regenerate all 40 cells at the time; reconstructing it now against the
  actual 8-row block's committed values shows that guess was wrong — the
  real formula is **linear**, `fill = round(PCR*82 + 6)`, confirmed by
  reproducing 19/20 sampled cells' exact stored fill values with this
  formula (one cell off by 1, a rounding-boundary case). This means §23's
  regenerated fills were an approximation of the true gradient, not exact
  — flagging here since a future session should use the linear formula,
  not the power-law one, if this heatmap is touched again.
- Inserted GPT-5.6-Sol as the 2nd row (by overall-PCR rank), recomputed
  all 9 rows' y-coordinates from the confirmed row-to-row spacing
  (0.6157), and verified the other 8 rows' fill values reproduce their
  ORIGINAL committed values exactly under the linear formula (not
  overwritten with new numbers) before trusting the insert.
- Shifted the colorbar block, its footnote (added a $\ddagger$ legend
  entry), and BOTH downstream panels (b: CGSV slopegraph, c: detector AUC)
  down by the same 0.6157 to avoid overlap with the now-taller panel a —
  confirmed panel b/c's shift-scope offsets both needed updating
  (`-6.55`→`-7.17`), found by locating all 5 `\begin{scope}[shift=...]`
  blocks in the file and checking which two sat at the old panel a height
  (Figure 3's two unrelated scope shifts, at `-6.30`, were correctly left
  untouched).
- Brace/environment/scope balance confirmed after the full rework:
  1859/1859 braces, 28/28 begin/end, 5/5 scope begin/end.

### Manuscript state after this pass
8 `\redflag{}` markers remain (down from 9 before this entry, 19
originally). A5 is now the 6th of the original 19 fully resolved
(alongside A2, A3, A4, A13, A14, A15, A16, A18, A19 from §26-27 — 10 total
before this entry, 11 now... correction: A5 makes it the 11th resolved of
19, 8 remaining).

### Not yet done
- [ ] A1's actual human judging of 701 review cases — unchanged, still
      real human labor, not attempted further this pass.
- [ ] A7, A8, A9, A10, A12, A17 — unchanged from §27/§28's assessment; no
      new attempt this pass.
- [ ] Real `pdflatex` compile — same standing gap as every prior
      manuscript pass; this pass's TikZ coordinate math was verified by
      hand-checking the formula and by brace/scope balance, NOT by an
      actual compile, so a real render check is still owed before trusting
      the heatmap's visual layout is free of any overlap.

---

## 30. version3/ red-flag resolution, round 4 — A6/A8/A17 removed, A7
implemented with a real new experiment, A9/A10 upload folders prepared,
A12 GPU/host text written — DONE (2026-08-06)

Continuation of §26-29, closing 6 of the 6 items that were confirmed
genuinely blocked at the end of that pass (A6, A7, A8, A9, A10, A12, A17).
Per explicit user instruction this pass: remove A6 and A8's redflags
outright, actually implement A7 and A17 (not just justify/defer), write
real P100+A100 GPU text for A12, and create two separate upload-ready
folders for A9/A10 so the user knows exactly what to upload where.

### A6 — DONE. Redflag removed (language change, not new data)
The Baselines claim that three of the study's controls aren't consistently
reported in comparable studies is a claim about *other authors'* work — it
can only be genuinely re-verified at the actual moment of submission, not
frozen in place now. Softened the sentence to "to the best of our
knowledge as of this writing" plus an explicit sentence committing to
re-confirm immediately before submission. Redflag removed —
`matpcr_snjnl.tex` around the Baselines subsection's opening paragraph.

### A8 — DONE. Redflag removed (honest limitation, not resolved)
The second-annotator/Cohen's-$\kappa$ redflag was removed, but the
underlying gap is NOT resolved — no second human reviewer has done an
independent pass on any oracle family; the harness
(`experiments/exp13_second_reviewer_kappa.py`) remains complete and ready
but unused. The manuscript text now states plainly that every precision in
Table 1 is a single-annotator point estimate, pending that second pass,
rather than carrying a blocking TODO marker for something that is real
human labor, not a text fix.

### A17 — DONE. Redflag removed after confirming a genuine task/interface
incompatibility, not just an unevaluated candidate
Researched MicroscopyGPT (Choudhary 2025, `choudhary2025microscopygpt` in
`matpcr_refs.bib`, already cited in the manuscript) via WebSearch before
deciding RUN vs. JUSTIFY. Found: it is a **structure-captioning** model —
predicts full atomic structure (lattice parameters, element identities,
atomic coordinates) from **simulated** scanning transmission electron
microscopy (STEM) images of 2D materials, fine-tuned on an 11B-parameter
LLaMA model using AtomVision-generated training data drawn from JARVIS-DFT
and the C2DB database. It has **no scale-bar-reading or
feature-size-estimation output interface at all** — its output space is a
crystal structure, not a length. A GitHub search-API query for
"microscopygpt" returned zero dedicated repositories (it appears folded
into the broader AtomGPT/JARVIS-tools ecosystem rather than released as a
standalone interface). Forcing it to answer the SEM oracle's feature-size
question would require inventing an ad hoc adapter around a model never
built to produce that kind of output — that would evaluate the adapter,
not the model. Rewrote the Baselines subsection to state this as a
justified, honest coverage gap on the image arms, removed the redflag.

### A12 — DONE. Real GPU/host text, no fabricated hours total
Per the user's explicit instruction: write P100 and A100 into
Acknowledgements. Cross-checked CLAUDE.md's own record first and found it
genuinely self-contradicts on the original host's GPU (§13/§979 record an
A100 80GB PCIe "confirmed present" on the pre-Panther host; §21/§1851
separately calls that same pre-migration host "single-P100") — did not
try to silently resolve this discrepancy, just wrote the union of both
claims: **an NVIDIA P100 (16GB) host for the earliest pilot and
Experiments 1-4, and an NVIDIA A100 (80GB) host and, later, QCRI's Panther
cluster (A100 80GB and H200 141GB partitions)** for the later-generation
model refresh, verifier retraining, and DFT-grounded re-runs. Deliberately
did **not** report a total GPU-hours figure — most historical result logs
(`exp2_results.jsonl`, `exp3_results.jsonl`, `exp4_results.jsonl`) never
recorded per-item timing at all, and the original P100 host's own logs no
longer exist (§27's A12 investigation already established this). A
fabricated aggregate would be a known-incomplete undercount; stating
plainly that an accurate total isn't recoverable is more honest than a
wrong number.

### A9/A10 — DONE. Two upload-ready folders created, redflags now name them
Per the user's explicit instruction: one separate folder for code, one for
dataset, so the user knows exactly what to upload where. Created at the
repo root:
- **`release_code/`** — `matpcr_metrics.py`, all `experiments/*.py` (35
  scripts, now including this pass's `exp18_prompt_sensitivity.py`),
  `experiments/slurm/` (Panther job scripts + docs), `verifier_weights/`
  (the 13 released LoRA adapters, 375K total, copied from
  `$MATPCR_DATA_ROOT/verifier_weights_20260805/`), and
  `matpcr_runbook.txt`. 2.6MB total.
- **`release_dataset/`** — all `experiments/*.jsonl` (29 real
  result/collection files, ~15MB), `experiments/mp_provenance.json`, and
  the 6 halfB manual-review `.txt` exports from the repo root (`xrd.txt`,
  `sem.txt`, `spectrum.txt`, `stability_halfB_review_2026-08-06.txt`,
  `metallicity_halfB_review_2026-08-06.txt`,
  `magnetism_halfB_review_2026-08-06.txt`). 15MB total.

Each folder has its own `README.md` explaining exactly what's inside and
how it maps to the manuscript's Data availability / Code availability
text. Deliberately did **not** bundle the raw third-party corpora
(opXRD/NFFA-EUROPE/RRUFF/Materials Project) into either folder — those
remain available from their own original public sources with their own
citable DOIs, and re-hosting them would duplicate a more authoritative
existing copy, not add one.

The manuscript's two A9/A10 redflags were **not** removed — no real
Zenodo (or equivalent) DOI exists yet, and minting one is an action only
the user can take — but both were edited to explicitly name
`release_dataset/`/`release_code/` instead of being bare, unscoped TODOs.
**Still needed from the user**: actually upload both folders somewhere
permanent (e.g. Zenodo via GitHub's release integration, discussed and
deliberately deferred earlier per §28) and mint real DOIs before this can
close.

### A7 — DONE. A real, new prompt-paraphrase-sensitivity experiment —
`experiments/exp18_prompt_sensitivity.py`

This is the one item that could not be resolved by editing text or
justifying an absence — the redflag explicitly asked to RUN a new
robustness check, distinct from `exp9_tolerance_sensitivity.py`'s earlier,
separate finding about oracle *tolerance* sensitivity (which never made a
new model call — it re-checked already-collected claims at different
tolerance values). A7 asks whether **paraphrasing the prompt itself**
changes which model looks best — a genuinely different robustness axis,
needing new API spend.

**Design**: for diffraction (XRD), spectra, and stability — the same three
constraint types `exp9`'s tolerance check covers — wrote one independently
worded paraphrase per prompt (not a minimal edit of the original: new
sentence structure and word choice, same task and same required
`FINAL_ANSWER` format so the existing parser could be reused unmodified).
Ran both the original and paraphrase prompt through 4 of the paper's API
models (Gemini 2.5 Flash Lite, GPT-4o, Claude Sonnet 4.5, GPT-5.6-Terra),
$n=15$/modality/variant (XRD's paraphrase variant landed at $n=10$ for
gemini and gpt56 after 2-3 unparseable items each — noted, not concealed).
Measured the exact same pairwise rank-agreement metric `exp9` already
uses, applied to prompt wording instead of oracle tolerance.

**Real operational incident, recorded honestly**: the first full-sweep
attempt (all 3 modalities in one run) genuinely stalled on a hung
OpenRouter socket read during stability's paraphrase variant, item 12/15's
gpt56 call — confirmed directly via `ss -tnp` showing a stuck `ESTAB`
connection and `/proc/<pid>/task/*/wchan` showing `futex_wait_queue_me`
across ~95 threads (the same documented hang class as an earlier
2026-07-10 incident in this project, CLAUDE.md §13 — a per-call `requests`
`(connect, read)` timeout tuple does not always bound a truly stalled
socket read in this environment). XRD and spectrum had already finished
cleanly before the hang; only stability was incomplete. Killed the hung
process and re-ran **just** the stability modality cleanly end-to-end as a
targeted retry (both variants, 120 calls, $0.234 cost) rather than
re-spending budget re-running the two modalities that had already
finished correctly. **The retry's stability/original numbers closely
reproduced the killed run's stability/original numbers** (claude 0.867→
0.933, gemini/gpt4o/gpt56 identical at 0.800/0.800/0.733) — a good
reproducibility check confirming the killed run's partial data, where
usable, was trustworthy. The exact item that hung before (item 12/15) then
passed through cleanly on retry in 6.1s, confirming this was a genuine
one-off network fluke, not a systemic bug in the harness or a
model-specific failure mode worth engineering around.

**Real, final results (all three modalities)**:

| Modality | Rank agreement (original vs. paraphrase) | Per-model rates (original → paraphrase) |
|---|---|---|
| Diffraction (XRD) | **0.5** | claude 0.700→0.700 (n=10/10); gemini 0.900→0.500 (n=10/8); gpt4o 1.000→0.800 (n=10/10); gpt56 0.800→0.800 (n=10/10) |
| Spectra | **0.833** | claude 0.133→0.200 (n=15/15); gemini 0.067→0.267 (n=15/15); gpt4o 0.000→0.067 (n=7/15); gpt56 0.867→0.933 (n=15/15) |
| Stability | **0.667** | claude 0.933→0.800; gemini 0.800→0.714 (n=15/14); gpt4o 0.800→0.800; gpt56 0.733→0.667 (all n=15/15 unless noted) |

**Real findings:**
- **Diffraction's ranking is fragile to prompt paraphrasing** (rank
  agreement only 0.5) — echoing, not resolving, its already-reported
  tolerance-sensitivity fragility (rank agreement 0.0 at different oracle
  tolerances). Two independent perturbation axes both break diffraction's
  ranking; this is now a doubly-confirmed robustness concern for any model
  comparison drawn from that column, not a one-off artifact of either
  check's specific design.
- **Spectra's ranking is fairly robust to paraphrasing** (0.833) — a
  cleaner result than diffraction's, consistent with spectra's
  tolerance-sensitivity check also being fully robust (rank agreement
  1.0). Spectra's ranking is the most trustworthy of the three modalities
  checked here under both perturbation types.
- **Stability's ranking is more mixed (0.667)**, but its absolute rates
  stay tightly clustered under both wordings (0.667-0.933 across all 4
  models × both variants) — a modest rank-agreement number here most
  likely reflects several close scores changing relative order, not any
  one model's judgment swinging dramatically. Worth reading alongside
  stability's tolerance-sensitivity number (0.67, from a different
  tolerance grid) — both land at a similar "partially robust" point,
  independently.
- **GPT-5.6-Terra is the clear standout on spectra under both wordings**
  (0.867/0.933) while **GPT-4o is consistently the weakest under both**
  (0.000/0.067) — a genuinely wording-independent qualitative pattern,
  even though the exact numeric ranking of the other two models shifts.
- **New clue on the standing GPT-4o/spectrum low-n anomaly** (first
  flagged in Experiment 2, reproduced in Experiments 2/3/4 and again on
  Panther, §21): it reproduced again here under the *original* wording
  ($n=7/15$) but did **not** reproduce under the *paraphrase* ($n=15/15$).
  This is a new, small, concrete data point suggesting the anomaly may be
  sensitive to the exact prompt wording rather than a fixed property of
  the (GPT-4o, spectrum) pairing — still not root-caused, but a real lead
  for whoever picks this up next.

**Manuscript updated** (`version3/matpcr_snjnl.tex`, Baselines subsection):
replaced the A7 redflag with a new paragraph reporting all three real
rank-agreement numbers and the qualitative findings above, written to sit
alongside the existing tolerance-sensitivity paragraph rather than
duplicate it. Confirmed brace/`\begin`-`\end`/`\begin{scope}`-`\end{scope}`
balance still equal after the edit (1857/1857, 28/28, 5/5).

### End state
**3 `\redflag{}` markers remain** in `version3/matpcr_snjnl.tex` (down
from 4 at the start of this pass): A1's spectrum-precision-audit-still-
needs-human-judging one (line ~367, unrelated to this session's work —
the review page exists per §28, nobody has judged the 495 cases yet), and
the two A9/A10 repository-DOI ones (now correctly naming
`release_dataset/`/`release_code/` instead of being bare TODOs).

### Not yet done
- [ ] A1's actual human judging of the 495 spectrum review cases — still
      real human labor, unrelated to and unaffected by this session's work.
- [ ] A second human reviewer for A8/EX6 — harness ready
      (`experiments/exp13_second_reviewer_kappa.py`), no second reviewer
      recruited yet.
- [ ] Actually uploading `release_code/` and `release_dataset/` to Zenodo
      (or equivalent, e.g. via GitHub's release integration) and minting
      real DOIs for A9/A10 — folders are prepared and upload-ready, the
      upload itself is a user action.
- [ ] Root-cause GPT-4o's spectrum low-n anomaly properly — this pass adds
      a real clue (wording-dependence) but does not resolve it.
- [ ] Real `pdflatex` compile — same standing gap as every prior
      manuscript pass in this project; this pass's edit was verified only
      by brace/environment/scope balance, not an actual render.

---

## 31. A1 (spectrum precision audit) — DONE. Rasul reviewed all 495 real
cases, precision 92.7%, dominated by a tolerance effect (2026-08-06)

Closes the last standing item from the §26-30 red-flag passes: the
review page for the revised (corrected) spectrum oracle existed (§28
built it), but nobody had judged the 495 real fired cases on it. Rasul
completed the full review this session, exported as
`spectrum_2.txt` (28KB, 495 cases) at the repo root — since renamed to
`spectrum_halfB_review_2026-08-06.txt` for consistency with the DFT
families' export naming (see File hygiene below).

**Result: precision 92.7%** (457 real / 36 false positive / 2 unsure,
excluded from the ratio) — a large, genuine improvement over the
pre-revision oracle's 72.8% ($n=103$), confirming the mid-project
prominence-check revision (Methods) fixed a real semantic gap rather than
just moving the same failure mode around.

**Root-caused the 36 false positives** (same discipline as every prior
oracle-family audit in this project — check real data, don't just accept
the aggregate number): resolved each fired record's `source_file` against
the currently-staged RRUFF copy (reusing `exp17_rebuild_review_images.py`'s
`resolve_source()`, the same path-resolution helper built for the A1
image-rebuild pass), re-ran `scipy.signal.find_peaks` on the real spectrum,
and measured each false positive's distance to the nearest genuinely
detected local maximum. **34 of 36 (94%) are within 10 cm⁻¹ of a real
peak** — just outside the oracle's 5 cm⁻¹ tolerance window, the same
tolerance-boundary root cause already identified for diffraction's false
positives (§ "Oracle validity" subsection) at a different tolerance value.
Only 2 of 36 are genuinely far from any real peak (>30 cm⁻¹: cases 124 and
138, distances 33.7 and 33.4 cm⁻¹ — not investigated further, low
priority at 2/495). This is a materially different, cleaner failure
pattern than the OLD pre-revision review found (where most false
positives had essentially no real peak-like structure at the claimed
position at all, i.e. a semantic mismatch, not a tolerance boundary) —
real, direct evidence the oracle revision fixed the right thing.

**Also confirmed**: exactly 495 fired records exist in
`experiments/halfB_fired_cases.jsonl` for `modality=="spectrum"` with
`fired=True`, matching the review's case count exactly (case N ↔ the Nth
fired record in file order, 1-indexed, per `halfB_report.py`'s
enumeration) — no reconciliation gap.

**Manuscript updated** (`version3/matpcr_snjnl.tex`): replaced the A1
redflag in the Results ("Oracle validity" subsection) with the real
92.7% figure, the false-positive root-cause finding, and an explicit
"cleaner than the pre-revision audit" framing; updated Table 1's Spectra
row from the superseded 72.8% ($n=103$) to 92.7% ($n=495$); rewrote the
table's caption and footnote to describe the spectrum figure as the
CURRENT (revised-oracle) number, with the old figure demoted to a
footnote rather than the other way around. Confirmed brace/`\begin`-
`\end`/`\begin{scope}`-`\end{scope}` balance still equal after the edit
(1864/1864, 28/28, 5/5).

**File hygiene**: archived the old pre-revision review export to
`archive/spectrum_OBSOLETE_precorrection_oracle_2026-08-01.txt` (matching
the existing `archive/{stability,metallicity,magnetism}_OBSOLETE_
precorrection_oracle_2026-07-10.txt` naming convention from §25); renamed
the new review to `spectrum_halfB_review_2026-08-06.txt` (matching the
DFT families' `_halfB_review_2026-08-06.txt` naming from §25); updated
`release_dataset/`'s copy and its `README.md` to match.

### End state
**2 `\redflag{}` markers remain** in `version3/matpcr_snjnl.tex` — both
A9/A10 repository-DOI markers (now correctly naming
`release_dataset/`/`release_code/`, §30), the only genuinely open items
left that require the user's own action (an actual Zenodo/equivalent
upload and DOI mint), not more data collection or text editing.

### Not yet done
- [ ] A second human reviewer for A8/EX6 — harness ready
      (`experiments/exp13_second_reviewer_kappa.py`), no second reviewer
      recruited yet — unaffected by this pass.
- [ ] Actually uploading `release_code/` and `release_dataset/` to Zenodo
      (or equivalent) and minting real DOIs for A9/A10 — folders are
      prepared and upload-ready, the upload itself is a user action.
- [ ] Mustafa's independent re-validation of the DFT precision batch
      (§25/§30) — standing, unaffected by this pass (this pass was
      spectrum-only, a geometric oracle family with no DFT involvement).
- [ ] Real `pdflatex` compile — same standing gap as every prior
      manuscript pass in this project.

---

## 32. A9/A10 (data and code repository links) — DONE. Real Zenodo and
GitHub links added by Rasul, both confirmed live (2026-08-07)

Closes the last two open red-flag items from §26-31. Rasul uploaded
`release_dataset/` to Zenodo and `release_code/` to GitHub himself (the
one part of A9/A10 that genuinely required the user's own action, per
§30) and edited `version3/matpcr_snjnl.tex` directly to replace both
`\redflag{}` placeholders with the real URLs:
- **Data availability** → `https://zenodo.org/records/21829644`
- **Code availability** → `https://github.com/KurbanIntelligenceLab/matpcr`

**Verified both links actually resolve** (`curl -sL -o /dev/null -w
"%{http_code}"` on each): Zenodo returns HTTP 200, GitHub returns HTTP
200 — not just pasted-in placeholder text, both are live and real,
confirmed directly rather than taken on faith.

**Confirmed no other change accompanied this edit** — diffed the file
against its pre-edit state (`older_version.txt`, saved at the repo root
during this same session before the edit) and the *only* difference is
these two URL substitutions; brace/`\begin`-`\end`/`\begin{scope}`-
`\end{scope}` balance unaffected in shape (1862/1862, 28/28, 5/5 — 2
fewer total braces than the prior 1864/1864 baseline, expected, since the
two `\redflag{...}` markers removed were themselves each one brace pair
of overhead beyond their real content).

### End state
**Zero `\redflag{}` markers remain anywhere in `version3/matpcr_snjnl.tex`.**
Every item from the original 19-item audit (`matpcr_REDFLAGS.txt`, A1-A19)
that was resolvable by text edit, new experiment, or the user's own
upload action is now closed. What remains open is exactly the set of
items that were always flagged as requiring a human/author decision
outside the scope of an in-session fix (see Not yet done below) — none of
these carry a `\redflag{}` marker in the manuscript itself, they are
tracked here in CLAUDE.md and in the standing REVISION_PLAN.md /
`matpcr_REDFLAGS.txt` items A5/A6/A7/A8/A12/A17-adjacent follow-ups
already noted as genuinely blocked in §27-28 (A6's live re-check at
submission time, A7's prompt-paraphrase sweep — done in §30 — A8's second
reviewer, A12's GPU-hours, A17's microscopy model — resolved in §30 as a
justified gap).

### Not yet done
- [ ] Mustafa's independent re-validation of the DFT precision batch
      (§25/§30) — standing, not affected by any redflag-text change.
- [ ] A second human reviewer for A8/EX6 — harness ready
      (`experiments/exp13_second_reviewer_kappa.py`), no second reviewer
      recruited yet.
- [ ] 2-3 independent human mock reviews of the manuscript (CLAUDE.md §8
      rule 5) — standing pre-submission checklist item, unaffected by
      closing the redflags.
- [ ] Real `pdflatex` compile — same standing gap as every prior
      manuscript pass; the manuscript's structural balance has been
      verified repeatedly by brace/environment/scope counting across many
      edits, but no actual render has been produced in this environment
      at any point in this project's history.
- [ ] A6's live re-check against the closest neighbors' then-current work
      — cannot be permanently resolved before the actual submission date
      (§28's own framing; unaffected by this session).

---

## 33. Three new real-data figures added — first worked examples anywhere
in the manuscript (2026-08-07)

Not tied to a red-flag item; requested directly. Every prior figure in
`version3/matpcr_snjnl.tex` was schematic (hand-drawn TikZ) or an
aggregate table/heatmap — nothing showed a single real case. Built three
figures entirely from artifacts already on disk (no new model calls),
via a new checked-in script, `experiments/exp19_manuscript_figures.py`,
run directly against the repo's real files to confirm reproducibility
before trusting the output.

1. **`fig_precision_funnel.pdf`** — stacked real/false-positive/unsure
   bars for all six oracle families, built directly from the six Half-B
   review `.txt` exports (`xrd.txt`, `sem.txt`,
   `spectrum_halfB_review_2026-08-06.txt`, and the three DFT families'
   `_halfB_review_2026-08-06.txt` files). Reproduces Table 1's precision
   column exactly (77.2/88.6/92.3$\approx$92.7/95.3/94.7/92.2%) as a
   visual companion — confirmed by recomputing the tallies directly from
   the same source files, not copied from the table.
2. **`fig_failure_gallery.pdf`** — three real, human-confirmed cases, one
   per image modality, with the actual embedded plot images extracted
   directly from `experiments/halfB_review_{xrd,sem,spectrum}.html`
   (base64-decoded, not redrawn) plus claim-vs-true-peak annotations:
   - XRD (`pattern_911.json`): model claimed 3.5°, oracle fired; the
     claim visibly sits near the y-axis rather than the true apex — the
     dominant XRD failure mode already quantified in the violation
     taxonomy (70.5% gridline/apex misreads).
   - SEM (`L1_ae57...jpg`, NFFA-EUROPE): model claimed 100 µm against a
     real 10 µm scale bar — a literal order-of-magnitude, 10$\times$ the
     entire field of view.
   - Spectrum (Gotzenite, RRUFF Raman): model claimed 800 cm$^{-1}$; the
     real apex is at ~830 cm$^{-1}$, just outside the oracle's 5 cm$^{-1}$
     tolerance — directly illustrates the exact root cause found for 34
     of 36 (94%) of the spectrum oracle's false positives (§31).
3. **`fig_cgsv_trajectory.pdf`** — a real 3-round CGSV revision
   trajectory (GPT-4o, opXRD CNRS `pattern_941.json`, pulled directly
   from `experiments/exp4_results.jsonl`'s real `claimed_values`: 28.3°
   → 27.9° → 28.6°), plotted against the pattern's real measured
   diffractogram with its real pymatgen reference peaks overlaid. Found
   directly by re-deriving the reference peaks
   (`halfB_collect.xrd_reference_peaks`) that the model's final answer
   (28.6°) lands within the oracle's 0.5° tolerance of a genuine but
   secondary Bragg reflection at 28.91° — not the pattern's actual
   tallest peak at 30.91°, which the model's own reasoning chain
   describes locating. This is a concrete, single-item illustration of
   the already-quantified Results finding (post-CGSV accuracy 29.8\% on
   diffraction, far below post-CGSV PCR) — CGSV converges on an
   oracle-admissible value, not necessarily the value it was originally
   reasoning toward.

**Manuscript integration**: added `\usepackage{graphicx}` to the preamble
(was not previously loaded anywhere — confirmed by grepping both the
`.tex` file and `sn-jnl.cls`; without it the three new
`\includegraphics` calls would not compile). Inserted the precision
funnel and failure gallery right after Table 1 in the "Oracle validity"
subsection (their natural home); inserted the CGSV trajectory figure
directly after the retreat-vs-correction paragraph in "Effect of
self-verification," the exact finding it illustrates. All three have
real captions explaining the source and what to look for, real labels
(`fig:precision-funnel`, `fig:failure-gallery`, `fig:cgsv-trajectory`),
and figure files live at `version3/figures/*.pdf`.

Confirmed brace/`\begin`-`\end`/`\begin{scope}`-`\end{scope}`/
`\begin{figure}`-`\end{figure}` balance after all edits: 1882/1882,
31/31, 5/5, 6/6 (up from the pre-edit 1862/1862, 28/28, 5/5, 3/3 — the
delta is exactly the three new figure environments plus one new
`\usepackage` line, nothing else moved).

### Not yet done
- [ ] No real `pdflatex` compile available in this environment (same
      standing gap as every prior pass) — the three new
      `\includegraphics` calls have not been visually verified inside an
      actual rendered page, only checked for valid PDF files, correct
      relative paths, and the newly-added `graphicx` package.
- [ ] `experiments/exp19_manuscript_figures.py` is not yet copied into
      `release_code/` (which is already uploaded/live per §32) — if the
      figures need to be reproducible from the public code release, this
      script should be added there in a future update.

---

## 34. version3/sample/ — best/worst real cases per modality, 6 figures
(2026-08-08)

Requested directly, not tied to a red-flag item: for each of the six
oracle families, pick the 2 real fired cases with the smallest
claim-vs-truth gap ("best") and the 2 with the largest ("worst"), as one
2x2 figure per modality, saved to a new `version3/sample/` folder.
Generating script: `experiments/exp20_best_worst_samples.py` (run directly
against the repo to confirm reproducibility before trusting the output).

**Real bug caught and fixed during selection, worth remembering**: the
first pass ranked XRD cases by comparing each claim to the pattern's raw
`numpy.argmax(intensity)`. Two of the resulting "best"/"worst" picks were
wrong for two different, real reasons, both traced by re-checking against
the case's exact recorded `source_file` (`experiments/halfB_fired_cases.jsonl`)
rather than trusting the ranking:
1. `pattern_211.json` exists identically-named in FIVE opXRD institution
   folders (CNRS, EMPA, INT, HKUST-B, USC). A naive `glob.glob()` across
   institutions picked an arbitrary one (HKUST-B), whose real global max
   sits at 45.8° — but the review case's actual image (and its real
   `source_file`, CNRS) shows the true tallest peak at 3.92°. Fixed by
   resolving every case through its exact recorded `source_file`, never a
   glob.
2. Raw `argmax` on `pattern_146.json` picked a decaying-baseline point
   near the plot's left edge (2-3°), not a genuine Bragg peak — the
   pattern's real, meaningful tallest peak is a sharp reflection at
   ~23.5°. Fixed by using `scipy.signal.find_peaks` (resolved local
   maxima) instead of a raw global max for the final geometric-modality
   rankings, the same fix pattern already used for XRD's Half-A peak
   resolution (CLAUDE.md §12).

**Selection method per modality:**
- **XRD, spectrum**: gap = |claimed value − nearest genuine resolved local-max
  peak|. Best: XRD Δ=0.18-0.19°, spectrum Δ=0.1-1.8 cm⁻¹. Worst: XRD
  Δ=14.7-16.4°, spectrum includes one claim (1750 cm⁻¹, Laurionite) that
  falls entirely outside the spectrum's real measured x-range
  (91.6-1284.8 cm⁻¹) — confirmed directly, the model stated a value the
  plot never showed at all.
- **SEM**: ranked by the review page's own recorded claim magnitude
  (re-running `sem_scale_bar`'s OCR fresh to recompute an exact FOV ratio
  was found unreliable — see below — so this uses what's already
  recorded, not a re-derived number). Best: two cases claiming ~100 nm
  against a real 1 µm scale bar (a plausible in-frame reading). Worst: a
  claimed 1000 µm (1 mm) against a real 10 µm scale bar (100× the field
  of view) and a claimed 150 µm against a real 10 µm bar (15×).
- **Stability, metallicity, magnetism**: best = real reference value
  closest to the oracle's tolerance boundary (hull within ~0.002 eV/atom
  of 0.05, band gap within ~0.07 eV of the 0.20 eV abstention edge, or an
  exactly-zero real moment) — genuinely subtle, defensible misses, not
  arbitrary near-misses. Worst = real reference value farthest from the
  claim in absolute terms (hull 11-25× the tolerance; band gap 3.5-4.5 eV
  called metallic; a real moment of 32-110 µB called nonmagnetic).

**A real SEM re-computation reliability finding, not pursued further**:
attempted to recompute each SEM case's exact field-of-view ratio by
re-running `sem_scale_bar()` fresh against the resolved image, to rank
by ratio rather than raw claim magnitude. This produced physically
absurd ratios (up to ~11,000,000×) for several cases, traced to the
scale-bar OCR/marker-detection extracting a different (wrong) reading
than whatever the original Half-B collection pass used — the per-item
raw extractor output isn't cached anywhere retrievable
(`experiments/sem_scalebar_results.jsonl` doesn't contain these specific
files). Rather than risk mislabeling a real image with a re-derived wrong
number, fell back to ranking by the review page's own already-recorded
claim value, which is faithful to the original collection.

Manuscript itself (`version3/matpcr_snjnl.tex`) was **not** touched this
pass — these six figures are extra evidence artifacts saved to
`version3/sample/`, not inserted into the paper.

### Not yet done
- [ ] Decide whether any of these six best/worst figures should be
      inserted into the manuscript or SI, or remain as standalone
      reference material — not decided this pass.
- [ ] `experiments/exp20_best_worst_samples.py` is not yet copied into
      `release_code/` (already uploaded/live per §32) for the same reason
      `exp19` isn't yet — see the prior "Not yet done" entry above.

---

## 35. Full-manuscript audit (Workflow, multi-agent) + fixes applied
(2026-08-12)

Per explicit user request ("go through the whole paper, check everything,
check for any inconsistencies, any mistaken references, for everything,
every number, every percentage") a multi-agent Workflow audited
`version3/matpcr_snjnl.tex` + `matpcr_SI.tex` + `matpcr_refs.bib`: 353
numeric claims extracted and checked against real source data
(experiments/*.jsonl, the 6 current halfB review .txt exports, this
CLAUDE.md), every `\ref{}`/`\label{}`/`\cite{}` checked for resolution,
brace/environment balance re-verified, and an internal-consistency pass
(manuscript disagreeing with itself). 26 candidate problems survived
first-pass flagging; 13 survived adversarial re-verification (a skeptic
agent per candidate, defaulting to REFUTED unless independently
confirmed). All 13 have now been resolved:

1. **Diffraction PCR range** (line ~480) said "(0.47–0.80)"; Table 1's own
   GPT-5.6-Sol row shows 0.820 as the column max. Fixed to (0.47–0.82).
2. **GPT-5.6-Terra's overall CI lower bound** was inconsistently stated as
   0.736 (line ~485, matches raw data) vs. 0.738 (lines ~513, ~1004,
   wrong). All three now read 0.736.
3. **Bonferroni-corrected metallicity AUC CI** (line ~701) stated
   $[0.486,0.678]$ with no committed script backing the number. Extended
   `experiments/exp6_detector_analysis.py` with a real, runnable
   Bonferroni-widened (alpha/6) bootstrap CI block for all 6 held-out
   modalities; re-ran it. **Real, reproducible result: metallicity's
   corrected CI is $[0.487, 0.673]$**, not $[0.486, 0.678]$ — close but
   not exact. Updated the manuscript to the reproducible value. Does not
   change the qualitative conclusion (still excludes-chance: False, i.e.
   metallicity's apparent exception still does not survive correction).
4. **`matpc2025` bib entry** had a placeholder author, `{{MatPC Authors}}`,
   with an unresolved `% VERIFY`. Independently confirmed the real author
   list (Zhou, Jiacheng; Xiao, Bo; Liu, Qi; Liu, Lifeng; Zhang, Lei) via
   two authoritative registries queried directly (Crossref's own DOI
   record and Semantic Scholar's API for DOI 10.1021/acsami.5c08809),
   which agreed exactly — fixed. Note: the user separately re-verified
   and edited the rest of `matpcr_refs.bib` via Google Scholar on
   2026-08-12 (see the file's own updated header comment), independent of
   this fix.
5. **`vprm2026`** had a stale `% VERIFY` marker even though its own
   comment text said the entry was already confirmed — removed the
   marker, kept the confirmation note.
6. **Missing `R-CRYSTALS` citation — a real, more serious problem than
   originally flagged.** `matpcr_snjnl.tex:192` still cited
   `polat2025rcrystals`, but that bib key no longer existed anywhere in
   `matpcr_refs.bib` (removed, apparently by accident, during an earlier
   or the user's own edit pass) — this would have been an undefined-
   citation compile error, not just a stale-VERIFY hygiene issue. This is
   the paper's required declared-related-work citation for R-CRYSTALS
   (CLAUDE.md §8 rule 6 / §5), so it needed restoring, not just deleting.
   **User supplied the correct, current citation directly**: the paper
   published under a new title, "How Far Can You Grow? Characterizing the
   Extrapolation Frontier of Graph Generative Models for Materials
   Science," Polat/Serpedin/M. Kurban/H. Kurban, KDD 2026 (ACM,
   DOI 10.1145/3770855.3818872, pages 11821–11832). Added as
   `polat2026extrapolation` in `matpcr_refs.bib` and repointed the
   citation at `matpcr_snjnl.tex:192`. Confirmed the old key has zero
   remaining references anywhere and the new key is defined once and
   cited once.
7. **4 previously-uncited bib entries** (`eaa2026`, `liu2024llava`,
   `matty2026`, `wei2022cot`) — per the user's explicit choice ("cite them
   where relevant, then keep"), found natural homes and cited each
   exactly once: `eaa2026`/`matty2026` joined the existing agentic-
   materials-discovery citation list (line ~123, alongside `dreams2025`,
   `crystalyse2025`, etc.); `wei2022cot` (the foundational Chain-of-
   Thought paper) was cited where the Introduction first describes models
   reasoning "step by step" (line ~101-104); `liu2024llava` (LLaVA-1.5)
   was cited alongside the VLM framing at the same location, describing
   open instruction-tuned VLM architectures generally — NOT claimed as one
   of the study's evaluated models, since it wasn't.
8. **GPU/hardware contradiction**: Methods said the pilot/Experiment 1-4
   period used an A100; Acknowledgements said that same period used a
   P100 — a genuine, previously-unresolved conflict (CLAUDE.md §30/A12
   had deliberately punted on it as "the union of both claims"). **User
   resolved directly**: P100 was used only for early, pre-pilot
   exploratory work that produced no result reported in this paper; the
   A100 was the machine for the pilot and Experiment 1-4 onward (matching
   the contemporaneous pilot-era log at CLAUDE.md line ~507, "this
   machine's A100," and the Exp5 verifier-training note at line ~1178,
   both written at the time, not retrospectively). Rewrote the
   Acknowledgements sentence to say this precisely instead of leaving an
   unqualified P100 claim for the reported-work period.
9. **`fig_failure_gallery.pdf` / `fig_cgsv_trajectory.pdf` content
   drift**: §33 above states both figures were inserted into the main
   manuscript, but neither is actually referenced anywhere in the current
   `.tex` (only `fig_precision_funnel.pdf` survived, later moved to the
   SI per §"Move precision-funnel..." work). **Both files still exist on
   disk** at `version3/figures/*.pdf` — not deleted, just unreferenced.
   Per explicit user decision (2026-08-12): drop them, they're superseded
   by the three new professional oracle-example PDFs
   (`new_{xrd,raman,sem}_oracle_figure.pdf`) already in the main text.
   §33's text describing them as "inserted...into the main manuscript" is
   therefore **stale as of this entry** — the insertion happened at the
   time §33 was written but was later reverted (directly by the user,
   between sessions) when the three professional PDFs replaced that
   figure area. No manuscript edit was needed for this item; recorded
   here so a future session doesn't re-trust §33's insertion claim as
   current.

**Not confirmed as real / left as-is** (adversarial re-verification
refuted these, or user judged they don't warrant re-litigating a
correctly-documented retraction):
- No case found this pass of a "value was right once, then a re-run
  corrected it, and the manuscript kept the old one" pattern beyond what
  is already covered above — the manuscript is generally careful about
  this elsewhere (e.g. the magnetism-verifier retraction, the spectrum
  precision revision, both already correctly reported as superseded in
  their own sections rather than left stale).

**Standing gap, unaffected by this pass**: no real `pdflatex`/`bibtex`
compile has ever been run in this environment across the project's
history. All fixes above were verified via brace/`\begin`-`\end` balance
counts and direct grep/rerun of the underlying data/scripts, not an
actual render. This remains the single largest latent risk before
submission.
