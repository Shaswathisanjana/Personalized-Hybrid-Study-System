# Academic topic search and Word reports — Phase 3

Open **Advanced Research Agent** with a saved student profile. The page now provides a visible **Search Research Papers by Topic** form, the existing PDF upload section, a mixed-source collection/report section, and the existing abstract analysis/assessment/Markdown workflow.

## Search and select sources

1. Enter any academic topic and a desired usable-paper target. Click **Search academic papers** to fetch the first bounded page from the existing OpenAlex provider architecture.
2. Inspect actual supplied titles, authors, years, DOI, source links and reconstructed abstracts. Missing metadata is labelled not supplied. Rejected/missing abstracts remain visible with their quality-filter reasons.
3. Click **Load more / retry academic search** to retrieve another page or retry a failed page. Existing results and selections are retained. Retrieval does not run automatically on refresh. Targets are not guarantees; provider exhaustion, quotas and configured bounds are reported.
4. Filter saved results by title/author or usable abstracts and move through **Saved result page**. Check individual **Select search result** boxes, then click **Add selected search results to collection**. Selection survives refresh; starting a new search replaces the saved search session but preserves the research collection.
5. Duplicate provider IDs, DOI and conservative source identities do not add duplicate academic entries. A duplicate with a newly usable abstract can upgrade a metadata-only entry. Rejected abstracts may be retained as metadata-only records but are not silently analyzed.

OpenAlex cursor pagination follows its [official paging protocol](https://help.openalex.org/api/paging/). Its [authentication guidance](https://help.openalex.org/api/authentication/) states that paging beyond the first cursor page requires a key. Configure `OPENALEX_API_KEY` privately in the process environment or your existing ignored environment mechanism when needed. The application sends it in an authorization header, not source URLs, persisted search records or report references. No key is created, requested by email, edited or printed by this implementation. Provider policy, access and quotas can change; HTTP failures remain visible and retryable.

## Analyze the mixed collection

Uploaded PDFs keep their original Phase 2 extraction controls. Extract queued PDFs before mixed analysis. Retrieved papers remain **abstract_only**; downloading or reading their full text is not implied.

Use **Analyze / retry mixed collection batch** to process the next bounded set of selected PDF/abstract chunks. This invokes the configured Gemini provider and can incur charges. Each successful chunk is saved independently; retries skip successful work. Abstract quotations retain an abstract chunk identifier and no fabricated page number. PDFs retain their file hash and page/chunk provenance. Native PDF selection/removal remains in the original PDF section; academic selection/removal is in the mixed collection section.

Comparison reuses the existing research comparison/gap/objective services. Source observations are checked excerpts. Thematic synthesis is an attributed evidence map organized by reported fields; matching/distinct wording does not establish semantic consensus or contradictory results. Suggested gaps/directions are system-generated proposals motivated by reported limitations, not paper findings or validated novelty claims.

Searching, selection, analysis, viewing and export never update mastery. Existing assessed student-response workflows remain the route into CACM. The original abstract analysis slider now supports targets beyond five, within its backend ceiling of 100 and the configured target bound; the incremental search interface supports larger configured targets.

## Generate a Word report

1. Select active collection sources for analysis using their existing collection controls.
2. In the Word form, enter **Word report title** and **Word report research topic**.
3. Choose the exact **Papers to include in Word report**, independently of selecting analysis sources.
4. Choose any subset of the twelve **Word report sections**: title/topic; source details/references; overviews; paper objectives; methodologies; dataset/evaluation; comparison table; thematic synthesis; similarities/differences; preliminary gaps; proposed directions; limitations/coverage.
5. Click **Generate Research Report (.docx)**, then **Download Research Report (.docx)**. This builds a real Word package locally with headings, a methodology table where evidence exists, source URLs/hyperlinks and PDF/abstract citations. It makes no provider request.

The title/topic, source selection and section preferences are saved per profile when generating. Download bytes can be regenerated after refresh without repeating analysis. Unavailable analysis sections are omitted rather than filled with invented content. Reference metadata may legitimately be unknown. Mandatory coverage notices and inline source attribution remain even if optional references/limitations sections are unchecked. Pending/excluded sources are labelled when included; they do not gain findings just by appearing in a report. Existing Markdown downloads remain unchanged in the original abstract workflow.

Existing saved abstract analyses also appear in the Word form after a rerun/refresh. Their source-supported observations and verified quotations are reused without repeating retrieval or generation. They remain abstract-only; this does not silently add them to the persistent collection. Matching source URLs already represented in the active collection are not added a second time to that report view.

## Configuration

Positive integer environment settings apply before startup:

| Variable | Default | Meaning |
| --- | ---: | --- |
| `PHSS_RESEARCH_MAX_TARGET` | 1000 | Requested usable-paper target ceiling |
| `PHSS_RESEARCH_PAGE_SIZE` | 20 | Provider results per explicit request/display page; supported maximum 100 |
| `PHSS_RESEARCH_MAX_PAGES` | 50 | Successful pages per search |
| `PHSS_RESEARCH_MAX_RESULTS` | 2000 | Saved distinct results per search; also bounds target |
| `PHSS_RESEARCH_MAX_SOURCES` | 200 | Stored academic sources per profile, including inactive records |
| `PHSS_RESEARCH_MAX_ABSTRACT_CHARS` | 100000 | Per-source abstract character bound |
| `PHSS_RESEARCH_MAX_REPORT_SOURCES` | 100 | Selected sources per report |

PDF collection and analysis bounds from the Phase 2 guide still apply. Academic abstracts are split into bounded chunks using the same configured chunk size and analysis-batch limits as PDFs. Each academic response page has an 8 MiB transfer bound and provider timeout. Removal excludes a source from active use but retains stored records for recovery and quota accounting; clearing study progress does not purge research collections.

## Verification and current limits

Offline tests exercise real main-app actions, persisted selection, profile separation, provider failures, mixed analysis, section preferences and real generated DOCX contents. A four-field projection from an actual public OpenAlex work response is checked in with provenance under `tests/fixtures`; other records/failures are explicitly synthetic. Fixtures are not published research findings or a live search-quality evaluation.

No live Gemini analysis, credential validation, full retrieval benchmark, manual native-browser download/file-picker test or Microsoft Word desktop rendering check was performed. DOCX packages are validated and read back with python-docx. Full-text coverage remains limited to successfully extracted/analyzed chunks; OCR is unavailable. Large collections can produce long reports. Local profile IDs and code execution retain the previously documented prototype security limits. Phases 4–6 are not part of this change.
