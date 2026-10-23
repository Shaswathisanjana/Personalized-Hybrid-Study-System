# Web stages 5, 6 and 7

## Unified orchestration

backend/service.py calls the existing StudentJourneyService, QueryRouter and study_workspace functions. The selected activity is prepared inline. Bounded ordered plans persist before expensive content work. Continuation reads updated shared CACM; active genuine conflicts block advancement. Contextual clarification is persisted and does not run an unrelated workflow. Viewing, generation, navigation and research processing do not create mastery evidence.

## Actual workflows

Learning uses OrchestratorRuntime._run_learning, actual resource recommendations, LearningAgentRuntime adaptive sessions, existing question IDs/assessment transactions, progress tracker and LearningStudyPlanner. Topic browser reads the existing bank.

Coding uses curated VerifiedCodingExercise or validated OpenTopicGenerator packages, IntegratedCodingWorkflow and CodingSubmissionController. Monaco drafts save explicitly; hints and verified correction reviews use existing services. Original student code is assessed once through existing receipts. Correction code is never assessed as student evidence.

Research uses AcademicPaperSearch through ResearchSearchSession, UnifiedResearchDocumentStore, the existing PDF extraction subprocess, grounded chunk analyzer and research comparison/report helpers. Uploads are profile-owned, deduplicated and bounded. Corrupt files retain honest failures. Full-text excerpts and abstract-only sources stay labelled. Existing quote-grouped synthesis, comparisons and limitation-derived research suggestions are available; they are not a semantic systematic review. DOCX and Markdown exports preserve available sources and provenance. Research comprehension reuses ResearchAssessmentService and only evaluated answers enter CACM.

## Persistence and recovery

Existing snapshot capture/restore, safe codecs, assessment stages, receipts, optimistic revision checks and research storage are reused. Adapter operations serialize in a single worker; conflicting writes return a recoverable response. The frontend restores profile and collection reads sequentially. Pending assessments resume from their saved request; duplicate evaluations do not replay mastery updates. Production and fixture databases are distinct and neither points into PHSS_Git.

Executed validations: deterministic API suite, copied offline application suite, tooling tests, real Chrome workflow tests, and production-server startup. Exact final results and remaining limitations are in ../WEB_APP_COMPLETION_REPORT.md.
