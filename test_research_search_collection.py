"""Offline parsing, incremental search and persistent mixed collection acceptance."""
from copy import deepcopy
from dataclasses import asdict, replace
from io import BytesIO
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import URLError

from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.research_library_store import UnifiedResearchDocumentStore
from app.persistence.research_document_store import StaleDocumentError
from app.research_agent.collection_service import ResearchCollectionService
from app.research_agent.models import ResearchPaper
from app.research_agent.providers.openalex import OpenAlexSearch, OpenAlexSearchError
from app.research_agent.search_session import ResearchSearchSession, SearchLimits
from app.research_agent.research_report import report_sources
from pdf_collection_test_fixtures import make_pdf, ExtractiveAnalyzer
from test_research_analysis_recovery import ABSTRACT


def synthetic_paper(identifier, abstract=None):
    text = (ABSTRACT + ' The methodology uses a controlled comparison. '
            'The dataset contains synthetic records. The study is limited to synthetic examples.')
    return ResearchPaper('Synthetic search fixture ' + str(identifier), ['Synthetic Author'],
                         text if abstract is None else abstract, 'https://example.org/offline-fixture/' + str(identifier),
                         2025, 'offline_fixture', str(identifier))


class PagedFixture:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def search_page(self, query, limit=20, cursor='*'):
        self.calls.append((query, limit, cursor))
        index = 0 if cursor == '*' else int(cursor)
        value = self.pages[index]
        if isinstance(value, Exception):
            raise value
        return dict(papers=deepcopy(value), next_cursor=str(index + 1) if index + 1 < len(self.pages) else None,
                    total_count=None, warnings=[])


class AcademicSearchCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'students.sqlite3'
        self.store = SQLiteStudentStore(self.path)
        self.owner = self.store.create_profile('Synthetic owner')
        self.other = self.store.create_profile('Synthetic other')

    def test_parse_actual_provider_metadata_projection(self):
        work = json.loads(Path('tests/fixtures/openalex_work_projection.json').read_text(encoding='utf-8'))
        payload = dict(results=[work], meta={'next_cursor': 'fixture-next', 'count': 1})
        with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(payload).encode())) as request:
            page = OpenAlexSearch().search_page('open access articles', limit=7)
        paper = page['papers'][0]
        self.assertEqual((paper.paper_id, paper.year, paper.doi), ('W2741809807', 2018, 'https://doi.org/10.7717/peerj.4375'))
        self.assertEqual(paper.authors, [])
        self.assertEqual(paper.abstract, '')
        self.assertIn('cursor=%2A', request.call_args.args[0].full_url)
        self.assertIn('per_page=7', request.call_args.args[0].full_url)

    def test_parse_synthetic_complete_response_abstract_authors_and_missing_records(self):
        text = synthetic_paper(1).abstract
        inverted = {}
        for position, word in enumerate(text.split()):
            inverted.setdefault(word, []).append(position)
        payload = dict(results=[None, {}, dict(id='https://openalex.org/FIXTURE', display_name='Synthetic fixture',
                       authorships=[{'author': {'display_name': 'Synthetic Author'}}], publication_year=2025,
                       doi='fixture-doi-not-a-publication', primary_location={'landing_page_url': 'https://example.org/fixture'},
                       abstract_inverted_index=inverted)], meta={'next_cursor': None})
        with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(payload).encode())):
            page = OpenAlexSearch().search_page('arbitrary graph education topic')
        self.assertEqual(len(page['papers']), 1)
        self.assertEqual(page['papers'][0].abstract, ' '.join(text.split()))
        self.assertEqual(page['papers'][0].authors, ['Synthetic Author'])
        self.assertTrue(page['warnings'])

    def test_provider_failures_and_invalid_json_are_transparent(self):
        with patch('urllib.request.urlopen', side_effect=URLError('offline failure')):
            with self.assertRaises(OpenAlexSearchError):
                OpenAlexSearch().search_page('any topic')
        with patch('urllib.request.urlopen', return_value=BytesIO(b'not json')):
            with self.assertRaises(OpenAlexSearchError):
                OpenAlexSearch().search_page('any topic')

    def test_arbitrary_topic_incremental_duplicates_and_selection_survive_reopen(self):
        provider = PagedFixture([[synthetic_paper(i) for i in (1, 2, 3)],
                                 [synthetic_paper(i) for i in (3, 4, 5)],
                                 [synthetic_paper(i) for i in (6, 7)]])
        session = ResearchSearchSession(self.store, self.owner, provider, replace(SearchLimits(), page_size=3))
        session.start('Agentic AI for personalized quantum programming education', 7)
        for _ in range(3):
            session.fetch_next()
        record, _ = session.load()
        self.assertEqual(len(record['results']), 7)
        session.select(record['results'][0]['id'], True)
        reopened = ResearchSearchSession(SQLiteStudentStore(self.path), self.owner, provider)
        self.assertTrue(reopened.load()[0]['results'][0]['selected'])
        self.assertEqual(len(provider.calls), 3)
        self.assertIsNone(ResearchSearchSession(self.store, self.other).load()[0])

    def test_failed_page_keeps_prior_results_cursor_and_selection_for_retry(self):
        provider = PagedFixture([[synthetic_paper(1)], RuntimeError('Injected outage')])
        session = ResearchSearchSession(self.store, self.owner, provider)
        session.start('custom topic', 10)
        first = session.fetch_next()
        session.select(first['results'][0]['id'], True)
        failed = session.fetch_next()
        self.assertTrue(failed['error'])
        self.assertEqual((failed['pages'], len(failed['results']), failed['cursor']), (1, 1, '1'))
        self.assertTrue(failed['results'][0]['selected'])
        provider.pages[1] = [synthetic_paper(2)]
        recovered = session.fetch_next()
        self.assertFalse(recovered['error'])
        self.assertEqual(len(recovered['results']), 2)

    def test_abstract_collection_deduplication_upgrade_selection_and_isolation(self):
        library = UnifiedResearchDocumentStore(self.store)
        first = synthetic_paper(1, '')
        identity, _ = library.add_paper(self.owner, first)
        self.assertEqual(library.get(self.owner, identity)['record']['status'], 'excluded')
        same, status = library.add_paper(self.owner, synthetic_paper(1))
        self.assertEqual((same, status), (identity, 'upgraded'))
        self.assertEqual(library.add_paper(self.owner, synthetic_paper(1))[1], 'duplicate')
        service = ResearchCollectionService(self.store, self.owner, document_store=library)
        service.select(identity, False)
        self.assertFalse(UnifiedResearchDocumentStore(SQLiteStudentStore(self.path)).get(self.owner, identity)['record']['selected'])
        self.assertEqual(library.list(self.other), [])
        with self.assertRaises(ValueError):
            library.get(self.other, identity)

    def test_mixed_pdf_and_abstract_analysis_preserves_original_snapshot(self):
        from test_student_persistence import student_state
        from app.persistence.session_recovery import capture
        state = student_state(self.owner)
        payload = capture(state)
        self.store.save(self.owner, payload, 0)
        pdf_service = ResearchCollectionService(self.store, self.owner)
        pdf_service.add('synthetic.pdf', make_pdf())
        pdf_service.extract_batch()
        library = UnifiedResearchDocumentStore(self.store)
        library.add_paper(self.owner, synthetic_paper(1))
        analyzer = ExtractiveAnalyzer()
        service = ResearchCollectionService(self.store, self.owner, document_store=library, analyzer=analyzer)
        service.analyze_batch()
        sources = report_sources(service.list())
        self.assertEqual({s['scope'] for s in sources}, {'abstract_only', 'full_text_excerpts'})
        for source in sources:
            for claim in source['claims']['methodology']:
                self.assertEqual(claim['page'], None if source['scope'] == 'abstract_only' else 2)
        self.assertEqual(self.store.load(self.owner), (1, payload))
        calls = len(analyzer.calls)
        self.assertEqual(service.analyze_batch(), 0)
        self.assertEqual(len(analyzer.calls), calls)

    def test_search_and_collection_limits_are_enforced(self):
        session = ResearchSearchSession(self.store, self.owner)
        with self.assertRaises(ValueError):
            session.start('topic', 1001)
        with self.assertRaises(ValueError):
            SearchLimits(page_size=101)
        library = UnifiedResearchDocumentStore(self.store, replace(SearchLimits(), max_sources=1))
        library.add_paper(self.owner, synthetic_paper(1))
        with self.assertRaises(ValueError):
            library.add_paper(self.owner, synthetic_paper(2))

    def test_legacy_paper_defaults_preserve_old_cache_fingerprints(self):
        from app.persistence.state_codec import encode, decode
        from app.research_agent.source_identity import source_fingerprint
        paper = synthetic_paper(1)
        serialized = encode(paper)
        serialized['fields'].pop('doi')
        restored = decode(serialized)
        old = asdict(paper)
        old.pop('doi')
        self.assertEqual(restored.doi, '')
        self.assertEqual(source_fingerprint(restored), hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest())

    def test_removed_academic_source_rejects_late_results(self):
        library = UnifiedResearchDocumentStore(self.store)
        identity, _ = library.add_paper(self.owner, synthetic_paper(1))
        document = library.get(self.owner, identity)
        library.remove(self.owner, identity, document['revision'])
        with self.assertRaises(StaleDocumentError):
            library.update(self.owner, identity, document['record'], document['revision'])

    def test_doi_duplicates_across_provider_ids_do_not_create_two_collection_entries(self):
        library = UnifiedResearchDocumentStore(self.store)
        first, second = synthetic_paper('one'), synthetic_paper('two')
        first.doi = 'https://doi.org/fixture-not-a-registered-publication'
        second.doi = 'doi:FIXTURE-NOT-A-REGISTERED-PUBLICATION'
        identity, _ = library.add_paper(self.owner, first)
        self.assertEqual(library.add_paper(self.owner, second), (identity, 'duplicate'))
        self.assertEqual(len(library.list(self.owner)), 1)

    def test_partial_abstract_failure_retries_only_unfinished_source(self):
        library = UnifiedResearchDocumentStore(self.store)
        library.add_paper(self.owner, synthetic_paper(1))
        second = synthetic_paper(2)
        second.abstract += ' second_failure_marker'
        library.add_paper(self.owner, second)
        analyzer = ExtractiveAnalyzer()
        analyzer.fail_chunk = 'second_failure_marker'
        service = ResearchCollectionService(self.store, self.owner, document_store=library, analyzer=analyzer)
        service.analyze_batch()
        self.assertEqual([len(d['record']['analysis']) for d in service.list()], [1, 0])
        analyzer.fail_chunk = None
        reopened = ResearchCollectionService(SQLiteStudentStore(self.path), self.owner,
                     document_store=UnifiedResearchDocumentStore(SQLiteStudentStore(self.path)), analyzer=analyzer)
        reopened.analyze_batch()
        self.assertEqual(len(analyzer.calls), 3)
        self.assertTrue(all(len(d['record']['analysis']) == 1 for d in reopened.list()))

    def test_optional_provider_key_uses_header_and_never_enters_source_urls(self):
        payload = dict(results=[], meta={'next_cursor': None})
        provider = OpenAlexSearch(api_key='offline-placeholder-not-a-real-key')
        for operation in (lambda: provider.search_page('topic'), lambda: provider.search('topic')):
            with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(payload).encode())) as request:
                operation()
            sent = request.call_args.args[0]
            self.assertEqual(sent.get_header('Authorization'), 'Bearer offline-placeholder-not-a-real-key')
            self.assertNotIn('offline-placeholder', sent.full_url)


if __name__ == '__main__':
    unittest.main()
