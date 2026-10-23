# Limitations and remaining priorities

The current prototype has implemented and offline-tested workflows; it is not a validated production learning platform. Milestone reports and the latest evaluation artifacts provide the exact tested scope.

| Area | Current boundary | Next priority |
| --- | --- | --- |
| Code execution | Local subprocesses have time limits, but no dependable filesystem/network/process/memory isolation | Before public/untrusted use, isolate execution with resource limits and a threat-reviewed runner |
| Identity | UUID profiles and ownership checks separate state; URLs are not authentication | Add authenticated identity and server-side authorization before multi-user deployment |
| Student data | SQLite snapshots persist sensitive answers/code; stale writes are rejected rather than merged | Define retention, access controls, backup/restore and deployment storage procedures |
| Environment | Launcher/import and HTTP startup checks pass; observed direct versions recorded in requirements.txt; no tested clean install/transitive lock | Reconstruct a separate environment and validate installation with approval |
| Provider behavior | Offline fixtures cover injected failures; live quality/availability/costs are unmeasured | Budgeted live smoke checks, grounded-answer review and quota/error observations |
| Transaction guarantees | Saved completed stages are reused; a response lost before its checkpoint may require another call | Avoid claims of exactly-once provider billing; consider provider request reconciliation where available |
| Coding coverage | Six curated concepts/18 exercises plus generated Python function packages; generated reference/tests are not independent oracles; native SQL/other languages are unsupported | Review topic relevance, difficulty and test coverage; isolate execution before untrusted use; see [open-topic coding](OPEN_TOPIC_CODING.md) |
| Research | OpenAlex abstract retrieval and uploaded PDF page/chunk-grounded analysis; bounded search may miss requested paper count; scanned/image-only PDFs need OCR | Evaluate additional providers/OCR only if needed; preserve source traceability and coverage labels |
| Mastery | Heuristic model and synthetic tests; planning/revision thresholds are design choices | Validate calibration and educational utility using an ethical study protocol |
| UI validation | AppTest plus isolated native-browser smoke coverage; no broad browser/accessibility/load evaluation or native Word/file-picker validation | Broaden browser/download/accessibility review and realistic concurrent sessions |
| Activity planning | A query sequences up to three distinct activities for the router's shared topic; not a general multi-topic dependency graph | Evaluate more complex planning separately; inspect the displayed topic/order before proceeding |

No real-student learning improvement, statistically significant outcome, systematic literature review, comprehensive security audit or live-provider reliability claim is supported by the offline suite.

The local launcher, dependency preflight and consistent SQLite backup utility now provide a supported delivery path. Prioritize clean-environment verification and a manual local demo next. Authentication and isolated execution are prerequisites for opening the service to untrusted users. Live quality evaluation and an empirical learning study are separate work with their own approvals and evidence requirements.
