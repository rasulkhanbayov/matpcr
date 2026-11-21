# Labeling guidelines (MatPCR human review, KBS revision)

There are two tasks, each with six pages (one per oracle family) of 30 cases. Read **Part A**
first, then the part for your task.

---

## Part A. Rules for both tasks

1. **Judge the claim, not the reasoning.** Each case has one checkable claim: the value or class in
   the model's `FINAL_ANSWER` line (shown as *Model's claim*). Your question is whether *that claim*
   violates the physical constraint the oracle checks. A sloppy chain with an admissible claim is
   not a violation. A tidy chain with an impossible claim is.
2. **Admissible is not the same as correct.** You are not grading accuracy. A peak position that is
   0.3° from the true apex, or a feature size that is a rough estimate, is *imprecise*, not a
   physical violation. A value that the data or the reference calculation **rules out** is a
   violation.
3. **Check the parser.** Compare *Model's claim* with the `FINAL_ANSWER` line at the end of the
   chain. If they differ (wrong number, unit or class), the oracle judged a value the model never
   stated. Take this into account as described in each task.
4. **Use only what is on the page.** That means the plot or micrograph, the reference values shown,
   and the chain. Don't look up other sources, the first annotator's labels or other cases' answers.
5. **Unsure is for cases that genuinely can't be decided** from the page (for example, an unreadable
   scale bar). Don't use it to avoid a borderline call; borderline cases have explicit rules below.
   Aim for at most 2–3 Unsure per page.
6. **Work alone, in one or two sittings, and label every case.** Unlabelled cases export as `null`.
7. **Exporting.** At the end, press **Export my review**, copy the text box, and save it under the
   file name given in `README.md`.

---

## Part B. Task 1: second annotator (`second_annotator_<family>.html`)

Every case here was **flagged** by the oracle (verdict: INCONSISTENT). Decide whether the flag is
right:

- **Real violation (oracle correct):** the claim genuinely violates the constraint.
- **False positive (oracle wrong):** the claim is in fact admissible. The flag comes from the
  oracle's tolerance, a wrong reference or scale-bar reading, or the parser.
- **Unsure:** see A5.

Parser rule (A3): if the parser misread the claim and the claim the model actually stated is
admissible, mark **False positive**. If the stated claim is also inadmissible, mark **Real**.

### Diffraction (XRD)
- **What the oracle checks.** The claimed 2θ of the strongest peak must lie within **0.5°** of a
  Bragg reflection computed from the sample's labelled structure, and inside the realizable window
  (5–90°).
- **Real:**
  - the claim is clearly not at any peak in the plotted pattern (more than about 1° from every
    visible peak);
  - it sits on flat baseline;
  - it is outside the measured range;
  - it reads the axis wrongly by a large margin (e.g. 3.5° when the peaks are at 25–40°).
- **False positive:**
  - the claim sits on a peak that is visible in the plot, but just outside the 0.5° window (roughly
    0.5–1° from the reference position);
  - the claim is on a clearly real peak in the measured data that the reference pattern simply
    lacks (e.g. an impurity phase).
- **Not a reason for "Real":** the claimed peak is real but not the *strongest* one. That is an
  accuracy error; mark **False positive** if the position is on a genuine peak.

### Microscopy (SEM)
- **What the oracle checks.** The claimed feature size must not exceed the **field of view** implied
  by the burned-in scale bar (scale-bar length in nm ÷ marker length in pixels × image width in
  pixels).
- **Real:** the claimed size really is larger than the whole imaged area. Check the scale bar
  yourself; for example, 100 µm claimed on an image whose 10 µm bar spans a tenth of the width.
- **False positive:**
  - the oracle's scale-bar reading is wrong (you read a different scale-bar value or unit), so the
    claim actually fits in the field of view;
  - the parser took the wrong unit or number.

### Spectra (Raman)
- **What the oracle checks.** A genuine local maximum (higher than both neighbouring valleys) with
  prominence of at least 5% of the spectrum's intensity range must exist within **5 cm⁻¹** of the
  claimed Raman shift.
- **Real:**
  - no peak exists at the claimed position: it is on baseline, on a monotonic rise or fall, or on
    noise;
  - it is outside the plotted range;
  - it is far from any peak.
- **False positive:**
  - the claim sits on a clearly visible real peak (on its apex or within its visible width) but just
    outside the 5 cm⁻¹ window;
  - the claim sits on a small but genuine peak that the 5% prominence rule misses.
- **Not a reason for "Real":** the claimed peak is real but not the *strongest* one. That is an
  accuracy error.

### Stability
- **What the oracle checks.** A STABLE claim is consistent if and only if the Materials Project
  energy above hull is **≤ 0.05 eV/atom** (near-hull). UNSTABLE is consistent if and only if it is
  above.
- **Real:** the claim contradicts the reference clearly, i.e. E_hull is well away from 0.05:
  - STABLE when E_hull ≫ 0.05 (e.g. 0.2 or more);
  - UNSTABLE when E_hull is 0 or tiny.
- **False positive:**
  - the parser misread STABLE/UNSTABLE;
  - E_hull lies within about 0.01 eV/atom of the 0.05 threshold, so the call is a coin-flip of
    definitions;
  - the model says UNSTABLE for 0 < E_hull ≤ 0.05 *and* Materials Project's own `is_stable` flag is
    False. The prompt told models to treat metastable as UNSTABLE, so this is a definition
    mismatch, not a physics error.

### Metallicity
- **What the oracle checks.** METALLIC is consistent if and only if the computed band gap is
  **≤ 0.05 eV**; NONMETALLIC if and only if it is **≥ 0.20 eV**. Materials in between are never
  shown.
- **Real:** the claim contradicts a clearly gapless or clearly gapped reference:
  - METALLIC with a gap of 1 eV or more;
  - NONMETALLIC with a gap of 0.0000 eV.
- **False positive:**
  - the parser misread the class;
  - the gap sits right at a threshold (0.04–0.05 eV, or 0.20–0.25 eV).

### Magnetism
- **What the oracle checks.**
  1. Class: |total magnetization| per atom ≥ **0.05 µB/atom** means magnetic. The prompt asked about
     the **net** moment.
  2. Magnitude: if both the model and the reference say magnetic, the claimed per-atom magnitude
     must be within **one order of magnitude** (a factor of 10) of the reference.
- **Real:**
  - wrong class against a clear reference;
  - a magnitude off by more than 10× with a clear reference;
  - MAGNETIC for a material whose net moment is ~0 because of antiferromagnetic or compensated
    ordering. The question was explicitly about net magnetization, so this counts as Real.
- **False positive:**
  - the parser misread the class or the number;
  - the reference per-atom moment is right at 0.05 µB/atom;
  - the magnitude is borderline at about 10× (e.g. 9–11×) and you judge the claim reasonable.

---

## Part C. Task 2: oracle-silent audit (`oracle_silent_<family>.html`)

Every case here **passed** the oracle (verdict: CONSISTENT). Decide whether the oracle missed a
genuine violation:

- **Missed violation (oracle wrong):** the claim is physically inadmissible even though the oracle
  accepted it.
- **Clean (oracle right):** the claim is admissible. It may still be imprecise, or not the
  strongest peak.
- **Unsure:** see A5.

Parser rule (A3): if the parser misread the claim and the claim the model actually stated is
inadmissible, mark **Missed violation**.

### Diffraction (XRD)
The oracle accepted the claim because a reference Bragg reflection lies within 0.5°.
- **Missed violation:**
  - nothing in the measured pattern is visible at the claimed position, because the matching
    reference reflection is absent or negligible in the real data and the claim sits on baseline;
  - the claim is outside the plotted range.
- **Clean:** the claim is on a real peak of the plot, even if it is not the strongest one, or is a
  few tenths of a degree off the apex.

### Microscopy (SEM)
The oracle accepted the claim because it does not exceed the field of view.
- **Missed violation:** the claimed size is physically impossible for what is shown, given the
  scale bar. For example, the claim is off by 10× or more because of a unit or scale-factor error
  (100 nm claimed for features that are clearly several µm, or the reverse), even though it fits
  inside the field of view.
- **Clean:** the claimed size is roughly compatible with visible features. Estimates within a
  factor of about 2–3 are imprecise, not violations.

### Spectra (Raman)
The oracle accepted the claim because a genuine local maximum with at least 5% prominence lies
within 5 cm⁻¹.
- **Missed violation:** looking at the plot, there is no real peak there. The accepted "maximum" is
  noise, a ripple on a broad background, or an edge artifact.
- **Clean:** there is a real peak at the claimed position, even if it is not the strongest one.

### Stability, Metallicity, Magnetism
The oracle accepted the claim because it agrees with the Materials Project reference under the
rules in Part B. Misses are expected to be rare here.
- **Missed violation:**
  - the parser misread the claim, and the class or magnitude the model actually stated contradicts
    the reference;
  - for magnetism, the oracle accepted NONMAGNETIC (or MAGNETIC with a plausible magnitude) but the
    reference values shown clearly contradict it.
- **Clean:** the stated claim agrees with the reference values shown. This holds even if the
  reasoning is weak, or the reference is near a threshold in the claim's favour.

---

## Part D. Quick reference

| Family | Oracle accepts if… | Typical **Real** / **Missed** | Typical **False positive** / **Clean** |
|---|---|---|---|
| XRD | reference reflection within 0.5° | claim on baseline or far from every peak | claim on a visible peak, 0.5–1° off |
| SEM | claimed size ≤ field of view | size impossible given the scale bar | oracle misread the scale bar; rough estimate |
| Raman | ≥5%-prominence local max within 5 cm⁻¹ | no real peak at that position | on a visible peak just outside 5 cm⁻¹ |
| Stability | STABLE ⇔ E_hull ≤ 0.05 eV/atom | contradicts a reference far from 0.05 | E_hull at threshold; metastable called UNSTABLE |
| Metallicity | METALLIC ⇔ gap ≤ 0.05 eV (≥ 0.20 nonmetallic) | contradicts a clearly (non)metallic gap | gap at a threshold; parser error |
| Magnetism | class at 0.05 µB/atom, magnitude within 10× | wrong class or >10× off (net moment) | moment at threshold; ~10× borderline |
