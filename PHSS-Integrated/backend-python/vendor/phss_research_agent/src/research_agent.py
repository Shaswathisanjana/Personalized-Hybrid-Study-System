
"""PHSS Research Agent: full-text PDF section analysis and printable Word report."""

import json
import os
from datetime import datetime

from .arxiv_search import search_arxiv, get_cached_embedder, is_survey_paper, clean_research_topic
from .semantic_scholar_search import search_semantic_scholar
from .embeddings import BGEEmbedder
from .text_processing import extract_candidate_sentences
from .analysis import build_evidence_clusters
from .gemini_synthesis import GeminiSynthesizer
from .paper_analysis import PaperAnalyzer
from .pdf_sections import PDFSectionExtractor
from .report_generator import WordResearchReportGenerator
from .config import OUTPUT_DIR, EMBEDDING_MODEL
from .agentic_controller import AgenticResearchController
from .limitation_verifier import LimitationVerifier


class ResearchAgent:
    @staticmethod
    def _normalize_paper_record(paper):
        """Convert arXiv Result objects to the dictionary format used downstream."""
        if isinstance(paper, dict):
            record = dict(paper)
            record.setdefault("title", "Untitled")
            record.setdefault("abstract", "")
            record.setdefault("authors", [])
            record.setdefault("url", "")
            record.setdefault("pdf_url", None)
            if not record.get("pdf_url"):
                url = record.get("url") or ""
                if "arxiv.org/abs/" in url:
                    record["pdf_url"] = url.replace("/abs/", "/pdf/") + ".pdf"
                elif record.get("external_ids", {}).get("ArXiv"):
                    record["pdf_url"] = f"https://arxiv.org/pdf/{record['external_ids']['ArXiv']}.pdf"
            # Preserve provider metadata and supply a consistent publication field.
            if not record.get("published") and record.get("year"):
                record["published"] = f"{record['year']}-01-01"
            return record

        title = getattr(paper, "title", None)
        summary = getattr(paper, "summary", None)
        authors = getattr(paper, "authors", []) or []
        published = getattr(paper, "published", None)
        updated = getattr(paper, "updated", None)

        return {
            "title": title.strip() if isinstance(title, str) else (title or "Untitled"),
            "abstract": summary.strip() if isinstance(summary, str) else (summary or ""),
            "authors": [getattr(author, "name", str(author)) for author in authors],
            "published": published.isoformat() if published else None,
            "updated": updated.isoformat() if updated else None,
            "url": getattr(paper, "entry_id", "") or "",
            "pdf_url": getattr(paper, "pdf_url", None),
        }

    def _search_with_fallback(self, query, max_papers):
        """Search arXiv first; use Semantic Scholar only if arXiv fails or yields no usable papers."""
        arxiv_error = None
        arxiv_papers = []

        try:
            arxiv_papers = search_arxiv(query, max_papers)
            arxiv_papers = [
                self._normalize_paper_record(paper)
                for paper in (arxiv_papers or [])
            ]
            arxiv_papers = [
                paper for paper in arxiv_papers
                if not is_survey_paper(
                    str(paper.get("title", "")),
                    str(paper.get("abstract", "")),
                )
            ]
        except Exception as exc:
            arxiv_error = exc
            print(f"  arXiv search failed: {exc}")

        if arxiv_papers:
            for paper in arxiv_papers:
                paper.setdefault("source", "arXiv")
            return arxiv_papers[:max_papers]

        reason = f" ({arxiv_error})" if arxiv_error else " (no usable papers returned)"
        print("  Trying Semantic Scholar fallback" + reason + "...")

        try:
            # The API search is bounded to at most 50 candidates. Its helper
            # filters likely review papers, deduplicates, and ranks candidates.
            candidates = search_semantic_scholar(
                query,
                limit=50,
                exclude_reviews=True,
            )
            candidates = [
                self._normalize_paper_record(paper)
                for paper in (candidates or [])
            ]
            # Apply the project's existing review filter as a second safety net.
            candidates = [
                paper for paper in candidates
                if not is_survey_paper(
                    str(paper.get("title", "")),
                    str(paper.get("abstract", "")),
                )
            ]
            if candidates:
                selected = candidates[:max_papers]
                for paper in selected:
                    paper.setdefault("source", "Semantic Scholar")
                print(
                    f"  Semantic Scholar fallback selected {len(selected)} "
                    f"paper(s) from {len(candidates)} eligible candidate(s)."
                )
                return selected
        except Exception as exc:
            print(f"  Semantic Scholar fallback failed: {exc}")

        return []

    def __init__(self):
        self.embedder = None
        # Uses Groq internally; the class name is retained for compatibility.
        self.synthesizer = GeminiSynthesizer()
        self.paper_analyzer = PaperAnalyzer()
        self.pdf_section_extractor = PDFSectionExtractor()
        self.word_report_generator = WordResearchReportGenerator()
        self.limitation_verifier = LimitationVerifier()
        self.agentic_controller = AgenticResearchController(
            max_adaptive_searches=int(os.getenv("PHSS_MAX_ADAPTIVE_SEARCHES", "1")),
            min_topic_overlap=float(os.getenv("PHSS_MIN_TOPIC_OVERLAP", "0.20")),
            min_relevance_score=float(os.getenv("ARXIV_MIN_RELEVANCE", "0.30")),
            min_relevant_ratio=float(os.getenv("PHSS_MIN_RELEVANT_RATIO", "0.60")),
        )

    def run(self, topic, max_papers=10, generate_docx=True):
        topic = clean_research_topic(topic)
        print("\n" + "=" * 70)
        print("PHSS RESEARCH AGENT")
        print("=" * 70)
        print("Topic:", topic)

        # STEP 1: Plan, retrieve, evaluate, and adapt once if evidence is weak.
        print("\n[1/8] Planning research and searching arXiv...")
        max_papers = max(1, min(int(max_papers), 10))
        agentic_plan = self.agentic_controller.create_plan(topic, max_papers)
        agentic_trace = []
        self.agentic_controller.record_action(
            agentic_trace, "plan_created",
            "Created evidence targets and a bounded search budget.",
            {"evidence_targets": agentic_plan["evidence_targets"],
             "adaptive_search_budget": agentic_plan["adaptive_search_budget"]},
        )

        papers = self._search_with_fallback(topic, max_papers)

        # IMPORTANT: score the initial candidates against the original topic too.
        # Previously, semantic re-ranking happened only after an adaptive search,
        # so a full initial result set could pass without per-paper relevance checks.
        try:
            embedder = get_cached_embedder()
            papers = self.agentic_controller.rerank_for_original_topic(
                topic, papers, embedder
            )
        except Exception as exc:
            print(f"  Initial semantic re-ranking skipped: {exc}")

        retrieval_evaluation = self.agentic_controller.evaluate_retrieval(
            topic, papers, max_papers
        )
        self.agentic_controller.record_action(
            agentic_trace, "initial_retrieval_evaluated",
            "Evaluated paper count, semantic relevance, and topic-token coverage.",
            retrieval_evaluation,
        )

        adaptive_searches_used = 0
        if retrieval_evaluation["needs_adaptation"] and agentic_plan["adaptive_search_budget"] > 0:
            adaptive_query = self.agentic_controller.choose_adaptive_query(topic, papers)
            print("\n  Agentic evaluator found weak retrieval; trying one targeted query:")
            print(" ", adaptive_query)
            adaptive_searches_used += 1
            try:
                additional = self._search_with_fallback(adaptive_query, max_papers)
                merged = self.agentic_controller.merge_unique(papers, additional)
                # Safety net: adaptive results must obey the same review-paper policy.
                before_filter = len(merged)
                merged = [
                    p for p in merged
                    if not is_survey_paper(
                        str(p.get("title", "")), str(p.get("abstract", ""))
                    )
                ]
                removed_reviews = before_filter - len(merged)
                if removed_reviews:
                    print(f"  Removed {removed_reviews} survey/review paper(s) after merging searches.")
                if merged:
                    embedder = get_cached_embedder()
                    merged = self.agentic_controller.rerank_for_original_topic(
                        topic, merged, embedder
                    )
                    threshold = float(os.getenv("ARXIV_MIN_RELEVANCE", "0.30"))
                    filtered = [
                        p for p in merged
                        if float(p.get("relevance_score", 0.0) or 0.0) >= threshold
                    ][:max_papers]
                    # Do not turn a weak search into a total failure: if every
                    # candidate falls below the heuristic threshold, retain the
                    # best-ranked candidates and record the caveat instead.
                    papers = filtered if filtered else merged[:max_papers]
                else:
                    papers = merged
                retrieval_evaluation = self.agentic_controller.evaluate_retrieval(
                    topic, papers, max_papers
                )
                self.agentic_controller.record_action(
                    agentic_trace, "adaptive_search_completed",
                    "Ran one bounded supplementary search and re-ranked against the original topic.",
                    {"query": adaptive_query, "new_candidates": len(additional),
                     "evaluation_after_search": retrieval_evaluation},
                )
            except Exception as exc:
                # Keep the initial results when the supplementary request fails (e.g. HTTP 429).
                self.agentic_controller.record_action(
                    agentic_trace, "adaptive_search_failed",
                    "Supplementary search failed; retained the initial results.",
                    {"query": adaptive_query, "error": str(exc)},
                )
                print(f"  Supplementary search failed; continuing with current results: {exc}")

        # Final safety net before any PDF download, analysis, diagrams, or references.
        before_final_filter = len(papers)
        papers = [
            p for p in papers
            if not is_survey_paper(
                str(p.get("title", "")), str(p.get("abstract", ""))
            )
        ]
        if before_final_filter != len(papers):
            print(f"  Final filter removed {before_final_filter - len(papers)} survey/review paper(s).")

        if not papers:
            raise RuntimeError(
                "No relevant original-research papers were retrieved from arXiv "
                "or Semantic Scholar after the bounded search. Try a broader topic, "
                "check your Semantic Scholar API configuration, or retry later."
            )

        self.agentic_controller.record_action(
            agentic_trace, "retrieval_stopped",
            "Stopped retrieval because the adaptive-search budget is exhausted or results are sufficient.",
            {"adaptive_searches_used": adaptive_searches_used,
             "final_retrieval_evaluation": retrieval_evaluation},
        )

        for i, paper in enumerate(papers, 1):
            print(f"  {i}. {paper.get('title', 'Untitled')}")

        # STEP 2: Download PDFs and extract sections.
        print("\n[2/8] Downloading PDFs and detecting paper sections...")
        papers = self.pdf_section_extractor.extract_papers(papers)

        # STEP 3: Extract structured information from full text.
        print(
            "\n[3/8] Extracting methodology, datasets, results, "
            "limitations, and future work..."
        )
        paper_analyses = self.paper_analyzer.analyze_papers(topic, papers)

        # STEP 3B: bounded follow-up search for limitations. This retrieves candidates;
        # it intentionally does not claim a limitation is resolved without full-text evidence.
        limitation_verification = {"enabled": False, "reason": "not_run"}
        if os.getenv("PHSS_ENABLE_LIMITATION_VERIFICATION", "1").lower() in {"1", "true", "yes"}:
            print("\n[3B] Verifying limitations with a bounded follow-up search budget...")
            try:
                limitation_verification = self.limitation_verifier.verify(topic, paper_analyses)
                print(
                    "  Limitation verification search rounds:",
                    limitation_verification.get("total_search_rounds_used", 0),
                    "| unique follow-up papers:",
                    limitation_verification.get("total_unique_followup_papers", 0),
                )
            except Exception as exc:
                limitation_verification = {"enabled": False, "error": str(exc)}
                print("  Limitation verification skipped due to error:", exc)

        extraction_evaluation = self.agentic_controller.evaluate_extraction(paper_analyses)
        self.agentic_controller.record_action(
            agentic_trace, "extraction_quality_evaluated",
            "Checked reported-field completeness without filling missing values by guesswork.",
            extraction_evaluation,
        )

        # STEP 4: Extract candidate evidence sentences.
        print("\n[4/8] Extracting limitation/challenge evidence...")
        candidates = []
        source_indices = []

        for paper_idx, paper in enumerate(papers):
            for sentence in extract_candidate_sentences(paper):
                candidates.append(sentence)
                source_indices.append(paper_idx)

        print("  Candidate evidence sentences:", len(candidates))

        # STEP 5: Generate BGE embeddings and cluster evidence.
        evidence_clusters = []

        if candidates:
            print("\n[5/8] Generating BGE embeddings and clustering evidence...")
            # Reuse the BGE model already loaded during semantic paper ranking.
            self.embedder = get_cached_embedder()

            sentence_embeddings = self.embedder.embed_documents(candidates)
            query_embedding = self.embedder.embed_query(topic)

            evidence_clusters = build_evidence_clusters(
                candidates,
                sentence_embeddings,
                query_embedding,
                source_indices,
            )

            for cluster in evidence_clusters:
                for evidence in cluster.get("evidence", []):
                    paper_index = evidence.get("paper_index")

                    if (
                        paper_index is not None
                        and 0 <= paper_index < len(papers)
                    ):
                        evidence["paper_title"] = papers[paper_index].get(
                            "title", "Unknown"
                        )
                        evidence["paper_url"] = papers[paper_index].get(
                            "url", ""
                        )
        else:
            print(
                "\n[5/8] No limitation sentences were extracted; "
                "skipping embedding/clustering."
            )

        # STEP 6: Synthesize potential research gaps using Groq.
        print("\n[6/8] Synthesizing potential research gaps with Groq...")
        synthesis = (
            self.synthesizer.synthesize(
                topic,
                papers,
                evidence_clusters,
            )
            if evidence_clusters
            else None
        )

        print(
            "  Gap synthesis generated."
            if synthesis
            else "  Gap synthesis unavailable."
        )

        # STEP 7: Save the structured JSON report.
        print("\n[7/8] Saving structured JSON report...")
        report = self.make_report(
            topic,
            papers,
            paper_analyses,
            evidence_clusters,
            synthesis,
        )

        report["limitation_verification"] = limitation_verification

        report["agentic_controller"] = {
            "enabled": True,
            "plan": agentic_plan,
            "retrieval_evaluation": retrieval_evaluation,
            "extraction_quality": extraction_evaluation,
            "trace": agentic_trace,
            "adaptive_searches_used": adaptive_searches_used,
            "decision": (
                "proceed_with_caveats"
                if extraction_evaluation["missing_field_count"] > 0 or retrieval_evaluation["needs_adaptation"]
                else "proceed"
            ),
        }
        self.save(report)
        self.save_extracted_sections(papers)

        print("Saved JSON:", OUTPUT_DIR / "latest_report.json")
        print("Saved extracted sections:", OUTPUT_DIR / "extracted_paper_sections.json")

        # STEP 8: Generate a printable Word report.
        if generate_docx:
            print("\n[8/8] Generating Word research report...")

            docx_path = self.word_report_generator.generate(
                topic=topic,
                paper_analyses=paper_analyses,
                gap_synthesis=synthesis,
                evidence_clusters=evidence_clusters,
            )

            report["word_report_path"] = str(docx_path)
            self.save(report)

            print("Saved Word report:", docx_path)

        return report

    def make_report(
        self,
        topic,
        papers,
        paper_analyses,
        evidence_clusters,
        synthesis,
    ):
        """Create the structured report without storing full PDF text."""

        paper_records = []

        for paper in papers:
            record = {
                key: value
                for key, value in paper.items()
                if key not in ("full_text", "sections")
            }

            record["section_sources"] = {
                category: [
                    {
                        "heading": section.get("heading"),
                        "start_page": section.get("start_page"),
                        "end_page": section.get("end_page"),
                    }
                    for section in entries
                ]
                for category, entries in (paper.get("sections") or {}).items()
            }

            paper_records.append(record)

        return {
            "generated_at": datetime.now().isoformat(),
            "topic": topic,
            "data_source": (
                "arXiv metadata, abstracts, and downloaded full-text PDFs "
                "where extraction succeeded"
            ),
            "number_of_papers": len(papers),
            "embedding_model": EMBEDDING_MODEL,
            "methodology": {
                "paper_analysis": (
                    "PDF section detection and structured extraction "
                    "from available full-text sections"
                ),
                "evidence_extraction": (
                    "Limitation, challenge, and future-work sentence "
                    "extraction using predefined patterns"
                ),
                "embedding": EMBEDDING_MODEL,
                "semantic_analysis": (
                    "Cosine similarity and agglomerative semantic clustering"
                ),
                "cross_paper_analysis": (
                    "Paper coverage within semantic evidence clusters"
                ),
                "gap_synthesis": (
                    "Groq synthesis of candidate research gaps from "
                    "extracted evidence; not a novelty verification"
                ),
            },
            "papers": paper_records,
            "paper_analyses": paper_analyses,
            "semantic_evidence_clusters": evidence_clusters,
            "research_gap_synthesis": synthesis,
            "limitations": [
                (
                    "PDF download or text extraction may fail for some "
                    "papers; check each paper's full_text_extracted status."
                ),
                (
                    "Section detection may miss unusual headings or confuse "
                    "combined sections. Detected headings and page ranges "
                    "are retained where available."
                ),
                (
                    "Information not explicitly reported in extracted text "
                    "may be omitted, especially for scanned PDFs or "
                    "incomplete extraction."
                ),
                (
                    "Potential gaps and novelty directions are not verified "
                    "novelty claims and require a broader literature review."
                ),
            ],
        }

    @staticmethod
    def save(report):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        output_path = OUTPUT_DIR / "latest_report.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

    @staticmethod
    def save_extracted_sections(papers):
        """Persist extracted paper sections for audit and reuse."""

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        records = []

        for paper in papers:
            records.append(
                {
                    "title": paper.get("title"),
                    "url": paper.get("url"),
                    "pdf_path": paper.get("pdf_path"),
                    "full_text_extracted": paper.get(
                        "full_text_extracted", False
                    ),
                    "pdf_extraction_error": paper.get(
                        "pdf_extraction_error"
                    ),
                    "sections": paper.get("sections", {}),
                }
            )

        output_path = OUTPUT_DIR / "extracted_paper_sections.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(
                records,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

    def run_interactive(self):
        topic = input("\nEnter your research topic: ").strip()

        if not topic:
            print("Topic cannot be empty.")
            return None

        raw_count = input(
            "Number of papers (1-10, default 10): "
        ).strip()

        try:
            count = int(raw_count) if raw_count else 10
        except ValueError:
            count = 10

        try:
            return self.run(
                topic,
                max_papers=max(1, min(count, 10)),
            )
        except Exception as exc:
            print("\nERROR:", exc)
            print(
                "Check your API key, internet connection, dependencies, "
                "and configuration."
            )
            return None


if __name__ == "__main__":
    ResearchAgent().run_interactive()