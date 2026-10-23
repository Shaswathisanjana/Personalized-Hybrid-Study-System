"""Resumable abstract analysis with explicit checkpoints and source provenance."""
from app.research_agent.abstract_quality_validator import AbstractQualityValidator
from app.research_agent.autonomous_search import AutonomousResearchSearcher
from app.research_agent.paper_search import AcademicPaperSearch
from app.research_agent.paper_summarizer import StructuredPaperSummarizer, PaperSummary, SUMMARY_FIELDS, NOT_REPORTED
from app.research_agent.thematic_reviewer import ThematicLiteratureReviewer
from app.research_agent.source_identity import merge_sources, source_fingerprint


def run_workflow(workflow, topic, limit=5, papers=None, include_thematic_review=True,
                 search_queries=None, resume_result=None, on_checkpoint=None):
    from app.research_agent.research_workflow import ResearchWorkflowResult
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("Research topic cannot be empty")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    result = resume_result or ResearchWorkflowResult(topic=topic.strip(), requested_papers=limit)
    if result.topic != topic.strip() or result.requested_papers != limit:
        raise ValueError("A saved analysis must resume with its original topic and paper target.")
    validator = AbstractQualityValidator()

    def checkpoint():
        if on_checkpoint is not None:
            on_checkpoint(result)

    def warn(message):
        if message not in result.warnings:
            result.warnings.append(message)

    checkpoint()  # Save the request before any external call.
    result.warnings = [w for w in result.warnings
                       if not w.startswith(("Paper target not met:", "The search ended without reaching"))]
    if not result.search_complete or "search" in result.stage_errors:
        try:
            if papers is not None:
                retrieved = list(papers)  # Empty supplied input never initiates a search.
            elif search_queries is not None:
                latest = {a.query: a for a in result.search_attempts}
                failed_queries = [q for q, a in latest.items() if a.reason.startswith("Search provider failed")]
                refined = AutonomousResearchSearcher(workflow.search_service, max_attempts=3).search(
                    failed_queries or search_queries, limit=limit, target_usable_papers=limit,
                    initial_papers=result.papers)
                retrieved = refined.papers
                result.search_attempts.extend(refined.attempts)
                for warning in refined.warnings:
                    warn(warning)
                if not retrieved and refined.attempts and all(a.reason.startswith("Search provider failed") for a in refined.attempts):
                    raise RuntimeError("All planned search attempts failed. Retry retrieval when the provider is available.")
            else:
                response = (workflow.search_service or AcademicPaperSearch()).search(topic.strip(), limit=limit)
                retrieved = response.papers
                for warning in response.provider_errors:
                    warn(warning)
            result.papers = merge_sources([], retrieved, validator)
            result.search_complete = True
            result.stage_errors.pop("search", None)
            if search_queries is not None and papers is None:
                latest = {a.query: a for a in result.search_attempts}
                usable = sum(validator.validate(p.abstract, p.title).is_usable for p in result.papers)
                if usable < limit and any(a.reason.startswith("Search provider failed") for a in latest.values()):
                    result.stage_errors["search"] = "Some planned queries failed; retry will reuse retrieved sources and retry failed queries."
        except Exception as exc:
            result.stage_errors["search"] = f"{type(exc).__name__}: {exc}"
        checkpoint()
    if not result.search_complete:
        return result

    result.warnings = [w for w in result.warnings if not w.startswith(
        ("Excluded paper '", "No papers passed abstract quality validation."))]
    result.accepted_papers, result.excluded_papers = [], []
    for paper in result.papers:
        quality = validator.validate(paper.abstract, paper.title)
        if quality.is_usable:
            result.accepted_papers.append(paper)
        else:
            result.excluded_papers.append((paper, quality))
            warn(f"Excluded paper '{paper.title}': {quality.reason}")
    if len(result.accepted_papers) < limit:
        scope = "The supplied source set is exhausted" if papers is not None else "The bounded search ended"
        warn(f"Paper target not met: {len(result.accepted_papers)}/{limit} usable publications. "
             f"{scope}; missing abstracts, exclusions, duplicates "
             "and provider warnings are recorded. No replacement findings were invented.")
    if not result.accepted_papers:
        warn("No papers passed abstract quality validation. Detailed analysis was not performed.")
        checkpoint()
        return result

    # Preserve all retrieved/excluded records; bound provider analysis to the requested count.
    selected = result.accepted_papers[:limit]
    if len(result.accepted_papers) > limit:
        warn(f"Analysis is limited to the first {limit} usable sources; all retrieved records are retained.")
    batch_summaries = None
    batch_error = None
    for paper in selected:
        key = source_fingerprint(paper)
        stage = "summary:" + key
        if key in result.summary_sources:
            continue
        try:
            if workflow.summarizer is None:
                workflow.summarizer = StructuredPaperSummarizer()
            summarizer = workflow.summarizer
            if hasattr(summarizer, "summarize"):
                summary = summarizer.summarize(paper)
            else:  # Existing injected batch-only implementations remain supported.
                if batch_summaries is None and batch_error is None:
                    try:
                        pending = [p for p in selected if source_fingerprint(p) not in result.summary_sources]
                        batch_summaries = summarizer.summarize_multiple(pending)
                    except Exception as exc:
                        batch_error = exc
                if batch_error is not None:
                    raise batch_error
                matching = [s for s in batch_summaries if s.title == paper.title and s.source_url == paper.url]
                if len(matching) != 1:
                    raise RuntimeError("No unique summary was returned for this source.")
                summary = matching[0]
            if not isinstance(summary, PaperSummary) or summary.title != paper.title or summary.source_url != paper.url:
                raise ValueError("Summary identity does not match the retrieved source.")
            # The production summarizer verifies quotations. Keep that boundary
            # for injected providers too, before storing a summary in the cache.
            normal = lambda text: " ".join(text.casefold().split())
            if any(not quote or normal(quote) not in normal(paper.abstract)
                   for quote in summary.evidence_quotes.values()):
                raise ValueError("Summary quotation is absent from the retrieved abstract.")
            for field_name in SUMMARY_FIELDS:
                if not summary.evidence_quotes.get(field_name):
                    setattr(summary, field_name, NOT_REPORTED)
            summary.authors, summary.year = list(paper.authors), paper.year
            result.summary_sources[key] = summary
            result.stage_errors.pop(stage, None)
            # Downstream results based on an older partial set must be regenerated.
            result.thematic_review = result.comparison = result.gap_report = result.proposal = None
        except Exception as exc:
            result.stage_errors[stage] = f"{paper.title}: {type(exc).__name__}: {exc}"
        result.summaries = [result.summary_sources[source_fingerprint(p)] for p in selected
                            if source_fingerprint(p) in result.summary_sources]
        checkpoint()
    if not result.summaries:
        warn("No structured summaries were produced.")
        return result
    result.warnings = [w for w in result.warnings if w != "No structured summaries were produced."]

    def stage(name, attribute, operation):
        if getattr(result, attribute) is None:
            result.warnings = [w for w in result.warnings if not w.startswith(name + " unavailable:")]
            try:
                value = operation()
                if value is None:
                    raise RuntimeError("The analysis stage returned no result.")
                setattr(result, attribute, value)
                result.stage_errors.pop(name, None)
            except Exception as exc:
                result.stage_errors[name] = f"{type(exc).__name__}: {exc}"
                warn(name + " unavailable: " + str(exc))
            checkpoint()

    if include_thematic_review:
        def thematic():
            if workflow.thematic_reviewer is None:
                workflow.thematic_reviewer = ThematicLiteratureReviewer()
            return workflow.thematic_reviewer.review(topic=result.topic, summaries=result.summaries)
        stage("thematic_review", "thematic_review", thematic)
    if len(result.summaries) >= 2:
        result.warnings = [w for w in result.warnings if w != "At least two summaries are required for methodology comparison."]
        stage("comparison", "comparison", lambda: workflow.comparator.compare(result.topic, result.summaries))
    else:
        warn("At least two summaries are required for methodology comparison.")
    stage("gap_report", "gap_report", lambda: workflow.gap_identifier.identify(result.topic, result.summaries))
    if result.gap_report is not None:
        stage("proposal", "proposal", lambda: workflow.objective_generator.generate(result.gap_report))
    return result
