"""Conservative report evidence repair and extractive narrative synthesis.

Works on saved exact quotations, not titles or outside knowledge. It never writes
student records and never introduces paper-specific free-form factual prose.
"""
from copy import deepcopy
import re

FUTURE=re.compile(r'future (?:work|research|directions?)|these directions|could be explored',re.I)
DATA=re.compile(r'\bdata\s*sets?\b',re.I)
SPECIFIC=re.compile(r'\b\d[\d,]*\s+(?:images|samples|records|instances|subjects|cases|classes|kinds|categories)\b',re.I)
METRIC=re.compile(r'\bmAP\b|\bF1(?:[- ]score)?\b|\bIoU\b|\bFPS\b|\bprecision\b|\brecall\b|\baccuracy\b|frames per second',re.I)
LIMIT=re.compile(r'\blimited to\b|\blimitation(?:s)? (?:is|are|include)|\bnot evaluated\b|\bfails? to\b|\black of\b',re.I)


def enrich_sources(sources):
    """Reuse an evidenced span in another field only with explicit lexical cues.

    Classification is a report aid, not semantic or scientific verification.
    All additions preserve the exact quote and original page/chunk attribution.
    """
    result=deepcopy(sources)
    for source in result:
        claims=source['claims']
        pool=[c for items in claims.values() for c in items]
        def add(field,c):
            if not any((x['quote'],x['chunk_id'])==(c['quote'],c['chunk_id']) for x in claims[field]):
                claims[field].append(deepcopy(c))
        for claim in pool:
            quote=claim['quote']
            if DATA.search(quote) and SPECIFIC.search(quote):add('dataset',claim)
            if METRIC.search(quote) and re.search(r'\d',quote):add('evaluation_metrics',claim)
        claims['evaluation_metrics']=[c for c in claims['evaluation_metrics'] if METRIC.search(c['quote'])]
        claims['dataset']=[c for c in claims['dataset'] if not (re.search(r'widely used|various datasets|assessment indices',c['quote'],re.I) and not SPECIFIC.search(c['quote']))]
        future=[c for c in claims['models_algorithms'] if FUTURE.search(c['quote'])]
        if future:
            claims['models_algorithms']=[c for c in claims['models_algorithms'] if not FUTURE.search(c['quote'])]
            source['warnings'].append('Future-work model mentions are excluded from the implemented/reviewed model field; their source role must be checked in context.')
        # Generic statements that future work exists do not establish a limitation.
        claims['limitations']=[c for c in claims['limitations'] if not (FUTURE.search(c['quote']) and not LIMIT.search(c['quote']))]
    return result


def synthesis_paragraphs(sources,cite,fields):
    """Build connected, attributed prose without inventing semantic agreement.

    Exact evidence remains inside quotes. Connectors describe only the act of
    reporting, not equivalence, causality or scientific superiority.
    """
    paragraphs=[]
    for field,label in fields:
        items=[]
        for source in sources:
            seen=set()
            for claim in source['claims'][field]:
                if claim['quote'] in seen:continue
                seen.add(claim['quote'])
                items.append((source,claim))
        if not items:continue
        clauses=[]
        for index,(source,claim) in enumerate(items):
            lead='For '+label+', ' if index==0 else 'In another source, '
            clauses.append(lead+'the authors of "'+source['title']+'" report: "'+claim['quote']+'" '+cite(source,claim)+'.')
        for start in range(0,len(clauses),3):paragraphs.append(' '.join(clauses[start:start+3]))
    return paragraphs
