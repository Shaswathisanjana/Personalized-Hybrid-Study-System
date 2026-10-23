# Research PDF collections — Phase 2

This guide describes the Phase 2 PDF path. Phase 3 adds [topic search, mixed-source collections and Word reports](RESEARCH_SEARCH_AND_DOCX.md) alongside it; the original PDF controls remain available.

The **Advanced Research Agent** page now has a dedicated **Uploaded research papers — PDF collection** section above the unchanged abstract workflow. These are separate source scopes: PDF analysis uses extracted page text; existing topic-search analysis and its Markdown export still use abstracts.

## Try it locally

1. Start the app with `python -B run_phss.py` (or refresh the existing local app) and select your saved student profile.
2. Open Advanced Research Agent. Read the displayed collection and processing limits.
3. Choose multiple PDFs, including more than five if desired, then click **Add uploaded PDFs to collection**. Repeated identical files are detected by SHA-256, even with another filename.
4. Click **Extract / retry next PDF batch**. Each click extracts up to three queued/retryable documents by default. Repeat for the rest. Corrupt, encrypted, scanned/text-poor or over-limit files receive explicit statuses; no OCR output is invented.
5. Choose a document in **Inspect a PDF document**. Inspect its supplied metadata, warnings and extracted page/chunk text. Missing titles are labelled unknown; filenames are display labels, not inferred bibliographic titles. Publication year/details remain unknown unless supported metadata is available; this version does not infer them from PDF creation dates or filenames.
6. Click **Analyze / retry next selected chunk batch**. This sends up to six extracted chunks to the configured Gemini provider and may incur API charges. No provider calls happen just from upload, extraction, navigation or refresh. Repeat until selected chunks are analyzed. Failures remain visible and retryable; successful chunks are reused.
7. Inspect individual fields and their source quotations/page/chunk IDs. Collection comparison, field-based evidence synthesis and preliminary limitation-derived objectives appear as results become available. Unknown fields are not invented. Partial coverage is displayed.
8. Refresh or restart and choose the same profile. Documents, extraction, selection and successful analysis are loaded from SQLite. Switch profiles to verify that another student cannot see the collection.
9. Uncheck **Include in active analysis** to exclude a document from analysis/comparison. **Remove from active collection** is an explicit, profile-scoped action. It retains the original data for recovery; re-uploading the same bytes reactivates it. Stored inactive files continue to count toward quotas. Clearing study progress does not delete PDFs.

Uploading/analyzing does not increase mastery, attempts or cognitive evidence. Existing evaluated student-assessment workflows remain the only route into CACM. This PDF interface does not yet offer a PDF-specific comprehension quiz.

## Configurable bounds

Set these environment variables before starting the app. No `.env` edit is required or performed by the implementation. Values must be positive integers; the active values are displayed in the UI.

| Variable | Default | Meaning |
| --- | ---: | --- |
| `PHSS_PDF_MAX_FILE_BYTES` | 20971520 | 20 MiB per file |
| `PHSS_PDF_MAX_DOCUMENTS` | 100 | Stored documents per student, including inactive records |
| `PHSS_PDF_MAX_COLLECTION_BYTES` | 209715200 | 200 MiB stored PDF bytes per student |
| `PHSS_PDF_MAX_PAGES` | 300 | Pages per PDF; over-limit files are rejected rather than silently truncated |
| `PHSS_PDF_MAX_TEXT_CHARS` | 1000000 | Extracted characters per document |
| `PHSS_PDF_CHUNK_CHARS` | 10000 | Maximum characters per page chunk; cannot exceed max text characters |
| `PHSS_PDF_MIN_TEXT_CHARS` | 80 | Minimum total extracted text to accept for analysis |
| `PHSS_PDF_EXTRACTION_BATCH` | 3 | PDFs extracted per explicit action |
| `PHSS_PDF_ANALYSIS_BATCH` | 6 | Chunk provider requests per explicit action |
| `PHSS_PDF_EXTRACTION_TIMEOUT` | 45 | Wall-clock seconds per extraction subprocess |
| `PHSS_PDF_PROVIDER_TIMEOUT` | 60 | Seconds per provider request; SDK retries disabled |
| `PHSS_PDF_MAX_WORKER_MEMORY_MB` | 512 | Per-extraction-process memory ceiling |

The extraction worker uses a Windows Job Object memory ceiling, or POSIX address-space limit on supported platforms, and a parent-enforced timeout. This is not filesystem/network isolation or a security sandbox. Streamlit buffers chosen uploads in the UI process; worker memory limits do not cap the whole server. Keep selections within displayed limits and use trusted local documents. Encrypted files must be decrypted separately; passwords are not collected or saved. Blank/image pages are explicitly outside extracted coverage because OCR is unavailable.

## Analysis and provenance

Each provider request receives actual extracted text for one page chunk, not filenames or a substituted abstract. Returned findings are accepted only as exact source excerpts of bounded length. Arbitrary generated paraphrases, outside citations and absent quotations are not stored as findings. Each claim retains its document hash, one-based PDF page number and chunk ID; extracted chunks additionally retain character offsets.

The fields are overview, research problem, objectives, methodology, dataset, experimental setup, models/algorithms, metrics, findings and limitations. Completed extracted coverage with no accepted evidence displays **Not specified in the supplied paper.** Unfinished analysis is identified separately. Quote checking establishes text membership; it does not prove perfect semantic field classification or factual truth of a paper. Human review remains necessary.

Existing methodology comparison, gap identification and objective-generation services are reused through a PDF-backed summary adapter. Comparison cells use the first accepted excerpt for their field, while individual analysis retains all accepted excerpts. Synthesis is an evidence map organized by fields and coverage, not an unrestricted generated literature-review narrative. Proposed directions are explicitly labelled system suggestions and require broader literature/feasibility checks. Internal `phss-document:<hash>` references identify local documents; they are not fabricated publication URLs or DOIs.

## Persistence and limits of completion

SQLite schema 4 adds `research_documents`, keyed by profile and file hash. It stores original bytes, extraction, selection, analysis and per-chunk errors. Existing snapshots, evidence, migration backups and assessment receipts remain intact. Document revisions reject stale writes and results for removed documents. Existing SQLite backup tooling also backs up the PDF table. There is no separate document filesystem to orphan or overwrite.

Live-provider quality and manual browser file-picker behavior have not been verified by offline tests. The native upload boundary is supplied real PDF fixture bytes in Streamlit AppTest; actual buttons, persistence and rendering run normally. Fixtures are explicitly synthetic, not academic publications. OCR, inferred publication metadata, PDF-specific quizzes, semantic literature-review narration, topic-search collection selection, DOCX export, open-topic coding and autonomous orchestration are not added in this phase.
