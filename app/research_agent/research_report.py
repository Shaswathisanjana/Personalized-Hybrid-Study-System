"""Pure mixed-source report view; content display/export never updates CACM."""
from app.research_agent.collection_models import FIELDS
from app.research_agent.full_text_analysis import document_claims


def report_sources(documents):
    sources = []
    for document in documents:
        record = document['record']
        if not record.get('selected', True):
            continue
        metadata = record['metadata']
        scope = record.get('source_scope', 'full_text_excerpts')
        sources.append(dict(id=document['document_id'], title=metadata.get('title') or '[Title unknown] ' + document['filename'],
                            authors=metadata.get('authors') or ([metadata['author']] if metadata.get('author') else []),
                            year=metadata.get('year'), doi=metadata.get('doi'), url=metadata.get('url'),
                            filename=document['filename'] if scope != 'abstract_only' else None,
                            scope=scope, claims=document_claims(document), warnings=list(record.get('warnings', [])),
                            completed=len(record['analysis']), total=len(record['chunks']), status=record['status'],
                            errors=list(record.get('analysis_errors', {}).values())))
    return sources


def location(source, claim):
    suffix = f"page {claim['page']}, " if claim['page'] is not None else 'abstract-only, '
    return (f"{source['id']}; {suffix}chunk {claim['chunk_id']}" +
            ('; ' + source['url'] if source['url'] else '') + ('; DOI ' + source['doi'] if source['doi'] else ''))


def evidence_groups(sources):
    return {field: [(source, claim) for source in sources for claim in source['claims'][field]]
            for field in FIELDS}


def workflow_report_sources(result):
    """Expose existing saved abstract analyses to Word export without re-analysis."""
    import re
    from app.research_agent.source_identity import source_fingerprint
    from app.research_agent.paper_summarizer import NOT_REPORTED
    mapping = dict(research_problem='research_problem', proposed_method='methodology', dataset='dataset',
                   evaluation_metrics='evaluation_metrics', key_findings='findings', limitations='limitations')
    sources = []
    for summary in result.summaries:
        paper = next((p for p in result.accepted_papers if p.title == summary.title and p.url == summary.source_url), None)
        if paper is None:
            continue
        identity = 'legacy:' + source_fingerprint(paper)
        claims = {field: [] for field in FIELDS}
        for original, target in mapping.items():
            quote = summary.evidence_quotes.get(original, '')
            value = getattr(summary, original)
            if not isinstance(quote, str) or not quote.strip() or not isinstance(value, str) or value == NOT_REPORTED:
                continue
            match = re.search(r'\s+'.join(re.escape(word) for word in quote.split()), paper.abstract, flags=re.IGNORECASE)
            if match:
                claims[target].append(dict(quote=match.group(0), observation=value, page=None,
                                            chunk_id='saved-abstract-summary', document_id=identity))
        sources.append(dict(id=identity, title=paper.title, authors=paper.authors, year=paper.year,
                            doi=getattr(paper, 'doi', ''), url=paper.url, filename=None, scope='abstract_only', claims=claims,
                            completed=1, total=1, status='saved abstract analysis',
                            warnings=['Existing saved abstract-only analysis; no full-text retrieval is implied.'] + result.warnings,
                            errors=list(getattr(result, 'stage_errors', {}).values())))
    return sources


def research_suggestions(topic, sources):
    from app.research_agent.paper_summarizer import PaperSummary
    from app.research_agent.research_gap_identifier import ResearchGapIdentifier
    from app.research_agent.research_objective_generator import ResearchObjectiveGenerator
    summaries = []
    for source in sources:
        for claim in source['claims']['limitations']:
            summaries.append(PaperSummary(source['title'], source['authors'], source['year'],
                             source['url'] or source['id'], limitations=claim['quote'] + ' [' + location(source, claim) + ']',
                             evidence_quotes={'limitations': claim['quote']}, source_scope=source['scope']))
    if not summaries:
        return None, None
    gaps = ResearchGapIdentifier().identify(topic.strip() or 'Selected research collection', summaries)
    return gaps, ResearchObjectiveGenerator().generate(gaps)
