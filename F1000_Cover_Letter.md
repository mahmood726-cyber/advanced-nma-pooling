Date: 14 March 2026

To: The Editors, F1000Research

Subject: Submission of software article - Advanced NMA Pooling v0.1.1

Dear Editors,

Please consider our manuscript, "Advanced NMA Pooling v0.1.1: a Python toolkit for reproducible network meta-analysis, bias adjustment, and non-proportional hazards workflows", for publication as a Software Tool Article in F1000Research.

The manuscript is submitted on behalf of Mahmood Ahmad, Niraj Kumar, Bilaal Dar, Laiba Khan, and Andrew Woo.

This submission was prepared with the recurring themes of real F1000 software-tool peer review in mind. In particular, we have aimed to avoid the common weaknesses seen in early software manuscripts: skeleton Methods/Results sections, unclear comparison with existing open tools, insufficient reproducibility detail, unsupported performance claims, and poor separation between implemented functionality and demonstrated validation evidence.

The manuscript therefore emphasizes four points:

- It describes the implemented package scope clearly, but limits quantitative claims to the workflows actually evidenced in the article.
- It ties the reported results to explicit generated artifacts in the release tree, namely `artifacts/publication-suite.json`, `artifacts/publication-summary.md`, `artifacts/paper1-bundle/manifest.json`, and `artifacts/paper1-bundle/paper1-executive-summary.md`.
- It documents a public source repository for release `v0.1.1` and the corresponding release provenance anchored at commit `d7b61ea98be6ee6ce11e61ed6b391a2675bf5c0a`.
- It states current limitations directly, including the present restriction of this draft to publication-suite and paper-bundle evidence, the continuous-only ML-NMR implementation, and the fact that DOI-backed archival through Zenodo remains pending even though the exact manuscript-result artifacts are now included in a public GitHub submission snapshot.

In brief, the manuscript reports an open-source Python package that integrates aggregate-data network meta-analysis, ML-NMR-style AD+IPD workflows, design-stratified bias adjustment, and survival non-proportional hazards workflows under a config-driven reproducibility layer. The article does not claim that every implemented module has a full standalone case study in this paper. Instead, it presents quantitative results from the publication suite and the paper bundle, supported by the release-tree artifacts and the current automated validation evidence.

The public source repository is:
https://github.com/mahmood726-cyber/advanced-nma-pooling

The current release analyzed in the manuscript is:
https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/v0.1.1

The public GitHub submission snapshot containing the revised manuscript package and exact generated result files is:
https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-14

The remaining publication-facing gap is DOI-backed archival packaging. The manuscript now points to the public GitHub submission snapshot, and Zenodo DOI generation for that frozen snapshot remains pending. That is an explicit limitation rather than an omitted dependency.

Thank you for your consideration.

Sincerely,
Mahmood Ahmad
Royal Free Hospital
mahmood.ahmad2@nhs.net

Corresponding author listed in manuscript:
Mahmood Ahmad (mahmood.ahmad2@nhs.net)
