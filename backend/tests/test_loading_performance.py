from threading import Barrier
from types import SimpleNamespace
import pytest
from app.learning_agent.resources.multi_source_retriever import MultiSourceResourceRetriever
from backend.tests.test_api import client


class Source:
    def __init__(self,label,gate=None,fail=False):self.label,self.gate,self.fail=label,gate,fail
    def search(self,**kwargs):
        if self.gate:self.gate.wait(timeout=3)
        if self.fail:raise RuntimeError('offline fixture failure')
        return [SimpleNamespace(url='https://example.org/'+self.label+str(i)) for i in range(2)]


def test_independent_sources_overlap_and_preserve_round_robin_order():
    gate=Barrier(3)
    result=MultiSourceResourceRetriever([Source('a',gate),Source('b',gate),Source('c',gate)]).search('Recursion',max_results=6)
    assert [x.url for x in result]==['https://example.org/'+name+str(i) for i in range(2) for name in ('a','b','c')]


def test_partial_failure_preserves_other_sources_and_deduplicates():
    result=MultiSourceResourceRetriever([Source('a'),Source('a'),Source('b',fail=True)]).search('Recursion',max_results=6)
    assert [x.url for x in result]==['https://example.org/a0','https://example.org/a1']


def test_all_source_failures_still_report_failure():
    with pytest.raises(RuntimeError,match='All resource retrieval attempts failed'):
        MultiSourceResourceRetriever([Source('a',fail=True),Source('b',fail=True)]).search('Recursion')


def test_server_timing_reports_actual_nonnegative_duration(client):
    response=client.get('/api/health')
    assert response.status_code==200
    assert response.headers['server-timing'].startswith('app;dur=')
    assert float(response.headers['server-timing'].split('=')[1])>=0
