# MatPCR — Full Session Knowledge Dump & Reproducibility Audit

Written 2026-07-31. Purpose: (1) capture everything learned across this
project's sessions in one place, distilled from `CLAUDE.md` (1600+ lines) and
this session's own work; (2) audit exactly what is and is not reproducible
right now, after `/ephemeral` and `/tmp` were wiped by a machine
reboot/reset (confirmed 2026-07-31: `/ephemeral` is a fresh, nearly-empty
disk; `/tmp/matpcr_secrets/` and its API keys are gone; `~/.local`, symlinked
to `/ephemeral/matpcr/local`, is a dangling link — every pip-installed
package in the main environment, not just datasets, is gone).

This file is a **companion to `CLAUDE.md`**, not a replacement. `CLAUDE.md`
remains the authoritative, chronological project log; this file is a
reorganized, audited summary optimized for "what do I have, what did I lose,
what do I need to do to get back to a working state."

---

## 1. What the project is

Build and evaluate **MatPCR**: a label-free way to measure whether a
vision-language/language model's *reasoning* about materials data (not just
its final answer) is physically consistent, using physics itself — not human
labels — as the ground truth. Target venue: npj Computational Materials
(Nature Portfolio), not core Nature. Three humans: Hasan Kurban (PI,
coordinates), Mustafa Kurban (validates all DFT physics — his sign-off is a
standing gate), Rasul (runs all experiments; the user in this session).

Five contributions: (1) reframe evaluation around reasoning-chain physical
consistency; (2) MatPCR — programmatic + DFT-grounded oracles; (3) PCR
metric with bootstrap CIs + exact McNemar; (4) a released, fine-tuned
physical-consistency verifier; (5) CGSV, a label-free self-verification loop.

---

## 2. Repository layout — what's actually in git (survives everything)

Everything under `/home/ubuntu/nature_submission` is a git repo, clean
working tree, nothing uncommitted lost. This includes:

- `matpcr_metrics.py` — the only production code; numpy-only oracles +
  metrics + a synthetic smoke test (`python3 matpcr_metrics.py`, currently
  passing, includes a `cohens_kappa` check added this session).
- `experiments/*.py` — ~30 scripts, one per experiment/analysis stage
  (pilot, Half-A/Half-B collection, exp1 through exp14, review-page
  generators, the SEM scale-bar extractor).
- `experiments/*.jsonl` / `experiments/*.json` — **every experiment's raw
  result records, all committed to git, all survived the wipe.** This is the
  single most important fact for reproducibility: the *numbers* in the
  manuscript do not depend on `/ephemeral` at all once collected. Re-deriving
  a number from these files (aggregation, re-plotting, re-computing a
  statistic) works right now, with no external dependency.
- `matpcr_snjnl.tex` (root, 835 lines) — **stale**, pre-Phase-1 numbers, no
  Baselines subsection, no SI table. Left untouched by explicit user
  decision (2026-07-20).
- `VERSION2/matpcr_snjnl.tex` (1473 lines) — **current, correct, complete**
  manuscript. All Phase 0–3 corrections applied. This is the one to build
  from for real submission.
- `matpcr_refs.bib`, `sn-jnl.cls`, `sn-nature.bst` — bibliography and the
  (patched-mirror) Springer Nature class files.
- `xrd.txt`, `sem.txt`, `spectrum.txt`, `stability.txt`, `metallicity.txt`,
  `magnetism.txt` — human review exports from Half-B manual audits. The 3 DFT
  ones are **stale** (predate the Mustafa-driven oracle redesign) — do not
  reuse for precision numbers.
- `REVISION_PLAN.md` — the phase-by-phase plan this and prior sessions
  executed against (Phase 0–3 all done; Final Gate items still open).
- `CLAUDE.md` — the full chronological project log (§1–§20). Read this for
  any specific historical detail this summary compresses away.

**Symlink now broken**: `opxrd -> /ephemeral/matpcr/opxrd` (dangling — target
gone). Harmless (nothing currently reads through it at rest), but will error
if a script tries to use it before the data is re-fetched.

---

## 3. What lived on `/ephemeral` and is now gone

`/ephemeral/matpcr/` held everything too large for the git repo or the small
root disk. All of it is gone. Enumerated exactly (grepped from `CLAUDE.md`):

| Path | Contents | Size (last known) |
|---|---|---|
| `/ephemeral/matpcr/local` | `~/.local` pip-install target — **every pip package in the main env** | ~4GB+ |
| `/ephemeral/matpcr/hf_cache` | HuggingFace cache (Qwen2.5-VL-7B-Instruct weights, etc.) | 16GB+ |
| `/ephemeral/matpcr/opxrd` | opXRD real XRD patterns (92,552 JSON files) | — |
| `/ephemeral/matpcr/val.db` | SimXRD-4M val split (never actually used in any script) | 26GB |
| `/ephemeral/matpcr/rruff/` | RRUFF Raman spectra (excellent_unoriented.zip extracted) | ~240MB |
| `/ephemeral/matpcr/nffa/extracted/` | NFFA-EUROPE SEM images (18,424 JPGs) | 12GB |
| `/ephemeral/matpcr/mp_data/` | Materials Project reference pull + `mp_provenance.json` | — |
| `/ephemeral/matpcr/verifier_weights/` | **The 13 trained verifier LoRA adapters — never pushed publicly** | — |
| `/ephemeral/matpcr/matterchat/` | MatterChat checkpoint, Mistral-7B base model, isolated venv | ~30GB+ |

Also gone (not under `/ephemeral` but wiped by the same reboot):
- `/tmp/matpcr_secrets/.env` — held `OPENROUTER_API_KEY` and `MP_API_KEY`.
  **Both need to be regenerated/re-entered before any script that calls an
  API can run.**
- Any HF cache, pip cache, or other `/tmp` scratch state.

---

## 4. Reproducibility audit — per dependency, verified live today (2026-07-31)

I checked each of these directly (not from memory) before writing this
table.

| # | Dependency | Status | Verified how |
|---|---|---|---|
| 1 | **opXRD** (Zenodo record 15298026, CC-BY-4.0) | ✅ Re-downloadable, fully automatable | `curl -I` → 200 OK |
| 2 | **RRUFF** (rruff.net bulk ZIPs) | ✅ Re-downloadable, fully automatable | `curl -I` → 200 OK |
| 3 | **NFFA-EUROPE** (B2SHARE record qtq9v-ys023) | ✅ Re-downloadable, fully automatable, MD5s in the API response | `curl` the API → live JSON |
| 4 | **Materials Project** (via `mp-api`) | ⚠️ Re-fetchable, but **needs a brand-new API key** — old key was only in the wiped `.env`, never in git (correctly, since it's a secret) | Account presumably still exists at next-gen.materialsproject.org; key must be regenerated by a human |
| 5 | **SimXRD-4M val split** | ❌ NOT automatable — original download was manual browser + rsync from a non-scriptable OneDrive link. **But: never used by any script** (grepped, zero hits) — losing it costs nothing currently reproducible | `grep` across `experiments/*.py` → no references |
| 6 | **Qwen2.5-VL-7B-Instruct** (local model) | ✅ Re-downloadable, standard public HF repo | `curl -I` on `resolve/main/config.json` → 307 (normal HF redirect, not a 401 gate) |
| 7 | **MatterChat checkpoint + dataset** (Zenodo 18735961/18735881) | ✅ Re-downloadable, CC-BY-4.0, fully automatable | `curl -I` on the direct file URL → 200 OK, correct content-length |
| 8 | **Mistral-7B-Instruct-v0.3** (MatterChat's base LLM) | ✅ Re-downloadable via the ungated `mistral-community` mirror (the official `mistralai/` repo is gated, but the mirror isn't) | `curl -I` → 307, not 401/403 |
| 9 | **The MatterChat isolated venv** (pinned old deps: `transformers==4.42.4`, `pytorch-lightning==2.3.3`, `pymatgen==2024.4.13`, `ase==3.22.1`, etc.) | ⚠️ Reconstructable, not automatic — this session hit and fixed 6 real dependency issues one at a time (CUDA build mismatch, missing `pkg_resources`/`timm`/`protobuf`, `ase`'s `ExpCellFilter` rename). None of these fixes are scripted anywhere; a future session would need to rediscover them or read this file/CLAUDE.md §16/EX5 notes first | Not independently re-verified this session (would require repeating the ~1hr build) |
| 10 | **Released verifier weights** (13 LoRA adapters, Experiment 5's actual artifact) | ❌ **Genuinely, permanently lost as exact files.** Never pushed to a public repo. Training is **not seeded** (`exp5_train_verifier.py` has no `set_seed`/`torch.manual_seed` near its `Trainer` setup) — re-running reproduces *equivalent* performance (confirmed once already, per CLAUDE.md §16: a prior re-run matched original numbers within normal training noise) but not bit-identical weights | Read `exp5_train_verifier.py` directly; grepped for seed calls near `Trainer(...)` — none found |
| 11 | **Main-env Python packages** (`pymatgen`, `ase`, `mp-api`, `torch`, `transformers`, and everything else installed via the `~/.local` symlink) | ❌ Gone, but trivially reinstallable via `pip install` — the *packages* aren't hard to get back, only the **exact version-pin history** (e.g. the `emmet-core==0.85.1` pin needed to dodge a `mp-api`-pulled release-candidate bug) is only recorded in prose in `CLAUDE.md`, not in a `requirements.txt` | Confirmed all four `import` calls fail right now |
| 12 | **API keys** (`OPENROUTER_API_KEY`, `MP_API_KEY`) | ❌ Gone, human action required (regenerate at OpenRouter / Materials Project) — correctly were never committed to git | Confirmed `/tmp/matpcr_secrets/` no longer exists |
| 13 | **Every experiment's result files** (`experiments/*.jsonl`, `*.json`) | ✅ **Fully intact**, committed to git, survived everything | `git status` clean, files present and readable |
| 14 | **The manuscript, bibliography, class files, cover letter** | ✅ Fully intact | Present, `VERSION2/matpcr_snjnl.tex` recompiles clean as of the last session |

### Bottom line
- **Nothing already-measured is at risk.** Every number in every table in
  `VERSION2/matpcr_snjnl.tex` traces back to a `.jsonl`/`.json` file that is
  safely in git. You do not need any of the lost infrastructure to read,
  cite, or write about existing results.
- **Re-running anything that touches raw data, a local model, or an API
  requires, in order: (a)** a fresh `MP_API_KEY` and `OPENROUTER_API_KEY`
  (human step), **(b)** reinstalling the Python environment (mechanical, but
  the exact version pins — especially `emmet-core==0.85.1` — are only in
  prose, not a lockfile — a real gap worth fixing), **(c)** re-downloading
  opXRD/RRUFF/NFFA-EUROPE/MP-data (all automatable, no human step needed),
  **(d)** for MatterChat specifically, rebuilding the isolated venv with its
  own older pins (partially undocumented as a script — the fixes are prose
  in this session's transcript / CLAUDE.md, not a `setup.sh`).
- **The one truly irrecoverable artifact is the exact verifier weight files.**
  Re-training gives an equivalent, not identical, result. If the plan is to
  actually release these weights (the runbook says to), that release has to
  happen from a re-trained copy now, and should probably happen soon, before
  another wipe.
- **SimXRD's loss is free** — it was never wired into anything.

---

## 5. The oracles — current, corrected design (as of Phase 0, 2026-07-16/17)

All three DFT oracles were redesigned mid-project after the supervisor audit
and Dr. Mustafa's formal review comments. The geometric oracles also had one
significant correction (spectrum).

- **XRD (Bragg's law)**: `xrd_peak_consistent(claimed_2theta, ref_peaks,
  tol_deg=0.5)`. Unchanged since Phase 0. Real finding this session (Phase
  2/item 19): **the model ranking on this constraint type is NOT robust to
  the tolerance choice** — flips completely between tol=0.25° and tol=1.0°.
- **SEM (scale bar)**: exact FOV threshold, no ambiguity window, unchanged.
- **Spectrum (Raman/IR peak)**: **corrected mid-project** — changed from a
  windowed-maximum check to requiring a genuine interior local maximum (with
  defined prominence, rejecting monotonic rises/shoulders). This single fix
  collapsed reported spectrum PCR from ~0.62–0.88 (pre-fix) to ~0.10–0.18
  (post-fix) across every model. Any spectrum number dated before
  2026-07-16 is stale.
- **Stability**: `stability_claim_consistent(claimed_stable,
  e_above_hull_eV_atom, tol_eV_atom=0.05)`, with sensitivity reported at
  {0, 0.025, 0.05, 0.10} eV/atom (all four gave 0% FN/FP in the positive
  control). 0–0.05 eV/atom must be called "near-hull/metastable," never
  "stable" outright (Mustafa's explicit condition).
- **Metallicity**: `metallicity_claim_consistent(claimed_metallic,
  band_gap_eV, metal_max_eV=0.05, gap_min_eV=0.20)` — returns `None`
  (excluded from PCR) for the 0.05–0.20 eV ambiguous band. Mustafa's literal
  thresholds, not the code's inherited 0.3 eV default.
- **Magnetism — the biggest redesign**: renamed from
  `property_sign_magnitude_consistent` to `magnetism_magnitude_consistent`.
  **Sign is never checked** (a DFT magnetization's sign is an arbitrary axis
  choice, not a physical claim). New protocol: normalize to
  `|total_magnetization|/nsites` (per-atom, never raw), classify
  magnetic-vs-not at 0.05 μB/atom, then compare magnitude only within the
  magnetic class (order-of-magnitude band). A near-zero reference is
  `zero_atol=1e-6`, not exact float equality (a real bug found and fixed
  during Half-A: 82/3000 real materials had `0 < |mag| < 1e-6`).

All oracle logic lives in `matpcr_metrics.py`; smoke test at the bottom of
that file (`python3 matpcr_metrics.py`) exercises every oracle including the
new `cohens_kappa` added this session, and currently passes.

---

## 6. Data provenance for the DFT numbers

`mp_provenance.json` (was at `/ephemeral/matpcr/mp_data/`, now gone but its
*content* is quoted verbatim in CLAUDE.md §9 and reproduced here):

```
source: Materials Project (materialsproject.org)
client: mp-api
database_version: 2026.04.13
retrieval_date: 2026-07-16
calculation_type: GGA/GGA+U relaxation, Materials Project standard workflow
fields_pulled: material_id, formula_pretty, energy_above_hull, is_stable,
               band_gap, is_metal, total_magnetization, nsites
n_requested: 3000, n_docs_returned: 3000
note: standardized computational references, NOT experimental ground truth
```

`mp-api` compatibility note: the latest `mp-api` pulls in
`emmet-core==0.86.0rc1` (a release candidate), which imports `NotRequired`
from the stdlib `typing` — Python 3.11+ only. This machine runs Python 3.10.
**Fix: pin `emmet-core==0.85.1`.** This is the single most important
version pin to remember when rebuilding the environment; it is currently
recorded only in prose (CLAUDE.md §9 and this file), not in any
`requirements.txt`.

Materials Project's own `is_stable` field uses an exact-zero threshold, NOT
the oracle's 0.05 eV/atom tolerance — 571/3000 (19%) of real materials are
`is_stable=False` by MP's own flag but within the oracle's tolerance. This is
a real, substantive definitional question for Mustafa's review, not a bug.

---

## 7. Experiment-by-experiment result summary (all numbers verified against
committed files, current/corrected as of this session)

### Experiment 1 — the gate (positive control + precision audit)
All 6 oracle families: 0% false-negative rate at planted violation rates
10/30/50%. Precision audit (human review of real fired cases):
- Diffraction (XRD): 77.2% (n=101)
- Microscopy (SEM): 88.6% (n=105)
- Spectra (Raman): 72.8% (n=103) — **stale**, predates the spectrum-oracle
  fix; no fresh audit has been done on the corrected oracle
- Stability / Metallicity / Magnetism: **pending human review** — review
  pages regenerated against the corrected oracles, but nobody has completed
  the manual pass yet. This is the single biggest standing "needs a human"
  blocker.

### Experiment 2 — main PCR sweep (`experiments/exp2_results.jsonl` +
`exp2_refresh_results.jsonl`)
8 models total (4 original + 4 current-gen refresh added this session) × 6
constraint types × 3 seeds. Full corrected grid:

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

*DFT column provisional, pending Mustafa's sign-off.

Real finding: capability scaling is NOT automatic — GPT-5.6-Terra clearly
beats GPT-4o (non-overlapping CIs), but Claude Opus 4.6 does not beat Claude
Sonnet 4.5, and explicit reasoning mode (Qwen3-VL-8B-Thinking) does not beat
its non-reasoning sibling (both CIs overlap).

### Experiment 3 — accuracy vs. consistency (`exp3_results.jsonl`)
Mean gap across 12 cells: **22.2%** (revised down from an earlier 41.8% once
the spectrum fix flowed through). Diffraction now dominates the gap
(58.1% in one cell); spectrum's gap shrank to 4.2–11.2% (was the largest
gap pre-fix, now one of the smallest — the qualitative story flipped, not
just the number). Stability balanced accuracy (correcting for class
imbalance): Qwen2.5-VL-7B 0.494, Gemini 0.681, GPT-4o 0.476, Claude Sonnet
4.5 0.971 — 3 of 4 models drop to at/near chance once corrected; only
Claude's apparent stability skill survives.

### Experiment 4 — CGSV effect (`exp4_results.jsonl`, 545 records)
b=0 (zero regressions) in every cell, for every model, always. All 4 models
significant: Qwen 0.338→0.439 (p=3.1e-5), Gemini 0.521→0.632 (p=2.4e-4),
GPT-4o 0.434→0.593 (p=7.6e-6), Claude 0.373→0.639 (p=4.6e-13). Resolved the
correction-vs-retraction question (BL4) with a direct check: all 545 items
expose exactly 1 checkable claim before and after, every round — so a PCR
gain here cannot be explained by the model dropping/hedging a claim, only by
the claim's value actually changing.

### Experiment 4b — mechanism-isolation controls (`exp7_results.jsonl`,
new this session, $12.19 API cost)
Unaided self-refinement: 0.349→0.339, n.s. (p=0.615), b=34 (real
regressions). Generic re-prompting: 0.358→0.342, n.s. (p=0.20), b=24. Neither
control reproduces CGSV's effect — supports attributing CGSV's gain to the
oracle signal specifically. Best-of-3: random-pick PCR=0.363, oracle-oracle
ceiling=0.419.

### Experiment 5 — verifier (`exp5_results.jsonl`, 2,152 records,
source-disjoint split — fixed a real train/test leak this session's prior
work)
In-distribution: precision 0.768, recall 0.706, F1=0.735, **AUC=0.850**,
ECE=0.096. Held-out-constraint-type (all 6, none usable):

| Constraint type | AUC | 95% CI |
|---|---|---|
| Diffraction | 0.497 | [0.419, 0.578] |
| Microscopy | 0.527 | [0.468, 0.589] |
| Spectra | 0.558 | [0.488, 0.626] |
| Stability | 0.436 | [0.370, 0.502] |
| Metallicity | 0.582 | [0.510, 0.652] |
| Magnetism | **0.503** | **[0.430, 0.576]** |

**Magnetism's held-out AUC was previously reported as 0.867 (a "clear
exception," the headline positive surprise of the whole verifier section).
This has been retracted** — confirmed under both held-out-modality and
held-out-constraint-type splits, both landing at chance. The 0.867 was an
artifact of a record-level (not source-disjoint) split leaking item
identity across train/test.

### Experiment 6 — detector analysis
Same corrected numbers as Exp5's held-out AUCs (they're the same
probs/labels). Do NOT report a pooled cross-constraint-type AUC (a naive
concatenation gave 0.315, an artifact of pooling separately-trained models'
non-comparable probability scales — recognized and deliberately not reported
in the manuscript).

### New this session (Phase 2, items 15–23 + EX6)
- **Item 17 — verifier baselines**: zero-shot LLM-judge (Gemini Flash Lite)
  AUC=0.447 in-distribution; self-confidence (local model's own token
  log-prob) AUC=0.315, **significantly below chance**. Investigated directly:
  the model is *more* confident when physically wrong (mean logprob −2.84 for
  violations vs. −3.99 for clean chains, on a 40-item check) — a real,
  non-obvious finding, not a sign bug.
- **Item 16 — MatterChat domain evaluee**: stability PCR=0.783,
  metallicity=0.795 (n=112/120), magnetism=0.850, on 120 real, *shuffled*
  Materials Project structures (a first, unshuffled attempt gave a
  3.3%-magnetic sample vs. the true ~65%, caught and fixed before trusting
  the result).
- **Item 19 — tolerance sensitivity**: diffraction's model ranking flips
  completely across the tolerance grid tested (rank agreement 0.0); spectrum
  is fully robust (1.0); stability partially robust (0.67).
- **Item 20 — violation taxonomy**: diffraction failures 70.5%
  gridline/scale misread, 14.1% peak misidentification; microscopy failures
  37.6%+23.7% scale-bar unit/conversion errors.
- **Item 21 — contamination check**: zero metadata-leakage hits across 2,152
  records; opXRD's Zenodo publication date (2025-04-28) postdates GPT-4o's
  cutoff, ruling out that specific pairing.
- **Item 22 — detector calibration**: every held-out split is severely
  miscalibrated in the same direction (low-probability bins massively
  underestimate the true violation rate) — at the default 0.5 threshold
  recall on held-out data is near zero; a 0.05 threshold recovers usable
  recall at a real precision cost.
- **EX6 — second-reviewer harness**: `cohens_kappa` added to
  `matpcr_metrics.py` (smoke-tested), `exp13_second_reviewer_kappa.py`
  built. Genuinely blocked on an actual second human reviewer completing an
  independent pass — the tool is ready, the labor is not done.

---

## 8. Manuscript state

`VERSION2/matpcr_snjnl.tex` is the current, correct, complete manuscript:
all 16 `\redflag{}` markers resolved with real data; 2 remaining are
intentional author-only placeholders (funding/grant numbers, GPU-hours).
Compiles clean (`pdflatex ×3 + bibtex`, 29 pages, zero undefined
references/citations) as of the last build. New content added this session:
a "Baselines, ablations, and controls" section with 5 fully-written
paragraphs, SI Table S1 (48 per-cell bootstrap CIs), an Acknowledgements
section, and a rewritten main-results figure (8-model heatmap, corrected
CGSV slopegraph, corrected verifier forest plot with the magnetism
retraction visible).

Root `matpcr_snjnl.tex` (835 lines) is **intentionally left stale** — old
numbers, no Baselines section, no SI table — per an explicit user decision
not to overwrite it this pass. Any future submission attempt must build from
`VERSION2/`, not root, or must explicitly reconcile the two.

`matpcr_cover_letter.txt` updated to match VERSION2's title and current
framing; still has `[AUTHOR: ...]` placeholders for the submission date and
ORCIDs.

---

## 9. What's still open (the actual "what's left" list)

**Needs a human, cannot be automated:**
1. Mustafa's DFT-protocol sign-off (review pages/provenance ready).
2. Manual re-review of the 3 DFT Half-B pages
   (`experiments/halfB_review_dft_{stability,metallicity,magnetism}.html`)
   — unblocks Table 1's 3 pending precision cells.
3. A second human reviewer for EX6 (Cohen's κ) — harness ready, no second
   person has done the review pass.
4. 2–3 independent human mock reviews of the manuscript.
5. Author-only manuscript fields (funding, grant numbers, GPU-hours, both
   ORCIDs, submission date).
6. A fresh arXiv novelty search right before submission (time-sensitive).

**Real work, not blocked, just not done yet:**
7. Holm/Benjamini–Hochberg multiple-comparisons correction across the
   144-cell sweep + 4 CGSV comparisons (flagged in the manuscript as owed).
8. GPT-4o's persistent low-n spectrum anomaly — reproduced 7+ times, never
   root-caused.
9. Gemini's magnetism-prompt token-budget truncation — root cause diagnosed,
   fix not applied.
10. A genuine verifier-as-best-of-N-selector comparison (needs
    `exp7_cgsv_controls.py` extended to persist each candidate's chain text).
11. Every `% VERIFY`-tagged citation (40 in root `.bib`, 6 in VERSION2's) —
    read against the real source before trusting the author list.

**Mechanical / infrastructure:**
12. Recompile on Overleaf with the official (non-patched) `sn-jnl` class.
13. Decide what to do about root vs. `VERSION2/matpcr_snjnl.tex` before
    submission.
14. **New, surfaced by this reproducibility audit**: write an actual
    `requirements.txt`/environment lockfile (the `emmet-core==0.85.1` pin
    and the MatterChat venv's pinned stack currently exist only as prose)
    and consider pushing the verifier weights to a public repo now, since
    the exact trained files cannot be regenerated identically once
    training is re-run (only equivalent performance can be recovered).
