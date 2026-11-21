# R2.W7: verification of the four requested references

The metadata below was fetched from Crossref, the arXiv API, OpenReview API v2 and OpenAlex
(2026-10-15). Semantic Scholar rate-limited every request, so it was not used.

| # | Paper | Exists | Venue | Relevance to MatPCR |
|---|---|---|---|---|
| 1 | Chen, Liu, Huang, Zhang, **Yu (Hang)**. *Seeing Sarcasm Through Different Eyes: Analyzing Multimodal Sarcasm Perception in Large Vision-Language Models* | yes | IEEE Trans. Comput. Soc. Syst. 13(2):2122–2139 (2026); DOI 10.1109/TCSS.2025.3608484 | loose: LVLM evaluation beyond benchmark scores (prompt-dependent perception, model disagreement) |
| 2 | Feng, Ding, Zhu, Liang, Zhang, Chen. *CoT-Evo: Evolutionary Distillation of Chain-of-Thought for Scientific Reasoning* | yes | ICLR 2026 (poster); arXiv:2510.13166 | direct: improves scientific CoT; uses a correctness/coherence fitness, i.e. generation rather than evaluation |
| 3 | Shen, Wang, Tan, Yao, Zhao, Xu, Wang, Chen. *FaithCoT-Bench: Benchmarking Instance-Level Faithfulness of Chain-of-Thought Reasoning* | yes | ICLR 2026 (poster); arXiv:2510.04040 | direct: instance-level faithfulness of the stated chain, the concern raised in our Introduction |
| 4 | Liu, **Yu (Hang)**, Wang, Xu, Li, Zou, Mao, Cambria. *Legal knowledge infusion for large language models: A survey* | yes | Information Fusion (Elsevier) 125:103426 (2026); DOI 10.1016/j.inffus.2025.103426 | loose: domain-knowledge infusion and checking in another specialised field |

**Fact to note:** papers 1 and 4 share an author, Hang Yu (Shanghai University, ORCID
0000-0003-3444-9992). None of the four appears in Knowledge-Based Systems. Whether to cite 1 and 4
is an author decision. Elsevier/COPE guidance lets authors decline reviewer-requested citations
they judge not relevant, provided they explain why in the response.

```bibtex
@article{sarcasm2026lvlm,
  author  = {Chen, Junjie and Liu, Xuyang and Huang, Subin and Zhang, Linfeng and Yu, Hang},
  title   = {Seeing Sarcasm Through Different Eyes: Analyzing Multimodal Sarcasm Perception in Large Vision-Language Models},
  journal = {IEEE Transactions on Computational Social Systems},
  volume  = {13}, number = {2}, pages = {2122--2139}, year = {2026},
  doi     = {10.1109/TCSS.2025.3608484}
}
@inproceedings{cotevo2026,
  author    = {Feng, Kehua and Ding, Keyan and Zhu, Zhihui and Liang, Lei and Zhang, Qiang and Chen, Huajun},
  title     = {{CoT-Evo}: Evolutionary Distillation of Chain-of-Thought for Scientific Reasoning},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2026}, url = {https://openreview.net/forum?id=OMf3w00d95}, note = {arXiv:2510.13166}
}
@inproceedings{faithcotbench2026,
  author    = {Shen, Xu and Wang, Song and Tan, Zhen and Yao, Laura and Zhao, Xinyu and Xu, Kaidi and Wang, Xin and Chen, Tianlong},
  title     = {{FaithCoT-Bench}: Benchmarking Instance-Level Faithfulness of Chain-of-Thought Reasoning},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2026}, url = {https://openreview.net/forum?id=lN3yKqqzF1}, note = {arXiv:2510.04040}
}
@article{legalinfusion2026,
  author  = {Liu, Qian and Yu, Hang and Wang, Qiqi and Xu, Qi and Li, Jinpeng and Zou, Zhuoqun and Mao, Rui and Cambria, Erik},
  title   = {Legal knowledge infusion for large language models: A survey},
  journal = {Information Fusion}, volume = {125}, pages = {103426}, year = {2026},
  doi     = {10.1016/j.inffus.2025.103426}
}
```
