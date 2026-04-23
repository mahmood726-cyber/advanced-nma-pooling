# Multi-Persona F1000 Pre-Submission Review: Advanced NMA Pooling

Review date: 2026-03-15  
Review model: internal 3-persona rubric (Methods, Reproducibility, Editorial)  
Calibration source: `<user-OneDrive>/Desktop/reviewer Report.txt` (local-only)

## Overall decision

Ready for external submission once DOI-backed archival is completed.

The local package now addresses the main reviewer-shaped weaknesses identified in the previous round. The manuscript-facing publication artifacts record a fixed git commit, the manuscript names representative tool comparators, the mixed-design example is more concrete, and the submission snapshot includes copied release-provenance files alongside the cited outputs. The manuscript framing is also narrower and more defensible: it now presents itself as a reproducibility-oriented software-tool paper rather than as a comprehensive methods-validation article. The only mandatory blocker that remains is external DOI-backed archival.

## Findings

### 1. High - DOI-backed archival is still the only real submission blocker
**Personas:** Reproducibility, Editorial  
**References:** `F1000_Software_Tool_Article.md`; `F1000_Cover_Letter.md`; `F1000_Submission_Checklist_RealReview.md`

The manuscript, cover letter, and checklist now consistently state that Zenodo deposition is pending. That is accurate, but it still leaves the package short of a final F1000-ready archived-source record.

**Why this matters:** The local submission bundle is now coherent, but the journal-facing archival requirement is external and still unmet until the public snapshot is deposited and a DOI is minted.

**Needed fix:** Create the Zenodo record from the frozen public snapshot and replace the DOI placeholder everywhere in the submission package.

### 2. Low - The continuous publication-suite scenario remains a low-heterogeneity regression check rather than a broad stress test
**Personas:** Methods  
**References:** `F1000_Software_Tool_Article.md`; `configs/example-publication-suite.json`; `artifacts/publication-summary.md`

The current continuous scenario still uses `study_heterogeneity_sd: 0.0`. That is no longer hidden or overstated: the manuscript now explicitly frames this as a locked regression-and-stability check. Even so, a skeptical methods reviewer could still note that it is a favorable confirmatory setting rather than a general heterogeneity stress test.

**Why this matters:** This is now mainly a limitation of scope rather than a manuscript defect. The framing is substantially improved, and the paper no longer presents the scenario as broader methodological evidence than it is.

**Needed fix:** Optional for this submission cycle. If a later revision needs stronger methodological breadth, add one heterogeneity-positive confirmatory scenario to the manuscript-facing suite.

### 3. Low - The worked mixed-design example is improved, but it is still synthetic rather than a full applied case study
**Personas:** Editorial, Methods  
**References:** `F1000_Software_Tool_Article.md`; `f1000_artifacts/tutorial_walkthrough.md`; `artifacts/paper1-bundle/paper1-executive-summary.md`

The paper bundle now reads as a genuine worked example rather than a vague reviewer checklist: the manuscript explains the randomized and non-randomized inputs, interprets the positive `nrs` bias term, and reports the recovered treatment effects. That materially improves the narrative. The remaining limitation is that the example is still a synthetic mixed-design vignette, not a clinical use-case paper.

**Why this matters:** This is acceptable if the article continues to present itself as a reproducibility-and-validation software paper. It would be weaker only if the paper tried to claim broad applied-case-study validation.

**Needed fix:** No immediate local fix required beyond keeping the positioning modest, which the current draft does.

## Persona summaries

### Methods reviewer
- Strongest remaining concern: the central continuous scenario is appropriately described, but still intentionally narrow.
- Bottom line: acceptable for a software-tool paper because the title, abstract, and discussion now keep the claims aligned with that narrower evidence base.

### Reproducibility reviewer
- Strongest remaining concern: DOI-backed archival is still external and pending.
- Bottom line: the local provenance story is now materially stronger because the publication artifacts themselves record commit `694a31770a8e4e51d4ceab43a77d12aaad8795ea` and the submission package includes copied release-manifest and checksum files.

### Editorial reviewer
- Strongest remaining concern: the package still needs the final archive DOI before external submission.
- Bottom line: the manuscript no longer reads like an outline or an under-specified repo description; it now reads like a near-final software-tool submission with appropriately moderated claims.

## Positive notes

- The previously material provenance gap is fixed: the publication-summary and publication-suite artifacts now record a concrete git commit and the publication configuration requires that capture.
- The manuscript now names representative comparator classes concretely, including MetaInsight, `netmeta`, and `multinma`, without making exaggerated superiority claims.
- The mixed-design bundle section now functions as a readable worked example instead of only a reviewer-facing execution note.
- The manuscript now distinguishes engineering verification evidence from broader methodological validation, reducing the risk that software QA is read as inferential proof.
- The submission package includes the aligned figure asset/caption files, copied release provenance files, and the exact generated artifacts cited in the Results section.
- The full local regression run passed after the tightening changes.

## Final disposition

Internal decision: conditionally ready.

From a local package perspective, the actionable manuscript and reproducibility issues are substantially resolved. The remaining mandatory step is external archival: mint the Zenodo DOI from the frozen GitHub snapshot and patch that DOI into the submission materials.
