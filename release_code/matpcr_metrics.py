"""
matpcr_metrics.py
=================
Reference implementation of the quantities used in the MatPCR paper:

  * Modality-specific PHYSICAL CONSTRAINT CHECKERS (label-free oracles)
      - XRD: Bragg's-law d-spacing / 2-theta peak consistency
      - SEM/TEM: scale-bar geometric sanity for reported feature sizes
      - Spectra (Raman/IR/XRD-as-curve): reported peak must exist in the signal
  * PHYSICAL-CONSISTENCY RATE (PCR) and per-constraint violation rates
  * Bootstrap confidence intervals (numpy only)
  * Paired significance test for CGSV (before vs. after self-verification):
      exact McNemar test on discordant pairs
  * Detector AUC: does an internal flag (e.g., verifier-fired / model
      uncertainty) predict an actual physical-constraint violation?

DESIGN RULES
------------
* numpy-only.
* This module COMPUTES quantities from inputs. It NEVER asserts a fabricated
  experimental outcome. The smoke test at the bottom builds *synthetic* model
  outputs with a known, planted error rate and shows the estimators recover it;
  it is a correctness demo, not a result.

Run the smoke test:
    python3 matpcr_metrics.py
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

# ----------------------------------------------------------------------------
# Physical constants / conventions
# ----------------------------------------------------------------------------
CU_KALPHA_ANGSTROM = 1.5406  # Cu K-alpha1 wavelength; the dominant lab source.


# ----------------------------------------------------------------------------
# 1. Modality-specific physical-constraint checkers (the label-free oracles)
# ----------------------------------------------------------------------------
def two_theta_to_d(two_theta_deg: float, wavelength: float = CU_KALPHA_ANGSTROM) -> float:
    """Bragg's law: lambda = 2 d sin(theta)  ->  d = lambda / (2 sin(theta))."""
    theta = math.radians(two_theta_deg / 2.0)
    s = math.sin(theta)
    if s <= 0:
        return float("inf")
    return wavelength / (2.0 * s)


def xrd_peak_consistent(
    claimed_two_theta_deg: float,
    reference_two_thetas_deg: Sequence[float],
    tol_deg: float = 0.5,
    two_theta_window=(5.0, 90.0),
) -> bool:
    """A claimed XRD peak is physically consistent iff it (a) lies in a
    physically realizable 2-theta window for the stated source and (b) matches
    a reference peak (computed from a public CIF) within tolerance.

    reference_two_thetas_deg comes from a structure's simulated pattern, so this
    needs NO human annotation.
    """
    lo, hi = two_theta_window
    if not (lo <= claimed_two_theta_deg <= hi):
        return False
    if len(reference_two_thetas_deg) == 0:
        return False
    diffs = np.abs(np.asarray(reference_two_thetas_deg, float) - claimed_two_theta_deg)
    return bool(diffs.min() <= tol_deg)


def sem_feature_size_consistent(
    claimed_feature_nm: float,
    scale_bar_nm: float,
    scale_bar_px: float,
    image_px_long_edge: float,
    max_fraction_of_fov: float = 1.0,
) -> bool:
    """A reported feature size on a micrograph is physically impossible if it
    exceeds the field of view implied by the scale bar. nm-per-pixel is fixed by
    (scale_bar_nm / scale_bar_px); the FOV long edge in nm is that times the
    image's long-edge pixel count. No labels required: the scale bar is in the
    image and its pixel length is measured programmatically.
    """
    if scale_bar_px <= 0 or scale_bar_nm <= 0 or image_px_long_edge <= 0:
        return False
    nm_per_px = scale_bar_nm / scale_bar_px
    fov_nm = nm_per_px * image_px_long_edge
    if claimed_feature_nm <= 0:
        return False
    return claimed_feature_nm <= max_fraction_of_fov * fov_nm


def spectrum_peak_exists(
    claimed_peak_x: float,
    signal_x: np.ndarray,
    signal_y: np.ndarray,
    x_tol: float,
    prominence_frac: float = 0.05,
) -> bool:
    """A claimed spectral peak (Raman shift / wavenumber / 2-theta) is consistent
    iff there is a GENUINE local maximum near it (higher than both adjacent
    flanks down to their nearest valleys) whose prominence above the higher
    adjacent valley exceeds a fraction of the signal's dynamic range. Ground
    truth is the signal itself: label-free.

    Requires an actual interior local maximum, not just the tallest point in
    the tolerance window -- a monotonic rise or a shoulder on the flank of a
    nearby peak has no real apex near the claim and must be rejected, which a
    plain "max of windowed points minus global median" check does not do.
    """
    signal_x = np.asarray(signal_x, float)
    signal_y = np.asarray(signal_y, float)
    n = signal_x.size
    if n < 3:
        return False
    rng = float(signal_y.max() - signal_y.min())
    if rng <= 0:
        return False
    idx = np.where(np.abs(signal_x - claimed_peak_x) <= x_tol)[0]
    if idx.size == 0:
        return False
    # Consider windowed points from highest to lowest; accept the first genuine
    # interior local maximum whose prominence above the higher adjacent valley
    # clears the threshold.
    for k in sorted(idx.tolist(), key=lambda j: -signal_y[j]):
        if k <= 0 or k >= n - 1:
            continue
        if not (signal_y[k] > signal_y[k - 1] and signal_y[k] > signal_y[k + 1]):
            continue  # not a strict local maximum (rejects monotonic rise / shoulder)
        li = k
        while li > 0 and signal_y[li - 1] <= signal_y[li]:
            li -= 1  # walk down the left flank to the adjacent valley
        ri = k
        while ri < n - 1 and signal_y[ri + 1] <= signal_y[ri]:
            ri += 1  # walk down the right flank to the adjacent valley
        base = max(float(signal_y[li]), float(signal_y[ri]))
        if (float(signal_y[k]) - base) >= prominence_frac * rng:
            return True
    return False


# ----------------------------------------------------------------------------
# 2. PCR and per-constraint violation rates
# ----------------------------------------------------------------------------
@dataclass
class ItemResult:
    """One benchmark item after checking the model's reasoning chain.

    consistent: True if EVERY physical constraint extracted from the chain held.
    n_checks:   number of physical constraints the chain made checkable.
    n_violations: number that failed.
    constraint_type: e.g. 'xrd_peak', 'sem_scale', 'spectrum_peak'.
    flagged: an internal signal (verifier fired / high model uncertainty) used
             only for the detector-AUC analysis.
    """
    consistent: bool
    n_checks: int
    n_violations: int
    constraint_type: str
    flagged: bool = False


def physical_consistency_rate(items: Sequence[ItemResult]) -> float:
    """PCR = fraction of items whose reasoning chain has zero physical-constraint
    violations among items that exposed at least one checkable constraint."""
    checkable = [it for it in items if it.n_checks > 0]
    if not checkable:
        return float("nan")
    return float(np.mean([it.consistent for it in checkable]))


def violation_rate_by_type(items: Sequence[ItemResult]) -> dict:
    """Per-constraint-type violation rate = violations / checks aggregated by type."""
    out = {}
    types = sorted({it.constraint_type for it in items if it.n_checks > 0})
    for t in types:
        checks = sum(it.n_checks for it in items if it.constraint_type == t)
        viol = sum(it.n_violations for it in items if it.constraint_type == t)
        out[t] = float(viol) / checks if checks else float("nan")
    return out


# ----------------------------------------------------------------------------
# 3. Bootstrap confidence intervals
# ----------------------------------------------------------------------------
def bootstrap_ci(
    values: Sequence[float],
    n_boot: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple:
    """Percentile bootstrap CI for the mean of a 0/1 (or real) array."""
    rng = np.random.default_rng(seed)
    v = np.asarray(values, float)
    if v.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    means = np.empty(n_boot)
    n = v.size
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        means[b] = v[idx].mean()
    lo = float(np.quantile(means, alpha / 2))
    hi = float(np.quantile(means, 1 - alpha / 2))
    return (float(v.mean()), lo, hi)


# ----------------------------------------------------------------------------
# 4. Paired significance test for CGSV (before vs after self-verification)
# ----------------------------------------------------------------------------
def mcnemar_exact(before_consistent: Sequence[bool], after_consistent: Sequence[bool]) -> dict:
    """Exact McNemar test on the same items before and after CGSV.

    b = #(before consistent, after inconsistent)   [regressions]
    c = #(before inconsistent, after consistent)   [fixes]
    Two-sided exact p-value from Binomial(b+c, 0.5).
    """
    before = np.asarray(before_consistent, bool)
    after = np.asarray(after_consistent, bool)
    assert before.shape == after.shape
    b = int(np.sum(before & ~after))
    c = int(np.sum(~before & after))
    n = b + c
    if n == 0:
        return {"b_regressions": b, "c_fixes": c, "p_value": 1.0}
    k = min(b, c)
    # two-sided exact binomial p
    p = 0.0
    for i in range(0, k + 1):
        p += math.comb(n, i) * (0.5 ** n)
    p = min(1.0, 2.0 * p)
    return {"b_regressions": b, "c_fixes": c, "p_value": float(p)}


def holm_bonferroni(p_values: Sequence[float]) -> list:
    """Holm-Bonferroni step-down correction (FWER control).

    Returns adjusted p-values in the SAME order as the input. Adjusted
    p-value for the i-th smallest raw p is max over all j<=i of
    p_(j) * (m - j + 1), enforced monotone non-decreasing (the running-max
    step), then clipped to 1.0.
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = p[idx] * (m - rank)
        running_max = max(running_max, val)
        adjusted[idx] = min(running_max, 1.0)
    return adjusted.tolist()


def benjamini_hochberg(p_values: Sequence[float]) -> list:
    """Benjamini-Hochberg step-up correction (FDR control).

    Returns adjusted p-values (q-values) in the SAME order as the input.
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adjusted = np.empty(m)
    running_min = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        val = p[idx] * m / (rank + 1)
        running_min = min(running_min, val)
        adjusted[idx] = running_min
    return adjusted.tolist()


# ----------------------------------------------------------------------------
# 5. Detector AUC: does an internal flag predict an actual violation?
# ----------------------------------------------------------------------------
def roc_auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """AUC via the Mann-Whitney U statistic. labels: 1 = violation, 0 = clean.
    'scores' is the flag strength (higher = more suspected violation)."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, int)
    pos = s[y == 1]
    neg = s[y == 0]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, s.size + 1)
    # average ranks for ties
    _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.zeros(counts.size)
    np.add.at(sums, inv, ranks)
    avg = sums / counts
    ranks = avg[inv]
    r_pos = ranks[y == 1].sum()
    auc = (r_pos - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size)
    return float(auc)


# ----------------------------------------------------------------------------
# 6. DFT-grounded oracles (label-free: reference is a computed value)
# ----------------------------------------------------------------------------
def stability_claim_consistent(
    claimed_stable: bool,
    e_above_hull_eV_atom: float,
    tol_eV_atom: float = 0.05,
) -> bool:
    """A 'stable' claim is consistent iff the computed energy above the convex
    hull is within tolerance of the hull; an 'unstable' claim is consistent iff
    it is clearly above. e_above_hull comes from a DFT reference (public DB or a
    pinned in-house protocol), so no human label is needed.

    Per the domain co-author's review (M.K., 2026-07): 0.05 eV/atom is a
    reasonable near-hull tolerance, but a structure between 0 and tol_eV_atom
    should be DESCRIBED as "near-hull" or "potentially metastable," never as
    strictly thermodynamically stable -- that framing is a manuscript-text
    obligation, not something this function enforces. Report sensitivity of
    any downstream rate to tol_eV_atom in {0, 0.025, 0.05, 0.10} rather than
    the single default value alone.
    """
    is_actually_stable = e_above_hull_eV_atom <= tol_eV_atom
    return bool(claimed_stable) == bool(is_actually_stable)


STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM = (0.0, 0.025, 0.05, 0.10)


def metallicity_claim_consistent(
    claimed_metallic: bool,
    band_gap_eV: float,
    metal_max_eV: float = 0.05,
    gap_min_eV: float = 0.20,
):
    """A 'metallic' claim is consistent iff the computed band gap is ~zero.

    Because semilocal DFT underestimates band gaps, metallicity decisions are
    restricted to clearly gapped or clearly gapless cases: a gap at or below
    ``metal_max_eV`` is treated as computed-metallic, a gap at or above
    ``gap_min_eV`` as computed-non-metallic, and the ambiguous band in between
    returns ``None`` so the item is EXCLUDED rather than forced into a
    functional-error-sensitive decision. Callers treat ``None`` as "not
    checkable" (contributes no constraint to PCR).

    Thresholds are the domain co-author's (M.K., 2026-07) exact recommendation
    (<=0.05 eV computed-metallic, 0.05-0.20 eV ambiguous/abstain, >=0.20 eV
    computed-non-metallic), given explicitly to avoid "pretending that one
    threshold can remove the known semilocal-DFT band-gap error." Even outside
    the ambiguous band, some real small-gap semiconductors may still be
    predicted gapless by the functional; the abstention band mitigates but
    does not eliminate this (silicon, mp-149, remains safely non-metallic at
    a computed 0.61 eV, well clear of gap_min_eV).
    """
    if band_gap_eV <= metal_max_eV:
        is_actually_metallic = True
    elif band_gap_eV >= gap_min_eV:
        is_actually_metallic = False
    else:
        return None  # ambiguous gap in the functional-error dead zone: excluded
    return bool(claimed_metallic) == bool(is_actually_metallic)


def magnetism_magnitude_consistent(
    claimed_magnetic: bool,
    claimed_magnitude: "float | None",
    total_magnetization_muB: float,
    n_atoms: int,
    magnetic_threshold_muB_per_atom: float = 0.05,
    rel_tol: float = 1.0,
) -> "bool | None":
    """Renamed from 'sign/magnitude' per the domain co-author's review (M.K.,
    2026-07): total magnetization must NOT be treated as a signed quantity.
    Its sign can reverse under an equivalent global spin reversal (an
    arbitrary choice of "up" in a DFT calculation, not a physical claim a
    model could be right or wrong about), and an order-of-magnitude ratio is
    undefined near zero. The corrected protocol, exactly as specified:

      1. Normalize to |total_magnetization| PER ATOM (never signed, never
         un-normalized -- comparing raw total moments across cells of
         different sizes is not physically meaningful either).
      2. Classify magnetic vs. non-magnetic FIRST, using a small
         preregistered threshold on that per-atom magnitude
         (magnetic_threshold_muB_per_atom).
      3. Only within the magnetic class, compare MAGNITUDE (never sign) to
         the DFT reference, within an order-of-magnitude band (rel_tol=1.0
         means [ref/10, ref*10]).

    Parameters
    ----------
    claimed_magnetic: the model's binary MAGNETIC/NONMAGNETIC claim.
    claimed_magnitude: the model's stated |magnetization|/atom, or None if the
        chain only exposed the binary claim (magnitude check is skipped, and
        this function evaluates the classification claim only).
    total_magnetization_muB: DFT reference total magnetization in Bohr
        magnetons (raw, NOT yet normalized -- normalization happens here).
    n_atoms: number of atoms in the reference cell, for per-atom normalization.

    Returns True/False for a checkable claim, or None if n_atoms is not a
    positive integer (not checkable -- contributes no constraint to PCR).
    """
    if not n_atoms or n_atoms <= 0:
        return None
    ref_magnitude_per_atom = abs(total_magnetization_muB) / n_atoms
    is_actually_magnetic = ref_magnitude_per_atom >= magnetic_threshold_muB_per_atom
    if bool(claimed_magnetic) != bool(is_actually_magnetic):
        return False
    if not is_actually_magnetic or claimed_magnitude is None:
        return True  # classification alone is checkable and it matched
    ratio = abs(claimed_magnitude) / ref_magnitude_per_atom
    return (10 ** (-rel_tol)) <= ratio <= (10 ** rel_tol)


# ----------------------------------------------------------------------------
# 7. Verifier evaluation: predicted-violation vs oracle-violation
# ----------------------------------------------------------------------------
def cohens_kappa(rater_a: Sequence[str], rater_b: Sequence[str]) -> float:
    """Cohen's kappa for inter-rater agreement between two independent human
    reviewers labeling the same items (e.g. Half-B fired-case verdicts:
    "real" / "false_positive" / "unsure"). Corrects raw percent agreement
    for the agreement expected by chance given each rater's own label
    distribution -- needed because two reviewers can agree 80% of the time
    trivially if one label dominates the population, which raw agreement
    alone would not reveal.

    kappa = (p_o - p_e) / (1 - p_e), where p_o is observed agreement and
    p_e is chance agreement under each rater's marginal label distribution.
    """
    a = list(rater_a)
    b = list(rater_b)
    if len(a) != len(b):
        raise ValueError("rater_a and rater_b must have the same length (same items, same order)")
    n = len(a)
    if n == 0:
        return float("nan")
    labels = sorted(set(a) | set(b))
    p_o = sum(1 for x, y in zip(a, b) if x == y) / n
    p_e = 0.0
    for lab in labels:
        p_a = sum(1 for x in a if x == lab) / n
        p_b = sum(1 for y in b if y == lab) / n
        p_e += p_a * p_b
    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else float("nan")
    return (p_o - p_e) / (1 - p_e)


def precision_recall_f1(pred: Sequence[int], true: Sequence[int]) -> dict:
    """pred/true are 1 = violation, 0 = clean (true comes from the oracles)."""
    p = np.asarray(pred, int)
    t = np.asarray(true, int)
    tp = int(np.sum((p == 1) & (t == 1)))
    fp = int(np.sum((p == 1) & (t == 0)))
    fn = int(np.sum((p == 0) & (t == 1)))
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec and not math.isnan(prec)
                                             and not math.isnan(rec)) else float("nan")
    return {"precision": prec, "recall": rec, "f1": f1}


def expected_calibration_error(probs: Sequence[float], true: Sequence[int],
                               n_bins: int = 10) -> float:
    """ECE for the verifier's predicted violation probability."""
    p = np.asarray(probs, float)
    t = np.asarray(true, int)
    if p.size == 0:
        return float("nan")
    edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        m = (p > edges[i]) & (p <= edges[i + 1]) if i > 0 else (p >= edges[i]) & (p <= edges[i + 1])
        if m.sum() == 0:
            continue
        conf = p[m].mean()
        acc = t[m].mean()
        ece += (m.sum() / p.size) * abs(conf - acc)
    return float(ece)


# ----------------------------------------------------------------------------
# SMOKE TEST  (synthetic; demonstrates expected behavior, asserts no result)
# ----------------------------------------------------------------------------
def _smoke_test() -> None:
    rng = np.random.default_rng(42)
    print("=" * 70)
    print("MatPCR metrics smoke test (synthetic data; NOT an experimental result)")
    print("=" * 70)

    # --- checker unit checks against known physics ---
    d = two_theta_to_d(28.44)  # Si(111)-ish
    print(f"[checker] 2theta=28.44 deg -> d={d:.4f} A (expected ~3.13 A)")
    assert abs(d - 3.13) < 0.05

    refs = [28.44, 47.30, 56.12]
    assert xrd_peak_consistent(28.5, refs, tol_deg=0.5) is True
    assert xrd_peak_consistent(33.0, refs, tol_deg=0.5) is False
    assert xrd_peak_consistent(120.0, refs) is False  # outside window
    print("[checker] xrd_peak_consistent: in-window match=OK, mismatch=OK, "
          "out-of-window=OK")

    # 100 nm bar = 50 px -> 2 nm/px; 1024 px long edge -> FOV 2048 nm
    assert sem_feature_size_consistent(500, 100, 50, 1024) is True
    assert sem_feature_size_consistent(5000, 100, 50, 1024) is False  # > FOV
    print("[checker] sem_feature_size_consistent: in-FOV=OK, impossible=OK")

    x = np.linspace(100, 2000, 2000)
    y = np.exp(-((x - 1350) ** 2) / (2 * 25 ** 2))  # peak at 1350 (G band-like)
    assert spectrum_peak_exists(1350, x, y, x_tol=10) is True
    assert spectrum_peak_exists(800, x, y, x_tol=10) is False
    print("[checker] spectrum_peak_exists: real peak=OK, absent peak=OK")

    # --- Cohen's kappa: perfect agreement, chance-level, and a planted case ---
    perfect_a = ["real", "false_positive", "real", "real", "false_positive"]
    assert abs(cohens_kappa(perfect_a, perfect_a) - 1.0) < 1e-9
    # Two raters who agree exactly as often as their marginals predict by
    # chance should score kappa~=0 -- constructed directly, not estimated.
    rater_a = ["real"] * 50 + ["false_positive"] * 50
    rater_b = ["real"] * 25 + ["false_positive"] * 25 + ["real"] * 25 + ["false_positive"] * 25
    k = cohens_kappa(rater_a, rater_b)
    assert -0.05 < k < 0.05
    print(f"[checker] cohens_kappa: perfect agreement=OK (kappa=1.0), chance-level=OK (kappa={k:.3f})")

    # --- PCR / violation-rate recovery on a planted error rate ---
    n = 1200
    true_viol_p = 0.30  # planted: 30% of chains contain a physical violation
    items = []
    for _ in range(n):
        ctype = rng.choice(["xrd_peak", "sem_scale", "spectrum_peak"])
        violated = rng.random() < true_viol_p
        items.append(ItemResult(
            consistent=not violated,
            n_checks=1,
            n_violations=int(violated),
            constraint_type=ctype,
            # internal flag correlates with violation (planted AUC ~0.8)
            flagged=bool(rng.random() < (0.75 if violated else 0.20)),
        ))
    pcr = physical_consistency_rate(items)
    mean, lo, hi = bootstrap_ci([it.consistent for it in items if it.n_checks > 0],
                                n_boot=2000, seed=1)
    print(f"\n[PCR] planted consistency={1-true_viol_p:.2f}; "
          f"estimated PCR={pcr:.3f}  95% CI [{lo:.3f}, {hi:.3f}]")
    assert abs(pcr - (1 - true_viol_p)) < 0.05

    vbt = violation_rate_by_type(items)
    print("[violation rate by type]", {k: round(v, 3) for k, v in vbt.items()})

    # --- CGSV before/after with planted fix>regression, McNemar ---
    before = np.array([it.consistent for it in items])
    after = before.copy()
    inconsistent_idx = np.where(~before)[0]
    fixed = rng.random(inconsistent_idx.size) < 0.45  # CGSV fixes 45% of violations
    after[inconsistent_idx[fixed]] = True
    consistent_idx = np.where(before)[0]
    regressed = rng.random(consistent_idx.size) < 0.03  # small regression
    after[consistent_idx[regressed]] = False
    mc = mcnemar_exact(before, after)
    print(f"\n[CGSV McNemar] fixes(c)={mc['c_fixes']} "
          f"regressions(b)={mc['b_regressions']} p={mc['p_value']:.2e}")
    print(f"[CGSV] PCR before={before.mean():.3f}  after={after.mean():.3f}")

    # --- multiple-comparisons correction (Holm, Benjamini-Hochberg) ---
    raw_p = [0.001, 0.02, 0.03, 0.5, 0.9]
    holm_adj = holm_bonferroni(raw_p)
    bh_adj = benjamini_hochberg(raw_p)
    # Both corrections must never REDUCE a p-value below its raw value.
    assert all(h >= r - 1e-12 for h, r in zip(holm_adj, raw_p))
    assert all(b >= r - 1e-12 for b, r in zip(bh_adj, raw_p))
    # Holm is at least as conservative as BH pointwise (Holm controls FWER,
    # a stricter criterion than BH's FDR).
    assert all(h >= b - 1e-12 for h, b in zip(holm_adj, bh_adj))
    # A p-value of exactly 1.0 must stay at 1.0 under both.
    assert abs(holm_bonferroni([1.0, 0.5])[0] - 1.0) < 1e-12
    assert abs(benjamini_hochberg([1.0, 0.5])[0] - 1.0) < 1e-12
    print(f"\n[multiplicity] raw p={raw_p}")
    print(f"[multiplicity] Holm-adjusted={[f'{x:.4f}' for x in holm_adj]}")
    print(f"[multiplicity] BH-adjusted  ={[f'{x:.4f}' for x in bh_adj]}")

    # --- detector AUC ---
    scores = np.array([1.0 if it.flagged else 0.0 for it in items])
    # add jitter so AUC is not degenerate on a binary flag
    scores = scores + rng.normal(0, 0.1, scores.size)
    labels = np.array([it.n_violations for it in items])
    auc = roc_auc(scores, labels)
    print(f"\n[detector AUC] verifier-flag predicts violation: AUC={auc:.3f} "
          f"(planted to be well above 0.5)")
    assert auc > 0.6

    # --- DFT-grounded oracle unit checks ---
    assert stability_claim_consistent(True, 0.01) is True       # near hull, called stable
    assert stability_claim_consistent(True, 0.30) is False      # above hull, called stable
    assert metallicity_claim_consistent(False, 1.8) is True     # gapped, called non-metal
    assert metallicity_claim_consistent(True, 1.8) is False     # gapped, called metal
    assert metallicity_claim_consistent(True, 0.02) is True     # deep in metallic band
    assert metallicity_claim_consistent(True, 0.12) is None     # ambiguous dead zone: excluded
    assert metallicity_claim_consistent(False, 0.61) is True    # silicon-like, safely non-metallic
    # magnetism: classification-only claim (claimed_magnitude=None)
    assert magnetism_magnitude_consistent(True, None, 2.0, 1) is True    # 2 muB/atom, called magnetic
    assert magnetism_magnitude_consistent(False, None, 2.0, 1) is False  # magnetic, called non-magnetic
    assert magnetism_magnitude_consistent(False, None, 1e-7, 1) is True  # ~0 muB/atom, called non-magnetic
    # magnetism: classification + magnitude claim, sign of the claim must be ignored
    assert magnetism_magnitude_consistent(True, 2.1, 2.0, 1) is True     # right ballpark, magnitude only
    assert magnetism_magnitude_consistent(True, -2.1, 2.0, 1) is True    # sign is irrelevant, still consistent
    assert magnetism_magnitude_consistent(True, 0.05, 2.0, 1) is False   # magnitude off by >10x
    print("[DFT oracle] stability / metallicity / magnetism-magnitude checks: OK")

    # --- verifier evaluation on a planted predictor ---
    true_lab = np.array([it.n_violations for it in items])
    # planted verifier: probability higher on true violations
    probs = np.where(true_lab == 1,
                     rng.uniform(0.55, 0.95, true_lab.size),
                     rng.uniform(0.05, 0.45, true_lab.size))
    pred = (probs >= 0.5).astype(int)
    prf = precision_recall_f1(pred, true_lab)
    ece = expected_calibration_error(probs, true_lab)
    print(f"[verifier] precision={prf['precision']:.3f} recall={prf['recall']:.3f} "
          f"F1={prf['f1']:.3f}  ECE={ece:.3f}  (planted to be strong)")
    assert prf["f1"] > 0.6

    print("\nAll smoke-test checks passed. These are synthetic demonstrations of"
          "\nestimator behavior, not measured model results.")


if __name__ == "__main__":
    _smoke_test()
