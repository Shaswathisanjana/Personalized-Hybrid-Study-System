# Upgrade validation

Validated in this delivery:

- 24 Node tests passed: Gemini message adapter and error handling, research API input checks, student-scoped job lookup and output allowlist, existing real Pyodide execution tests, coding roadmap and Student ID guards.
- 4 Python tests passed: exact quote filtering, cross-paper evidence references, section headings, and clustering with deterministic fixture vectors.
- A generated text PDF was processed by PyMuPDF, including section heading identification.
- Word report generation was exercised with a clearly labelled fixture, rendered and inspected for layout.
- Home and research routes returned their pages. Node syntax checks passed for server and research scripts.
- Production Node dependencies installed successfully with npm ci --ignore-scripts --omit=dev.

Not validated live: arXiv retrieval, Gemini responses, downloading/loading BGE weights, end-to-end research with real papers, MongoDB persistence, Judge0, and YouTube. No API key was supplied and sentence-transformers is not installed in this execution environment. Real BGE embeddings were not replaced with fake embeddings in the application. The clustering unit test uses fixture vectors only.

The source was reconstructed from the saved CACM-Full-Code.txt export, which includes coding/roadmap.cjs and newer Student ID fixes beyond the pasted backup. Existing learning and coding behavior was preserved while routing generation through the Gemini REST API.
