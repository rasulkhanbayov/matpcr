# MatPCR revision plan — response to supervisor review + Dr. Mustafa's comments

Created 2026-07-16, from `VERSION2/matpcr_REDFLAGS.txt` (supervisor's deep audit)
and `VERSION2/Dr_mustafas_comments` (DFT co-author's approval-with-conditions).
Execution mode: proceed through all phases autonomously, report at each
milestone (Phase 0 done, Phase 1 done, Phase 2 done, Phase 3 done).

## Independent verification done before trusting the audit (2026-07-16)

- **BL1 (seed pseudoreplication) claim is factually wrong as literally stated.**
  The audit says "S=3 seeds run on the same 30 items." Checked directly
  against real data (`experiments/exp4_results.jsonl`, 555 records): **0**
  duplicate source files across any seed in any (modality, model) cell.
  Seeds draw a fresh random sample via `seed=BASE + seed*100` in the item
  builders — a genuinely different subset each time, not the same items
  redecoded. The audit's specific mechanism does not apply here. The deeper
  concern (correct unit of analysis; watch for incidental overlap; multiple
  claims per chain) still gets addressed in Phase 1, just not via the fix the
  audit describes.
- **BL2 (verifier split leakage) is real.** `exp5_build_dataset.py` drops the
  `source_file` identifier when flattening `halfB_fired_cases.jsonl` into
  `exp5_verifier_dataset.jsonl` — disjointness can't even be verified post
  hoc. Must rebuild with provenance retained, then re-split.
- **Found independently (not in the audit):** `exp2_results.jsonl` and
  `exp3_results.jsonl` never recorded a source/item ID at all (only exp4's
  did). Item-level re-analysis of Experiments 2 and 3 requires re-running
  them with an ID added, not just re-aggregating existing files.
- **Confirmed current-gen models are reachable** on the existing OpenRouter
  key with $699 of $700 budget remaining: `anthropic/claude-opus-4.6`,
  `openai/gpt-5.6-terra`, `qwen/qwen3-vl-8b-instruct`,
  `qwen/qwen3-vl-8b-thinking`. Selected per user decision 2026-07-16.
- **Metallicity ambiguous band: use Mustafa's literal 0.05–0.20 eV**, not
  VERSION2 code's inherited default of `gap_min_eV=0.3` (user decision).
- **Not executable by me alone: EX6's second human annotator / Cohen's kappa.**
  I can build the second-review harness; the human judgment itself needs
  another person. Flagged, not silently dropped.

---

## Phase 0 — Oracle/code corrections (blocks everything downstream)

- [ ] 1. Magnetism oracle redesign (Mustafa, mandatory): replace signed
      comparison with magnetic-vs-not classification via a small
      preregistered threshold on `|total_magnetization|`/atom, then magnitude
      comparison only within the magnetic class. Rename "sign/magnitude" →
      "magnetism magnitude" everywhere (code, callers, manuscript).
- [ ] 2. Stability: add sensitivity reporting at {0, 0.025, 0.05, 0.10}
      eV/atom. Reframe 0–0.05 as "near-hull/metastable," never "stable."
- [ ] 3. Metallicity dead-zone: ≤0.05 eV metallic, 0.05–0.20 eV excluded
      (ambiguous), ≥0.20 eV non-metallic — Mustafa's literal thresholds.
- [ ] 4. Spectrum oracle: adopt VERSION2's genuine-local-maximum fix (rejects
      monotonic rise/shoulder, requires a real interior local max with
      defined prominence).
- [ ] 5. Pin MP provenance (DB/API version, retrieval date, calc type, exact
      fields). Describe MP values as "standardized computational reference,"
      never "experimental ground truth," throughout.
- [ ] 6. Re-run `python3 matpcr_metrics.py` smoke test after all changes;
      confirm it still passes before touching any experiment script.

## Phase 1 — Re-run affected experiments on corrected oracles

- [ ] 7. Re-run DFT Half-A (positive control) on all 3 corrected DFT oracles.
- [ ] 8. Re-run DFT Half-B collection (I collect + parse; manual precision
      judgment follows the same division of labor as before).
- [ ] 9. Re-run Experiment 2 (PCR sweep), adding a source/item ID to every
      record, on corrected oracles, all 6 constraint types.
- [ ] 10. Re-run Experiment 3 (accuracy-vs-consistency), adding a source/item
      ID, on corrected oracles; add balanced accuracy / class-conditional
      rates for the stability arm.
- [ ] 11. Re-run Experiment 4 (CGSV) on corrected oracles; add checkable-claim
      counts k_i before/after per chain (BL4 — separates correction from
      retraction).
- [ ] 12. Rebuild `exp5_verifier_dataset.jsonl` with provenance retained;
      re-split in-distribution train/test disjoint at the source level;
      retrain all 13 verifier runs; re-run Experiment 6's detector bootstrap
      CIs on the new scores.
- [ ] 13. Item-level (not record-level) McNemar p-values and bootstrap CIs
      everywhere: aggregate to one value per item first, cluster by parent
      source where items share one.
- [ ] 14. Multiple-comparisons correction (Holm/Benjamini-Hochberg) across the
      full sweep and the 4 CGSV comparisons; effect sizes with CIs alongside
      every p-value.

## Phase 2 — New experiments the venue will expect

- [ ] 15. Model refresh (EX3/EX4): add `anthropic/claude-opus-4.6`,
      `openai/gpt-5.6-terra` (frontier), `qwen/qwen3-vl-8b-instruct` (current
      open), `qwen/qwen3-vl-8b-thinking` (reasoning-mode) across applicable
      experiments.
- [ ] 16. Domain evaluee (EX5): add a materials-domain model if reachable
      (MatterChat on DFT/structure arms); flag explicitly if unavailable
      rather than skip silently.
- [ ] 17. Verifier baselines (EX1): zero-shot LLM-as-judge, model
      self-confidence/log-prob, and an off-the-shelf PRM if accessible — same
      items, shared metric.
- [ ] 18. CGSV mechanism-isolation controls (EX2): unaided self-refine (no
      oracle), generic re-prompting at equal compute, best-of-N with/without
      verifier as selector.
- [ ] 19. Tolerance/prompt sensitivity sweep (EX7): show rankings survive
      reasonable tolerance changes; extend beyond stability to XRD/spectrum
      tolerances and prompt wording.
- [ ] 20. Violation taxonomy (EX8): categorize inconsistency types, per-type
      frequency, annotated example chains.
- [ ] 21. Contamination check (EX9): n-gram/perplexity overlap vs. known
      pretraining corpora where checkable; per-family/per-modality item
      counts with provenance table.
- [ ] 22. Detector calibration (EX11): reliability diagrams + a recommended
      operating point per split.
- [ ] 23. Recommended, lower priority (EX12/EX13): downstream utility demo
      (best-of-N reranking or PCR-predicts-failure) and a capability/scaling
      trend, if time/budget allow after 1–22.
- [ ] EX6 (not executable solo): build the second-reviewer harness; flag that
      the human judgment pass itself needs another person.

## Phase 3 — Text-only fixes (interleave with Phase 2 while runs are in flight)

- [ ] 24. Fill pure-missing-text `\redflag{}` items: DFT protocol paragraph
      (functional, cutoff, k-mesh, pseudopotentials, MP version/date),
      decoding config (temperature, top-p, bootstrap B), exact model versions
      + API snapshot dates + experiment date, SI Table S1 (per-cell CIs),
      Acknowledgements funding/compute detail, cover letter date + ORCIDs.
- [ ] 25. Verify each "fixes already applied" item in REDFLAGS section C
      against VERSION2's actual `.tex`/`.py` before treating as done.
- [ ] 26. Reconcile "modality" vs. "constraint type" terminology throughout.

## Final gate (unchanged, still standing)

- [ ] 27. Close the loop with Mustafa once Phase 0 items 1–5 are implemented
      exactly per his wording — confirm his sign-off is satisfied.
- [ ] 28. 2–3 independent human mock reviews.
- [ ] 29. All 40 `% VERIFY` citations in `matpcr_refs.bib` checked against source.
- [ ] 30. Recompile on Overleaf with the official (non-patched) `sn-jnl` class.
