**Knowledge-Based Systems: revised manuscript**

**Manuscript:** Physics as the label for measuring and correcting materials reasoning in multimodal models

**Authors:** Hasan Kurban, Rasul Khanbayov, and Mustafa Kurban

Dear Editor,

Thank you for the opportunity to revise our manuscript and for the two constructive reviews. We submit the revised version together with a point-by-point response to every comment and a version of the manuscript in which all changes are highlighted in blue.

The revision addresses each point raised by the reviewers. In brief:

- **Scope.** We now state precisely what the benchmark measures: the physical admissibility of the quantities a reasoning chain states. We also explain what this adds to answer accuracy.
- **Oracle validity.** We report interval estimates for every oracle-precision audit, the oracle version and date behind each audit, and the explicit conditions under which the theoretical guarantee applies.
- **Self-verification.** We replaced the unpaired interpretation of the self-verification results with a paired before–after analysis of answer correctness. We also state that the absence of consistency regressions follows from the stopping rule.
- **Model comparisons.** All model comparisons now rest on item-level paired or exact tests with multiplicity correction, effect sizes and the minimum detectable difference. A new common item set makes the DFT comparisons paired.
- **Coverage and class balance.** We report the checkable share of every cell, alternative treatments of non-checkable responses, and class-balanced rates.
- **Verifier.** We added a per-family breakdown of verifier performance.
- **Presentation.** We removed internal labels and the revision history from the main text and collected the development history in a supplementary note.
- **Related work.** We extended the related-work discussion as Reviewer 2 recommended.

We carried out the language revision ourselves rather than through the language-editing service: every revised passage was rewritten for clarity, long sentences were split, and internal jargon and project-specific labels were removed.

As requested, the response to reviewers, highlights, cover letter, CRediT statement, author agreement and declaration of interest are provided in Word format. The manuscript source is LaTeX with its .bib file, tables and equations are editable, and every figure is supplied as a separate raster file of at least 300 dpi.

The benchmark, provenance records, prompts and machine-readable results are available at Zenodo (record 21829644). The oracle implementations and the evaluation and analysis code are available at github.com/KurbanIntelligenceLab/matpcr, and the 13 retrained verifier adapters at huggingface.co/rasulkhanbayov/matpcr-verifier.

This manuscript is original, is not under consideration elsewhere, and has been approved by all authors. The authors declare no competing interests.

Sincerely,

Mustafa Kurban, on behalf of all authors
Ankara University, Ankara, Türkiye
kurbanm@ankara.edu.tr
