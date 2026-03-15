Date: 15 March 2026

To: The Editors, F1000Research

Subject: Submission of software article - Advanced NMA Pooling v0.1.1

Dear Editors,

Please consider our manuscript, "Advanced NMA Pooling v0.1.1: a reproducibility-oriented Python toolkit for advanced evidence-synthesis workflows", for publication as a Software Tool Article in F1000Research.

The manuscript is submitted on behalf of Mahmood Ahmad, Niraj Kumar, Bilaal Dar, Laiba Khan, and Andrew Woo.

This submission was prepared with the recurring themes of real F1000 software-tool peer review in mind. In particular, we have aimed to avoid the common weaknesses seen in early software manuscripts: skeleton Methods/Results sections, unclear comparison with existing open tools, insufficient reproducibility detail, unsupported performance claims, and poor separation between implemented functionality and demonstrated validation evidence.

The manuscript therefore emphasizes five points:

- It describes the implemented package scope clearly, but limits quantitative claims to the workflows actually evidenced in the article.
- It ties the reported results to explicit generated artifacts in the release tree, namely `artifacts/publication-suite.json`, `artifacts/publication-summary.md`, `artifacts/paper1-bundle/manifest.json`, and `artifacts/paper1-bundle/paper1-executive-summary.md`, and it now packages copied release provenance files in `f1000_artifacts/release-manifest-v0.1.1.json` and `f1000_artifacts/SHA256SUMS-v0.1.1.txt`.
- It documents a public source repository for release `v0.1.1` and the corresponding release provenance anchored at commit `d7b61ea98be6ee6ce11e61ed6b391a2675bf5c0a`.
- It distinguishes engineering verification evidence such as tests, manifests, and release provenance from broader methodological validation, so software QA is not presented as a substitute for cross-software concordance.
- It states current limitations directly, including the present restriction of this draft to publication-suite and paper-bundle evidence, the continuous-only ML-NMR implementation, the narrow low-heterogeneity continuous scenario, and the fact that DOI-backed archival through Zenodo remains pending even though the exact manuscript-result artifacts, copied release provenance files, and aligned figure package are now included in a public GitHub submission snapshot.

In brief, the manuscript reports an open-source Python package that integrates aggregate-data network meta-analysis, ML-NMR-style AD+IPD workflows, design-stratified bias adjustment, and survival non-proportional hazards workflows under a config-driven reproducibility layer. The article is positioned as a software-tool and reproducibility paper rather than as a comprehensive cross-software benchmarking study. It does not claim that every implemented module has a full standalone case study in this paper. Instead, it presents quantitative results from the publication suite and the paper bundle, supported by named release-tree artifacts and engineering verification evidence that is explicitly separated from broader methodological claims.

The public source repository is:
https://github.com/mahmood726-cyber/advanced-nma-pooling

The current release analyzed in the manuscript is:
https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/v0.1.1

The public GitHub submission snapshot containing the revised manuscript package, exact generated result files, and copied release provenance files is:
https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-15-r3

The only mandatory external step that remains is DOI-backed archival packaging. The manuscript now points to the public GitHub submission snapshot, and Zenodo DOI generation for that frozen snapshot remains pending. That is an explicit limitation rather than an omitted dependency.

Thank you for your consideration.

Sincerely,
Mahmood Ahmad
Royal Free Hospital
mahmood.ahmad2@nhs.net

Corresponding author listed in manuscript:
Mahmood Ahmad (mahmood.ahmad2@nhs.net)
