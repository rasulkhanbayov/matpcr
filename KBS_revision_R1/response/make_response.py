"""Generate the response to reviewers (LaTeX and Markdown -> .docx via pandoc) from one source.

Pending numbers live in PENDING; anything not yet filled is rendered as a red [PENDING: ...] marker,
so the document never silently states a number we have not computed.

Run: python make_response.py   (writes response_to_reviewers.tex and response_to_reviewers.md)
"""

from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEWS = os.path.join(HERE, "..", "reviews", "reviews.md")
PENDING_FILE = os.path.join(HERE, "pending_values.json")

PENDING = json.load(open(PENDING_FILE)) if os.path.exists(PENDING_FILE) else {}


def P(key, desc):
    v = PENDING.get(key)
    return v if v is not None else f"[[PENDING: {desc}]]"


def load_comments():
    txt = open(REVIEWS).read()
    out = {}
    for m in re.finditer(r"\*\*([A-Za-z0-9.]+)\*\*(?: \(strength\))? (.*?)(?=\n\n\*\*|\n\n## |\Z)", txt, re.S):
        out[m.group(1)] = m.group(2).strip()
    return out


C = load_comments()

# ---------------------------------------------------------------------------------------------
# Responses. Text uses a light markup: $...$ math, \emph{...}, and plain text. Locations refer to
# the revised manuscript (sections by name; tables/figures by number).
# ---------------------------------------------------------------------------------------------
RESP = {}

RESP["R1.M1"] = (r"""We agree. Each item exposes one checkable quantity ($k_i=1$), so PCR tests the physical admissibility of a stated quantity, not every inferential step; the abstract, contributions, Introduction and Discussion now say so. We also agree that part of the accuracy-consistency gap is definitional, because the accuracy criteria are tighter than the oracle tolerances, and we no longer present the gap (mean 23.6% on diffraction and spectra) as evidence that PCR catches reasoning errors that accuracy misses. For stability the gap came entirely from near-hull materials, which the final oracle does not score (Reviewer 2, weakness 3). A new paragraph states what PCR adds: it needs no answer key, so it applies where no non-circular accuracy criterion exists (microscopy, magnetization); it is a floor, not a target; and, as a necessary condition, it complements accuracy where labels exist and screens where they do not.""",
                 "Abstract; Key contributions (1); Introduction (last two paragraphs of the gap and positioning text); Results, Accuracy versus consistency (new final paragraph); Discussion.")

RESP["R1.M2"] = (r"""We agree on all three points. (i) The positive control shows completeness on injected violations only. The text now says so, and $\mathrm{PCR}\le\mathrm{PCR}^\star$ is stated as conditional on $\hat d=1$ for real responses. A new audit of 30 oracle-silent responses per family finds 1/30 misses for diffraction, 2/30 for microscopy, 1/30 for spectra and none for the DFT families, an implied recall of 0.81-1.00, lowest for microscopy (Supplementary Table S8). (ii) We grounded the tolerances in the data. The 5 cm$^{-1}$ Raman tolerance spans ten sampling steps but is narrower than a typical peak (median FWHM 16.9 cm$^{-1}$), which is why 34 of 36 false positives lie on a peak flank. The 0.5 degree diffraction tolerance is about four peak widths (median FWHM 0.12 degrees) and is set by what can be read from the plot (3-4 pixels). The diffraction ranking depends on these criteria and is now marked provisional; the spectrum ranking does not. (iii) Every use of the theoretical result is now explicitly conditional, and Table 1 gives intervals for every precision.""",
                 "Results, Oracle validity (first paragraph); Methods, Programmatic geometric oracles (new paragraph on tolerances); Methods, What oracle error does to the reported rate; Table 1; Discussion (limitations).")

RESP["R1.M3"] = (r"""Both points are correct. CGSV stops once no violation remains, so $b=0$ follows from the stopping rule; we now describe it as an implementation check, not a finding. We replaced the unpaired "retreat" argument with paired correctness on the same items (new Table 4). Accuracy rises from 5.8% to 9.9% on spectra (14 items gained, 2 lost; McNemar $p=0.004$) and from 22.9% to 28.6% on diffraction (14 gained, none lost; $p=0.0001$). Most revisions that clear the oracle reach an admissible but inexact value (37 of 48 on spectra, 27 of 41 on diffraction). CGSV therefore removes inadmissible claims and gives a small, significant gain in correctness, but mostly moves claims into the admissible region rather than onto the exact value. The matched controls revise every item, so their regression counts are not comparable with CGSV's.""",
                 "Results, Effect of self-verification (rewritten); new Table 4; Table 3 caption; Figure 2 caption; Methods, Constraint-Grounded Self-Verification; Discussion.")

RESP["R1.M4"] = (r"""We agree. Coverage is now reported for every cell, separating items the oracle cannot score (e.g. 64 of 90 diffraction items are evaluable) from responses without a checkable quantity. Coverage is at least 0.93 everywhere except GPT-4o on spectra (0.49). Under three treatments of non-checkable responses the ordering barely changes (Kendall $\tau=0.83$ and $1.00$); GPT-4o drops from third to fifth when they count as violations (Supplementary Table S2). Class-conditional and class-balanced DFT rates are now reported (Supplementary Table S4), and they matter: Qwen2.5-VL-7B has a pooled stability PCR of 0.917 but a balanced rate of 0.485, whereas GPT-5.6-Terra has the lowest pooled rate (0.653) but a balanced rate of 0.814. On a new common set with 45 materials per class (Supplementary Table S6), every model is far less consistent on computed-metallic compositions (PCR 0.21-0.40) than on gapped ones (0.84-0.96), a shared bias the imbalanced sample hid.""",
                 "Results, Physical consistency of current models (new paragraphs on coverage and class balance); Methods, The Physical-Consistency Rate; Supplementary Tables S2, S4, S6.")

RESP["R1.m1"] = (r"""We agree. The DFT tasks give only a formula, checked against one Materials Project entry, so the reference polymorph is not identified. We now state and quantify this. Among the 540 compositions that occur more than once in our batch, polymorphs disagree on the stability class for 0.8%, on the band-gap class for 15.6% and on the magnetization class for 16.1%. Re-scoring every claim against the composition's lowest-energy polymorph changes 12.6% of stability verdicts (8.5% become abstentions, 4.0% flip) and 10.5% of metallicity verdicts. Structure-resolved prompts are noted as an extension.""",
                 "Methods, DFT-grounded property oracles; Discussion (final sentence).")

RESP["R1.m2"] = (r"""We agree. New Table 6 breaks the in-distribution result down by family: AUC is high for microscopy (0.922) and stability (0.804), moderate for magnetism (0.728) and diffraction (0.696), and near chance for metallicity (0.582) and spectra (0.513). A family-prior baseline alone reaches AUC 0.759, so part of the pooled 0.850 reflects base-rate differences between families. We now recommend the verifier only where it discriminates.""",
                 "Results, Verifier for violation prediction; new Table 6; Discussion; Key contributions (4).")

RESP["R2.S1"] = ("We thank the reviewer for this assessment.", "")
RESP["R2.S2"] = ("We thank the reviewer. Following Reviewer 1 (comment 1), we now also note that part of the accuracy-consistency gap is definitional, which sharpens the construct separation.", "Results, Accuracy versus consistency.")
RESP["R2.S3"] = ("We thank the reviewer. Following Reviewer 1 (comment 3), zero regressions is now attributed to the stopping rule, and retreat versus correction is tested with paired before-after correctness (new Table 4).", "Results, Effect of self-verification; Table 4.")

RESP["R2.W1"] = (r"""We agree. The main text now reports only final-protocol results. Superseded numbers, the withdrawn magnetism-transfer claim and the earlier accuracy-gap figure were moved to a new Supplementary Note 2, which records how the oracles and the verifier split reached their final form. Internal labels, experiment numbers, repository paths and file names were removed from the text, captions and Acknowledgements.""",
                 "Results; Discussion; Methods (Programmatic geometric oracles, DFT-grounded property oracles, Models and experimental protocol, Statistics); Figure 4 caption; Table 3 caption; Acknowledgements; Supplementary Note 2.")

RESP["R2.W2"] = (r"""Thank you for catching this. The spectrum and DFT audits were redone under the final oracles; the statements that their reviews "predate" these definitions referred to an older taxonomy and were out of date. Table 1 now gives the sample size of every audit, and its caption states the oracle version under which each family was sampled and judged (the final definitions in every case) and the audit dates; the Figure 1c note and the Methods are aligned with it. The taxonomy now covers all six families, using the final-oracle audits (Supplementary Table S5).""",
                 "Table 1 (sample sizes and caption); Figure 1c caption and note; Methods, Baselines (error taxonomy); Supplementary Table S5.")

RESP["R2.W3"] = (r"""We agree, and this led to an important correction. Table 1 now gives Wilson 95% intervals; the 2 unsure spectrum cases move precision by at most 0.4 points. A second, blind annotator re-labelled a stratified subsample of 30 cases per family. Agreement is high where the criterion is sharp (Cohen's kappa 1.00 for metallicity, 0.71 for microscopy, 0.63 for magnetism) and low at the diffraction (0.33) and spectrum (0.13) tolerance boundaries, where every dispute was a claim just outside tolerance on the flank of a real peak. Both annotators then adjudicated the 24 disputed cases. Weighted back by stratum, consensus precision is 0.60 [0.44, 0.75] for diffraction, 0.61 [0.44, 0.76] for spectra and 0.89-1.00 for the other families (Table 1, new column). The paper now states that about four in ten fired diffraction and spectrum cases are not violations, so these families' PCR understates the true rate more than the single audit suggested.

The second annotation also exposed a flaw in the stability oracle: the prompt tells models to call borderline cases UNSTABLE, but the oracle required STABLE within 0.05 eV/atom of the hull. We now treat this near-hull band as an abstention band, as for metallicity, and recomputed all stability results from the existing responses. The stability audit becomes 57 of 57 genuine violations; results under the original rule are in Supplementary Table S7.""",
                 "Table 1 (new two-annotator consensus column, stability row and footnote); Results, Oracle validity; Methods, DFT-grounded property oracles (stability definition) and Baselines (human agreement); Supplementary Note 2; Supplementary Tables S7 and S8.")

RESP["R2.W4"] = (r"""We agree, with one clarification: for the image constraint types all models already received the same items in each seed, so those comparisons were paired; the Methods now say so. For the DFT types each model drew its own materials. Every comparison is now tested at the item level (exact McNemar for paired items, Fisher's exact test for DFT, a paired bootstrap for overall PCR), with Holm correction and effect sizes (Supplementary Table S3). GPT-5.6-Terra exceeds GPT-4o by 0.072 [0.018, 0.125] (Holm $p=0.045$); the Opus-Sonnet, Thinking-Instruct and Sol-Terra differences are not significant. On microscopy, seven of the other eight models exceed Qwen2.5-VL-7B; Qwen3-VL-8B-Instruct does not. We also ran all models on a common, class-balanced DFT set (Supplementary Table S6). There no stated DFT comparison is significant (GPT-5.6-Terra vs GPT-4o +0.021 [-0.042, 0.085]), so that gap comes from the image types, chiefly spectra. Qwen3-VL-8B-Thinking is missing from this set because its endpoint was withdrawn. Diffraction comparisons are marked provisional.""",
                 "Results, Physical consistency of current models; Table 2 caption; Methods, Models and experimental protocol and Statistics; Supplementary Tables S3 and S6.")

RESP["R2.W5"] = (r"""We agree. Coverage is now reported for every cell (Supplementary Table S2). Because excluding non-checkable responses could reward saying less, we also report PCR with them counted as violations and as consistent. The ordering barely changes (Kendall $\tau=0.83$ and 1.00); GPT-4o falls from third to fifth when they count as violations, because of its low spectrum coverage (0.49).""",
                 "Results, Physical consistency of current models; Methods, The Physical-Consistency Rate; Supplementary Table S2.")

RESP["R2.W6"] = (r"""We agree. With about 500 checkable items per model, the smallest difference detectable at 80% power is 0.064-0.079 overall and 0.11-0.20 within a constraint type; the Results and Discussion now state this, with effect sizes and intervals for every comparison. Non-significant contrasts are described as excluding only differences above about 0.07, not as equivalence. The claims about scaling, reasoning modes and pricing tiers moved to the limitations, since each rests on one pair of models.""",
                 "Results, Physical consistency of current models; Discussion (first paragraph); Table 2 caption.")

RESP["R2.W7"] = (r"""Thank you. We verified all four studies and discuss them in a new Introduction paragraph, as background rather than as comparators for the metric. FaithCoT-Bench tests whether a chain reflects the computation behind an answer; MatPCR tests whether the stated quantities are physically admissible, so the two are complementary. CoT-Evo's evolutionary distillation could use an admissibility signal as a fitness term. The prompt dependence found in the sarcasm-perception study parallels our finding that checkability shifts with prompt wording. The legal knowledge-infusion survey separates injection from verification; MatPCR belongs to verification. None of the four measures the physical admissibility of stated quantities.""",
                 "Introduction (new paragraph after the discussion of chain faithfulness); References.")


ORDER = ["R1.M1", "R1.M2", "R1.M3", "R1.M4", "R1.m1", "R1.m2",
         "R2.S1", "R2.S2", "R2.S3", "R2.W1", "R2.W2", "R2.W3", "R2.W4", "R2.W5", "R2.W6", "R2.W7"]
TITLE = {"R1": "Reviewer 1", "R2": "Reviewer 2"}
NAME = {"M": "Major comment", "m": "Minor comment", "S": "Strength", "W": "Weakness"}


def label(cid):
    who, rest = cid.split(".")
    return f"{TITLE[who]}, {NAME[rest[0]]} {rest[1:]}"


def tex_escape(s):
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"), ("$", r"\$")]:
        s = s.replace(a, b)
    s = s.replace(r"\textbackslash\{\}", r"\textbackslash{}")
    return s


def tex_resp(s):
    s = s.replace("%", r"\%").replace("&", r"\&")
    return re.sub(r"\[\[PENDING: (.*?)\]\]", r"\\textcolor{red}{[PENDING: \1]}", s)


def build_tex():
    out = [r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.3cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,xcolor,enumitem}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}\setlength{\parskip}{0.5em}
\newenvironment{reviewer}{\begin{quote}\itshape\small}{\end{quote}}
\begin{document}
{\Large\bfseries Response to Reviewers}\par\medskip
\textbf{Manuscript:} Physics as the label for measuring and correcting materials reasoning in multimodal models\par
\textbf{Journal:} Knowledge-Based Systems\par\bigskip
"""]
    current = None
    for cid in ORDER:
        who = cid.split(".")[0]
        if who != current:
            out.append(rf"\section*{{{TITLE[who]}}}")
            current = who
        resp, where = RESP[cid]
        out.append(rf"\subsection*{{{label(cid)}}}")
        out.append(r"\begin{reviewer}" + tex_escape(C[cid]) + r"\end{reviewer}")
        out.append(r"\textbf{Response.} " + tex_resp(resp))
        if where:
            out.append(r"\textbf{Changes in the manuscript.} " + tex_resp(where))
    out.append(r"\end{document}")
    return "\n\n".join(out)


def md_resp(s):
    s = re.sub(r"\$([^$]*)\$", lambda m: m.group(1).replace("\\hat d", "d̂").replace("\\le", "≤").replace("\\mathrm{PCR}^\\star", "PCR*")
               .replace("\\mathrm{PCR}", "PCR").replace("\\alpha", "α").replace("\\tau", "τ").replace("k_i", "k_i").replace("^{-1}", "⁻¹"), s)
    s = s.replace("cm^{-1}", "cm⁻¹").replace("cm$^{-1}$", "cm⁻¹").replace("\\pm", "±")
    s = re.sub(r"\\emph\{(.*?)\}", r"*\1*", s)
    return re.sub(r"\[\[PENDING: (.*?)\]\]", r"**[PENDING: \1]**", s)


def build_md():
    out = ["# Response to Reviewers", "",
           "**Manuscript:** Physics as the label for measuring and correcting materials reasoning in multimodal models  ",
           "**Journal:** Knowledge-Based Systems", ""]
    current = None
    for cid in ORDER:
        who = cid.split(".")[0]
        if who != current:
            out += [f"## {TITLE[who]}", ""]
            current = who
        resp, where = RESP[cid]
        out += [f"### {label(cid)}", "", "> *" + C[cid].replace("\n", " ") + "*", "", "**Response.** " + md_resp(resp), ""]
        if where:
            out += ["**Changes in the manuscript.** " + md_resp(where), ""]
    return "\n".join(out)


if __name__ == "__main__":
    missing = [k for k in ORDER if k not in C]
    assert not missing, f"comment text missing for {missing}"
    open(os.path.join(HERE, "response_to_reviewers.tex"), "w").write(build_tex())
    open(os.path.join(HERE, "response_to_reviewers.md"), "w").write(build_md())
    n_pend = build_md().count("[PENDING:")
    print(f"wrote response_to_reviewers.tex / .md  ({n_pend} pending markers)")
