"""Deterministic provider reliability and concise partial-report regressions."""
from types import SimpleNamespace
from unittest.mock import Mock,patch
import json
import pytest
from app.research_agent.full_text_analysis import GroundedChunkAnalyzer
from app.research_agent.paper_summarizer import StructuredPaperSummarizer
from backend.research_reports import report_blocks,failure_summary
from app.research_agent.collection_models import FIELDS


def analyzer(responses):
    generate=Mock(side_effect=responses)
    provider=SimpleNamespace(client=SimpleNamespace(models=SimpleNamespace(generate_content=generate)),model_name='fixture',_clean_json=StructuredPaperSummarizer._clean_json)
    return GroundedChunkAnalyzer(provider=provider,timeout_seconds=17),generate


def response(fields):return SimpleNamespace(text=json.dumps(fields))


def test_transient_failure_recovers_with_bounded_requests():
    error=RuntimeError('fixture unavailable');error.code=503
    a,g=analyzer([error,response({'dataset':'The dataset contains synthetic records.'})])
    with patch('app.research_agent.full_text_analysis.time.sleep'):
        assert a.analyze({'text':'The dataset contains synthetic records.','page':1,'chunk_id':'p1'})
    assert g.call_count==2
    assert all(0<c.kwargs['config']['http_options']['timeout']<=17000 for c in g.call_args_list)


def test_invalid_quote_retries_and_never_accepts_fabrication():
    a,g=analyzer([response({'findings':'Invented result not present in source.'})]*2)
    with patch('app.research_agent.full_text_analysis.time.sleep'),pytest.raises(ValueError):
        a.analyze({'text':'The dataset contains synthetic records.','page':1,'chunk_id':'p1'})
    assert g.call_count==2 and 'shorter exact quotations' in g.call_args.kwargs['contents']


def test_whitespace_recovery_preserves_exact_original_span():
    original='The dataset contains\n synthetic records.'
    a,g=analyzer([response({'dataset':'The dataset contains synthetic records.'})])
    assert a.analyze({'text':original,'page':1,'chunk_id':'p1'})=={'dataset':original}
    assert g.call_count==1


def test_authentication_error_is_not_retried():
    error=RuntimeError('authentication failure');error.code=401
    a,g=analyzer([error])
    with pytest.raises(RuntimeError):a.analyze({'text':'source','page':1,'chunk_id':'p1'})
    assert g.call_count==1


def test_exhausted_time_budget_never_retries():
    error=RuntimeError('fixture unavailable');error.code=503
    a,g=analyzer([error])
    with patch('app.research_agent.full_text_analysis.time.monotonic',side_effect=[0,0,18]),pytest.raises(RuntimeError):
        a.analyze({'text':'source','page':1,'chunk_id':'p1'})
    assert g.call_count==1


def test_partial_report_does_not_repeat_unanalyzed_papers_in_each_section():
    base=dict(authors=[],year=None,doi=None,url=None,filename=None,scope='abstract_only',claims={k:[] for k in FIELDS},warnings=[],errors=[],total=1,status='ready')
    ready=dict(base,id='a',title='Analyzed paper',completed=1)
    pending=dict(base,id='b',title='Pending paper',completed=0,errors=['ServerError: 503 UNAVAILABLE sensitive diagnostic payload'])
    blocks=report_blocks('Report','topic',[ready,pending],['title','overviews','objectives','methods','evaluation','comparison','limitations'],partial=True)
    headings=[value[0] for kind,value in blocks if kind=='heading']
    assert headings.count('[2] Pending paper')==2 # limitations and references only
    comparison=[value for kind,value in blocks if kind=='table'][1]
    assert len(comparison[1])==1
    text=str(blocks)
    assert 'temporarily unavailable' in text and 'sensitive diagnostic payload' not in text
    assert 'could not be verified' in failure_summary(['ValueError: quotation is absent'])


def test_one_invalid_field_does_not_destroy_verified_evidence_after_retry():
    fields={'dataset':'The dataset contains synthetic records.','findings':'Fabricated improvement is not in the source.'}
    a,g=analyzer([response(fields),response(fields)])
    with patch('app.research_agent.full_text_analysis.time.sleep'):
        result=a.analyze({'text':fields['dataset'],'page':1,'chunk_id':'p1'})
    assert result=={'dataset':fields['dataset']}
    assert 'findings' in a.last_warnings[0] and g.call_count==2
