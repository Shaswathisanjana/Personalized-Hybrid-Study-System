from copy import deepcopy
from backend.report_synthesis import enrich_sources,synthesis_paragraphs
from backend.tests.test_report_truthfulness import sources


def test_dataset_size_is_recovered_from_objective_without_mutating_saved_claims():
    original=sources();quote='HRIPCB, a synthesised PCB dataset that contains 1386 images with 6 kinds of defects is proposed.'
    claim=dict(quote=quote,page=3,chunk_id='p3-c1',document_id='1')
    original[0]['claims']['objectives']=[claim];before=deepcopy(original)
    enriched=enrich_sources(original)
    assert enriched[0]['claims']['dataset'][-1]==claim
    assert original==before


def test_metric_quote_recovered_from_findings_with_original_provenance():
    source=sources()[0]
    result=enrich_sources([source])[0]
    assert result['claims']['evaluation_metrics']==source['claims']['findings']
    assert result['claims']['models_algorithms']==[]
    assert result['claims']['limitations']==[]


def test_no_dataset_or_metric_fabricated_from_generic_mentions():
    source=sources()[1]
    source['claims']['findings']=[]
    result=enrich_sources([source])[0]
    assert not result['claims']['dataset'] and not result['claims']['evaluation_metrics']


def test_narrative_preserves_quotes_and_does_not_rank_methods():
    items=sources()
    paragraphs=synthesis_paragraphs(items,lambda s,c:'['+s['id']+']',[('findings','reported outcomes')])
    assert len(paragraphs)==1
    assert 'In another source' in paragraphs[0]
    assert all(c['quote'] in paragraphs[0] for s in items for c in s['claims']['findings'])
    assert '[1]' in paragraphs[0] and '[2]' in paragraphs[0]
    assert 'outperforms' not in paragraphs[0]


def test_repair_is_idempotent_for_claims():
    first=enrich_sources(sources());second=enrich_sources(first)
    assert [s['claims'] for s in first]==[s['claims'] for s in second]
