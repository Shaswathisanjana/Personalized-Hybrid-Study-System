# CACM-PHSS thesis draft

This is the project's web-application thesis, prepared from the inspected implementation and the supplied reference layout. It uses the same broad preliminary-page order, eight main chapters, appendix, references and publications page. Chapter subjects are adapted to PHSS. The current compiled PDF has approximately 53 pages.

## Open the deliverables

- `PHSS_Thesis.pdf`: compiled reading copy.
- `PHSS_Overleaf_Project.zip`: uploadable LaTeX source package.
- `mythesis.tex`: main source file.
- `metadata.tex`: title, team, institution, guide and date fields.
- `chapters/`: editable original prose.
- `mybib.bib`: 13 cited primary-paper/documentation references.
- `evidence/`: validation and recorded software-test results; not a student-study dataset.

## Use in Overleaf

1. Choose New Project > Upload Project and upload `PHSS_Overleaf_Project.zip`.
2. Select `mythesis.tex` as the main document.
3. Use pdfLaTeX and the normal automatic bibliography build (BibTeX/ieeetr).
4. Recompile. If references initially appear unresolved, recompile again.
5. Edit confirmed details in `metadata.tex` and review every chapter before submission.

The PDF was compiled locally with portable Tectonic 0.17.0, which runs the TeX/BibTeX passes automatically. The source uses standard packages compatible with pdfLaTeX. No remote Overleaf session was accessed or compiled, and exact pagination can vary with TeX versions. A local LaTeX installation can use `pdflatex mythesis`, `bibtex mythesis`, then two more `pdflatex mythesis` passes.

## Confirm before submission

The supplied team details and institution are filled in. The following are deliberately unconfirmed:

- final approved wording of the project title (current descriptive title: CACM-PHSS: A Multi-Agent Personalized Hybrid Study System);
- thesis advisor's name;
- authorised countersignatory / head of department;
- examination date;
- publication status and institution-approved certificate/declaration wording.

Certificates and declarations remain draft wording until reviewed and signed. No signatures, approvals, guide names or publication claims have been fabricated. The institution logo was rendered from the supplied reference PDF after the institution was confirmed; confirm the institution's preferred logo version before final submission.

## Scope and originality

The thesis focuses on the React/FastAPI web app. Streamlit is mentioned briefly as the initial prototype; one appendix test-suite name also reflects that development history. It does not describe Streamlit as the final application.

The main emphasis is implemented agentic coordination: semantic routing, state observation, bounded plans, real tool actions, assessment, shared CACM updates and follow-up decisions. Explicit rules, local-profile limitations, source coverage and student interaction are described honestly. No training, real-student learning gains, mastery calibration, public execution sandbox or benchmark superiority is claimed.

The project prose was written for PHSS. Another team's scientific content, results and identities were not copied. Standard institutional layout and conventional academic headings necessarily resemble the reference. No similarity service was used, and no under-10-percent similarity score or AI-detector outcome is guaranteed. Follow institutional requirements for attribution and disclosure of writing assistance.

## Evidence

Implementation baseline: `40e5a88`, branch `phss-web-app`.

During thesis preparation the offline backend suite passed 77 tests (52.20 s; one existing Starlette/httpx deprecation warning). Nine selected browser tests passed (26.6 s; zero skipped/flaky). The results chapter also identifies the earlier baseline runs separately, including 34 existing coding/persistence unittest executions and a successful production build. Overlapping runs are not counted as independent educational results.

UI images use synthetic offline fixture profiles. They show genuine application controls, not results from real students. The whole historical browser suite was not run. No application source files or real student data were changed for this thesis.

## Source and build checks

The package includes an original architecture diagram, agentic-loop diagram and research-provenance diagram, readable UI captures, equations taken from the mastery source, tables, bibliography and source mapping. The local checks verify citations, referenced input files, page count and layout overflow. Minor underfull typesetting warnings can remain; these are not unresolved references or overflowing content.
