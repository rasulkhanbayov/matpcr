# Knowledge-Based Systems: submission requirements that apply to this revision

Fetched 2026-10-15 from the current Guide for Authors
(https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors).
A full-text snapshot is in `kbs_guide_for_authors_snapshot_2026-10-15.md`. Items marked
"decision letter" come from the editor's comments.

| Requirement | Source | Applies how |
|---|---|---|
| Editable source: .tex + .bib (+ .bbl); PDF not a source | GFA; decision letter | LaTeX source, flat folder, include .bib/.bbl/.cls/.bst |
| House class is `elsarticle` (CTAN v3.5, 2026-01-09); Springer `sn-jnl` is not appropriate for Editorial Manager | Elsevier LaTeX page | convert manuscript + SI to `\documentclass[preprint,review,12pt]{elsarticle}` |
| Numbered references in square brackets, in order of appearance | GFA | `elsarticle-num.bst` |
| Abstract ≤ 250 words | GFA | check / trim |
| 1–7 keywords | GFA | current 5, OK |
| Highlights: separate editable file with "highlights" in the name, 3–5 bullets, each ≤ 85 characters | GFA (encouraged); decision letter (Word) | `highlights.docx` |
| Graphical abstract | not required | skip |
| Length: preferably ≤ 20 double-spaced pages incl. tables/figures | GFA | currently ~29 pp in sn-jnl; move audit trail and long method notes to SI |
| Figures as separate files (Figure_1, ...); raster ≥ 300 dpi; **not PDF** for the revision | GFA; decision letter | export every figure (incl. TikZ) as 300+ dpi PNG/TIFF |
| Tables and equations as editable text, not images | GFA; decision letter | already LaTeX tables/equations |
| CRediT author statement (required) | GFA; decision letter (Word) | `credit_author_statement.docx` |
| Declaration of competing interest via Elsevier tool, uploaded as .docx | GFA; decision letter | author action (tool) + draft text |
| Funding statement: "This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors." | GFA | replace current wording |
| Data availability statement + repository link | GFA (Option C) | Zenodo link present |
| GenAI declaration: section titled "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process", before references, exact wording "During the preparation of this work the author(s) used [NAME OF TOOL/SERVICE] in order to [REASON]. After using this tool/service, the author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the published article." | GFA | replace current "Use of AI assistance" |
| Cover letter, response to reviewers, highlights, CRediT, author agreement, declaration of interest in **Word** | decision letter | produce .docx for each (author agreement needs signatures) |
| English language editing (Elsevier Author Services recommended) | decision letter | thorough edit by us; paid service is an author decision |
| Peer review: single anonymized | GFA | names stay on manuscript |
