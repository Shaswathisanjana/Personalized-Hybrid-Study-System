"""Evidence-grounded paper analysis with per-field BGE retrieval and Groq synthesis."""

from __future__ import annotations

import json

import os

import re

import time

from dotenv import load_dotenv

try:

    from groq import Groq

except ImportError:

    Groq = None

from .config import GROQ_MODEL, EMBEDDING_MODEL
from .embeddings import get_embedding_model

load_dotenv()

MISSING = "Not explicitly reported in full text"

FIELD_CONFIG = {

    "methodology": {

        "categories": ("methodology", "approach", "methods"),

        "query": "research methodology model architecture algorithm procedure experimental setup",

        "top_k": 4,

    },

    "dataset": {

        "categories": ("dataset", "experimental_setup", "evaluation", "data collection"),

        "query": "dataset name source number of samples images PCBs annotations labels classes data collection",

        "top_k": 4,

    },

    "results_metrics": {

        "categories": ("results", "evaluation", "experiments", "dataset", "data collection", "discussion", "conclusion"),

        "query": "results findings quantitative results accuracy precision recall F1 score mAP metrics comparison dataset statistics number of images PCBs samples annotations total unique instances comparison with prior datasets demonstrated capabilities",

        "top_k": 5,

    },

    "author_stated_limitations": {

        "categories": ("limitations", "discussion", "conclusion"),

        "query": "explicit author acknowledged limitations weaknesses constraints",

        "top_k": 3,

    },

    "future_work": {

        "categories": ("future_work", "conclusion", "discussion"),

        "query": "future work future directions planned improvements stated by authors",

        "top_k": 3,

    },

}

def _clean_json_response(text: str) -> str:

    text = (text or "").strip()

    text = re.sub(r"^\`\`\`(?:json)?\s*", "", text, flags=re.I)

    text = re.sub(r"\s*\`\`\`$", "", text)

    start, end = text.find("{"), text.rfind("}")

    return text[start:end + 1] if start >= 0 and end > start else text

def _as_text(value, fallback=MISSING) -> str:

    if value is None:

        return fallback

    if isinstance(value, list):

        value = "; ".join(

            str(item).strip() for item in value if str(item).strip()

        )

    value = re.sub(r"\s+", " ", str(value)).strip()

    return value or fallback

def _split_chunks(text: str, size: int = 1000, overlap: int = 140):

    """Split section text into overlapping chunks."""

    text = re.sub(r"\s+", " ", text or "").strip()

    chunks = []

    start = 0

    while start < len(text):

        end = min(start + size, len(text))

        if end < len(text):

            boundary = max(

                text.rfind(". ", start, end),

                text.rfind("; ", start, end),

            )

            if boundary > start + size // 2:

                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:

            chunks.append(chunk)

        if end >= len(text):

            break

        start = max(end - overlap, start + 1)

    return chunks

def _is_noisy_summary(value: str) -> bool:
    """Reject obvious numeric/OCR dumps without discarding valid summaries."""
    value = re.sub(r"\s+", " ", value or "").strip()
    if not value or value == MISSING:
        return False
    numeric_tokens = re.findall(r"(?<![A-Za-z])(?:\d+\.\d+|\d+%?)(?![A-Za-z])", value)
    words = re.findall(r"[A-Za-z]{3,}", value)
    if len(numeric_tokens) >= 10 and len(numeric_tokens) > max(2, len(words) * 0.8):
        return True
    if re.search(r"(?:\b(?:0?\.\d{2,}\s+){5,}0?\.\d{2,})", value):
        return True
    if value.count("|") > 8 or value.count("[") > 8:
        return True
    return False
def _is_reference_material(text: str, heading: str = "") -> bool:

    """Reject bibliography headings and chunks dominated by citation records."""

    heading_text = re.sub(

        r"[^a-z ]", " ", str(heading).lower()

    ).strip()

    if re.search(

        r"\b(references|bibliography|works cited|literature cited)\b",

        heading_text,

    ):

        return True

    text = text or ""

    if not text.strip():

        return True

    # Count common citation patterns. Keep this regex valid in Python.

    citation_pattern = (

        r"https?://"

        r"|doi\s*:"

        r"|arxiv\s*:\s*\d"

        r"|\bvol\.\s*\d"

        r"|\bpp?\.\s*\d"

        r"|\bet al\."

    )

    citation_signals = len(

        re.findall(citation_pattern, text, flags=re.IGNORECASE)

    )

    sentences = re.findall(r"[^.!?]+[.!?]", text)

    # Reference lists often contain many citation patterns and little

    # explanatory prose. Avoid rejecting normal technical paragraphs

    # merely because they cite one or two sources.

    if citation_signals >= 3 and len(text) < 1800:

        return True

    if (

        len(sentences) >= 4

        and citation_signals / max(len(sentences), 1) >= 0.75

    ):

        return True

    return False

def _is_low_quality_evidence(text: str, heading: str = "") -> bool:

    """Reject fragments, captions, and flattened table/OCR material before retrieval."""

    text = re.sub(r"\s+", " ", text or "").strip()

    heading = re.sub(r"\s+", " ", str(heading or "")).strip().lower()

    if not text or _is_reference_material(text, heading):

        return True

    if len(text) < 90:

        return True

    if re.match(r"^(fig(?:ure)?|table|algorithm|listing)\s*\d*\s*[:.\-]", text, re.I):

        return True

    if re.search(r"\b(acknowledg(e)?ments?|author contributions?|conflict of interest|funding statement)\b", heading):

        return True

    numbers = re.findall(r"(?<![A-Za-z])(?:\d+\.\d+|\d+%?)(?![A-Za-z])", text)

    words = re.findall(r"[A-Za-z]{3,}", text)

    if len(numbers) >= 7 and len(numbers) > max(2, len(words) * 0.65):

        return True

    if len(re.findall(r"[.!?]", text)) == 0 and len(words) < 16:

        return True

    return False

def _looks_unsupported_or_fragmentary(value: str) -> bool:

    """Catch obviously incomplete outputs without attempting factual verification."""

    value = re.sub(r"\s+", " ", value or "").strip()

    if not value or value == MISSING:

        return False

    words = re.findall(r"[A-Za-z]{3,}", value)

    if len(value) < 35 and len(words) < 6:

        return True

    if re.match(r"^(?:and|or|but|with|using|which|where|because)\b", value, re.I):

        return True

    if re.search(r"(?:\b\d+(?:\.\d+)?\s+){5,}\d+(?:\.\d+)?$", value):

        return True

    return False

def _category_matches(category: str, aliases: tuple[str, ...]) -> bool:

    category = re.sub(r"[^a-z0-9]+", "_", str(category).lower()).strip("_")

    return any(alias == category or alias in category for alias in aliases)

class PaperAnalyzer:

    """Retrieve relevant paper chunks and synthesize concise factual fields."""

    def __init__(self):

        key = os.getenv("GROQ_API_KEY")

        self.client = (

            Groq(api_key=key)

            if key and Groq is not None

            else None

        )

        if key and Groq is None:

            print("Groq SDK unavailable. Install it with: pip install groq")

        self.embedder = None

        self.embedder_attempted = False

    def _get_embedder(self):

        if self.embedder_attempted:

            return self.embedder

        self.embedder_attempted = True

        try:

            self.embedder = get_embedding_model()

            print("Using lightweight lexical research retrieval (no model weights).")

        except Exception as exc:

            print(f"Lexical vector retrieval unavailable; using keyword retrieval: {exc}")

        return self.embedder

    @staticmethod

    def _build_chunks(paper: dict) -> list[dict]:

        """Create chunks while preserving section headings and page ranges."""

        chunks = []

        for category, entries in (paper.get("sections") or {}).items():

            for entry in entries or []:

                heading = str(entry.get("heading") or category)

                section_text = str(entry.get("text") or "").strip()

                # IMPORTANT: do not call _is_reference_material with an

                # empty string. Empty text is classified as reference

                # material, which would incorrectly discard every section.

                if not section_text:

                    continue

                if _is_reference_material(section_text, heading):

                    continue

                for chunk_index, text in enumerate(_split_chunks(section_text)):

                    if not text.strip():

                        continue

                    if _is_reference_material(text, heading):

                        continue

                    chunks.append({

                        "category": str(category).lower(),

                        "heading": heading,

                        "start_page": entry.get("start_page", "?"),

                        "end_page": entry.get(

                            "end_page", entry.get("start_page", "?")

                        ),

                        "chunk_index": chunk_index,

                        "text": text,

                    })

        # Abstract is only a supplementary source.

        abstract = paper.get("abstract", "")

        for chunk_index, text in enumerate(

            _split_chunks(abstract, size=800, overlap=100)

        ):

            if not text.strip():

                continue

            chunks.append({

                "category": "abstract",

                "heading": "Abstract",

                "start_page": "?",

                "end_page": "?",

                "chunk_index": chunk_index,

                "text": text,

            })

        return chunks

    def _retrieve(

        self,

        chunks: list[dict],

        field: str,

        shared_chunk_vectors=None,

    ) -> list[dict]:

        """Retrieve field-specific evidence across usable full-text sections."""

        config = FIELD_CONFIG[field]

        categories = tuple(config["categories"])

        # Search all usable full-text sections. A section detector may label

        # headings differently from the aliases in FIELD_CONFIG, so section

        # names are a ranking hint rather than a hard filter.

        full_text_chunks = [

            chunk for chunk in chunks

            if chunk.get("category") != "abstract"

            and chunk.get("text", "").strip()

            and not _is_reference_material(

                chunk.get("text", ""), chunk.get("heading", "")

            )

        ]

        if not full_text_chunks:

            return []

        model = self._get_embedder()

        ranked = []

        if model is not None:

            try:

                if shared_chunk_vectors is not None:

                    query_vector = model.encode(

                        [config["query"]],

                        normalize_embeddings=True,

                        show_progress_bar=False,

                    )[0]

                    scores = shared_chunk_vectors @ query_vector

                else:

                    texts = [chunk["text"] for chunk in full_text_chunks]

                    vectors = model.encode(

                        [config["query"]] + texts,

                        normalize_embeddings=True,

                        show_progress_bar=False,

                    )

                    scores = vectors[1:] @ vectors[0]

                for chunk, score in zip(full_text_chunks, scores):

                    category_match = (

                        _category_matches(chunk.get("category", ""), categories)

                        or _category_matches(chunk.get("heading", ""), categories)

                    )

                    semantic_score = float(score)

                    ranked.append({

                        **chunk,

                        "retrieval_score": round(semantic_score, 4),

                        "_rank_score": semantic_score + (0.08 if category_match else 0.0),

                    })

            except Exception as exc:

                print(

                    f"Embedding retrieval failed for {field}; "

                    f"using lexical retrieval: {exc}"

                )

                ranked = []

        if not ranked:

            terms = set(re.findall(r"[a-z0-9]+", config["query"].lower()))

            for chunk in full_text_chunks:

                combined = (

                    chunk.get("heading", "") + " "

                    + chunk.get("category", "") + " "

                    + chunk.get("text", "")

                ).lower()

                lexical_score = sum(term in combined for term in terms)

                category_match = (

                    _category_matches(chunk.get("category", ""), categories)

                    or _category_matches(chunk.get("heading", ""), categories)

                )

                ranked.append({

                    **chunk,

                    "retrieval_score": lexical_score,

                    "_rank_score": lexical_score + (2 if category_match else 0),

                })

        ranked.sort(key=lambda item: item["_rank_score"], reverse=True)

        # Avoid returning duplicate chunks and keep the output compact.

        selected = []

        seen_text = set()

        for chunk in ranked:

            normalized = re.sub(r"\s+", " ", chunk.get("text", "")).strip().lower()

            if not normalized or normalized in seen_text:

                continue

            seen_text.add(normalized)

            selected.append({

                key: value for key, value in chunk.items()

                if key != "_rank_score"

            })

            if len(selected) >= config["top_k"]:

                break

        return selected

    def analyze_papers(

        self,

        topic: str,

        papers: list[dict],

    ) -> list[dict]:

        """Analyze papers using retrieved evidence from extracted PDF sections."""

        results = []

        for index, paper in enumerate(papers, 1):

            print(

                f"  Analyzing paper {index}/{len(papers)}: "

                f"{paper.get('title', 'Untitled')}"

            )

            chunks = self._build_chunks(paper)

            has_full_text = any(

                chunk.get("category") != "abstract"

                and chunk.get("text", "").strip()

                for chunk in chunks

            )

            # The flag can be false or absent even when sections contain text.

            extraction_ok = bool(paper.get("full_text_extracted") or has_full_text)

            # Encode each full-text chunk once per paper, then reuse its
            # vector for all five field-specific retrieval queries.
            retrieval_chunks = [

                chunk for chunk in chunks

                if chunk.get("category") != "abstract"

                and chunk.get("text", "").strip()

                and not _is_reference_material(

                    chunk.get("text", ""), chunk.get("heading", "")

                )

            ]

            shared_chunk_vectors = None

            model = self._get_embedder() if retrieval_chunks else None

            if model is not None and retrieval_chunks:

                try:

                    shared_chunk_vectors = model.encode(

                        [chunk["text"] for chunk in retrieval_chunks],

                        normalize_embeddings=True,

                        show_progress_bar=False,

                        batch_size=32,

                    )

                except Exception as exc:

                    print(

                        "Shared embedding failed; falling back to "

                        f"field-specific retrieval: {exc}"

                    )

                    shared_chunk_vectors = None

            retrieved = {

                field: self._retrieve(

                    chunks,

                    field,

                    shared_chunk_vectors=shared_chunk_vectors,

                )

                for field in FIELD_CONFIG

            }

            record = {

                "paper_index": index,

                "title": paper.get("title") or "Untitled",

                "authors": paper.get("authors") or [],

                "year": (paper.get("published") or "")[:4] or MISSING,

                "published": paper.get("published"),

                "abstract": paper.get("abstract") or "",

                "url": paper.get("url") or "",

                "pdf_url": paper.get("pdf_url") or "",

                "pdf_path": paper.get("pdf_path"),

                "full_text_extracted": extraction_ok,

                "section_sources": {

                    category: [

                        {

                            "heading": item.get("heading"),

                            "start_page": item.get("start_page"),

                            "end_page": item.get("end_page"),

                        }

                        for item in entries

                    ]

                    for category, entries in (paper.get("sections") or {}).items()

                },

                "retrieved_evidence": {

                    field: [

                        {

                            "heading": chunk.get("heading", ""),

                            "pages": (

                                f"{chunk.get('start_page', '?')}-"

                                f"{chunk.get('end_page', '?')}"

                            ),

                            "text": chunk.get("text", ""),

                            **(

                                {"retrieval_score": chunk["retrieval_score"]}

                                if "retrieval_score" in chunk else {}

                            ),

                        }

                        for chunk in selected

                    ]

                    for field, selected in retrieved.items()

                },

            }

            if not extraction_ok or not chunks:
                abstract_text = (record.get("abstract") or "").strip()
                if abstract_text and len(abstract_text) > 40 and self.client:
                    print("  Note: Full-text PDF was unavailable; extracting methodology, dataset & results from abstract.")
                    abstract_chunk = [{"heading": "Abstract", "pages": "1", "text": abstract_text}]
                    abstract_retrieved = {field: abstract_chunk for field in FIELD_CONFIG}
                    parsed = self._ask_groq(self._build_prompt(topic, record, abstract_retrieved))
                    if parsed:
                        for field in FIELD_CONFIG:
                            value = _as_text(parsed.get(field))
                            if _is_noisy_summary(value):
                                value = MISSING
                            record[field] = value
                        gap = _as_text(parsed.get("potential_gap_from_evidence"))
                        record["potential_gap_from_evidence"] = MISSING if _is_noisy_summary(gap) else gap
                    else:
                        for field in FIELD_CONFIG:
                            record[field] = MISSING
                        record["potential_gap_from_evidence"] = MISSING
                else:
                    print("  Warning: no usable extracted full-text sections or abstract found.")
                    for field in FIELD_CONFIG:
                        record[field] = MISSING
                    record["potential_gap_from_evidence"] = MISSING

            elif self.client:

                parsed = self._ask_groq(

                    self._build_prompt(topic, record, retrieved)

                )

                if parsed:

                    for field in FIELD_CONFIG:

                        value = _as_text(parsed.get(field))

                        if _is_noisy_summary(value):

                            print(f"  Rejected noisy Groq output for field: {field}")

                            value = MISSING

                        record[field] = value

                    gap = _as_text(parsed.get("potential_gap_from_evidence"))

                    record["potential_gap_from_evidence"] = (

                        MISSING if _is_noisy_summary(gap) else gap

                    )

                else:

                    print("  Groq synthesis failed; using retrieved evidence.")

                    self._fallback_fields(record, retrieved)

            else:

                print(

                    "  Groq unavailable; using retrieved source excerpts "

                    "instead of generated summaries."

                )

                self._fallback_fields(record, retrieved)

            record["potential_gap_from_abstract"] = record.get(

                "potential_gap_from_evidence", MISSING

            )

            results.append(record)

        return results

    @staticmethod

    def _build_prompt(topic, record, retrieved) -> str:

        """Ask for concise table-ready summaries grounded in source excerpts."""

        evidence = {

            field: [

                {

                    "heading": chunk.get("heading", ""),

                    "pages": f"{chunk.get('start_page', '?')}-{chunk.get('end_page', '?')}",

                    "text": chunk.get("text", ""),

                }

                for chunk in selected

            ]

            for field, selected in retrieved.items()

        }

        return f"""

You are extracting evidence for a research literature comparison table.

Research topic: {topic}

Paper: {record.get('title', 'Untitled')}

SOURCE RULES:

- Use only the supplied evidence. Do not use outside knowledge or guess.

- Read the evidence as source excerpts, not as ready-made answers. Identify whether the paper is primarily a model/experiment paper, a dataset/resource paper, or a survey; choose result types appropriate to that contribution.

- Ignore reference lists, citations, headers/footers, OCR fragments, and unrelated text.

- Never copy a long passage verbatim. Paraphrase the supported information.

- Do not combine numbers unless the source explicitly associates them with a metric.

- If a result table is flattened and the metric/value pairing is unclear, state that the metric/value pairing could not be reliably extracted rather than listing a string of numbers.

- Author-stated limitations must be explicit in the paper. Do not invent a limitation.

- A potential gap may be inferred cautiously from the supplied evidence, but label it as a potential gap, not an author claim.

TABLE CELL STYLE:

- methodology: 1-2 concise sentences describing the actual approach/model and how it works.

- dataset: dataset name, source, and size/classes/split only if explicitly available; 1-2 sentences.

- results_metrics: report the paper's actual outcomes in up to 3 concise sentences. For model/experiment papers, include metric:value pairs only when clearly supported. For dataset/resource papers, results may be dataset statistics (such as number of images, boards, samples, annotations, classes, or unique instances), comparisons with prior datasets, and capabilities demonstrated or enabled. Do not mark results missing just because accuracy/precision/recall are not reported. Never output unlabeled numeric sequences.

- author_stated_limitations: 1-2 concise sentences containing only explicitly stated limitations.

- future_work: concise statement of explicitly proposed future work, or the exact missing marker.

- potential_gap_from_evidence: 1-2 careful sentences grounded in evidence. If evidence is insufficient, use the exact missing marker.

All fields must be short, readable, self-contained, and specific to this paper. Avoid repetition across fields. Do not output raw table dumps, OCR noise, incomplete sentence fragments, or multiple unrelated paragraphs.

Return a valid JSON object only with these keys:

methodology, dataset, results_metrics, author_stated_limitations, future_work, potential_gap_from_evidence.

For unsupported fields, return exactly: {MISSING}

Retrieved source evidence:

{json.dumps(evidence, ensure_ascii=False)}

"""

    def _ask_groq(self, prompt: str):

        """Generate evidence-grounded paper analysis using Groq."""

        if not self.client:

            return None

        for attempt in range(3):

            try:

                response = self.client.chat.completions.create(

                    model=GROQ_MODEL,

                    messages=[

                        {

                            "role": "system",

                            "content": (

                                "You are a research paper analysis assistant. "

                                "Use only supplied evidence. Do not invent facts, "

                                "metrics, datasets, or limitations. Return valid "

                                "JSON only."

                            ),

                        },

                        {"role": "user", "content": prompt},

                    ],

                    temperature=0.1,

                    max_tokens=2500,

                )

                response_text = response.choices[0].message.content or ""

                parsed = json.loads(_clean_json_response(response_text))

                if isinstance(parsed, dict):

                    return parsed

                raise ValueError("Groq response was not a JSON object")

            except Exception as exc:

                print(f"Paper analysis attempt {attempt + 1} failed: {exc}")

                if attempt < 2:

                    time.sleep(2 * (attempt + 1))

        return None

    @staticmethod
    def _fallback_fields(record, retrieved):
        """Use relevant source excerpts when Groq synthesis fails."""
        for field in FIELD_CONFIG:
            usable = []
            for chunk in retrieved.get(field, []):
                text = re.sub(r"\s+", " ", chunk.get("text", "")).strip()
                if not text or _is_reference_material(text, chunk.get("heading", "")):
                    continue
                if _is_noisy_summary(text):
                    continue
                if len(re.findall(r"[A-Za-z]{3,}", text)) < 8:
                    continue
                sentences = re.split(r"(?<=[.!?])\s+", text)
                excerpt = " ".join(sentences[:2]).strip()
                if len(excerpt) < 45:
                    excerpt = text[:520].rsplit(" ", 1)[0]
                usable.append(excerpt[:520].rstrip())
            unique, seen = [], set()
            for excerpt in usable:
                key = re.sub(r"\W+", " ", excerpt.lower()).strip()
                if key and key not in seen:
                    seen.add(key)
                    unique.append(excerpt)
            record[field] = " ".join(unique[:2]) if unique else MISSING
        record["potential_gap_from_evidence"] = MISSING

