# Best/worst real fired cases, per modality

Six 2x2 figures, one per oracle family. Each shows two "best" (closest/most
subtle) and two "worst" (most egregious) real, human-confirmed fired cases,
selected by resolving every case's exact recorded `source_file` against the
currently-staged data and re-measuring the actual claim-vs-truth gap — not
eyeballed, not the first four cases in file order.

- `sample_xrd_best_worst` — best = smallest |claimed - true apex 2theta|
  (Δ=0.18-0.19°); worst = largest gap against a genuine resolved local-max
  peak (Δ=14.7-16.4°), not a raw global-max artifact (an earlier pass
  mistakenly used raw `argmax`, which for two candidate cases picked a
  baseline-decay tail or a wrong same-named file from another opXRD
  institution folder — both traced and fixed by resolving the *exact*
  `source_file` from `experiments/halfB_fired_cases.jsonl` rather than a
  glob across institutions).
- `sample_sem_best_worst` — best = claimed size closest to a plausible
  in-frame reading (~100 nm against a real 1 µm scale bar); worst = claimed
  size 15-100x the true field of view.
- `sample_spectrum_best_worst` — best = smallest |claimed - true apex
  Raman shift| (Δ=0.1-1.8 cm⁻¹); worst includes one claim (1750 cm⁻¹) that
  falls entirely outside the plotted spectrum's real measured range
  (91.6-1284.8 cm⁻¹) — the model stated a value the plot never showed.
- `sample_stability_best_worst` — best = real hull energy within ~0.002
  eV/atom of the 0.05 eV/atom tolerance boundary (a defensible near-miss);
  worst = real hull energy 11-25x the tolerance (an unambiguous miss).
- `sample_metallicity_best_worst` — best = real band gap within ~0.07 eV of
  the 0.20 eV abstention-band edge; worst = real band gap 3.5-4.5 eV (a
  clear insulator) claimed metallic.
- `sample_magnetism_best_worst` — best = real total_magnetization exactly
  zero (clean, but a case with no partial-moment ambiguity to hint at);
  worst = real moment 32-110 muB (large, unmistakable) claimed nonmagnetic.

All source data: `experiments/halfB_fired_cases.jsonl` /
`experiments/halfB_dft_fired_cases.jsonl` and the corresponding
`experiments/halfB_review_*.html` pages (real images/reasoning chains
embedded there). Real opXRD/RRUFF files resolved via
`experiments/exp17_rebuild_review_images.py`'s `resolve_source()`.

Reproducible from `experiments/exp20_best_worst_samples.py` — run directly
against the repo (with `MATPCR_DATA_ROOT` set) to regenerate all six figures
from scratch; confirmed to reproduce byte-equivalent output during
development.
