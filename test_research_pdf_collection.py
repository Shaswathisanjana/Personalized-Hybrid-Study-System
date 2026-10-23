"""Deterministic real-PDF extraction, ownership, migration and recovery checks."""
from dataclasses import replace
import hashlib
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch

from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.research_document_store import StaleDocumentError
from app.research_agent.collection_models import CollectionLimits, MISSING
from app.research_agent.collection_service import ResearchCollectionService
from app.research_agent.full_text_analysis import compare_collection, document_claims
from pdf_collection_test_fixtures import make_pdf, ExtractiveAnalyzer


class PDFCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'students.sqlite3'
        self.store = SQLiteStudentStore(self.path)
        self.owner = self.store.create_profile('Synthetic student')
        self.other = self.store.create_profile('Other synthetic student')
        self.analyzer = ExtractiveAnalyzer()
        self.service = ResearchCollectionService(self.store, self.owner, analyzer=self.analyzer)

    def extract_all(self):
        while self.service.extract_batch():
            pass

    def test_seven_pdfs_actual_text_page_citations_comparison_and_reopen(self):
        for index in range(7):
            self.service.add(f'unrelated-filename-{index}.pdf', make_pdf(index))
        self.assertEqual(self.service.extract_batch(), 3)
        self.assertEqual(sum(d['record']['status'] == 'ready' for d in self.service.list()), 3)
        self.extract_all()
        while self.service.analyze_batch():
            pass
        docs = self.service.list()
        self.assertEqual(len(docs), 7)
        self.assertTrue(all(d['record']['status'] == 'ready' for d in docs))
        self.assertEqual(len(self.analyzer.calls), 14)
        self.assertTrue(any('controlled comparison' in text for text in self.analyzer.calls))
        for document in docs:
            claim = document_claims(document)['methodology'][0]
            self.assertEqual((claim['page'], claim['chunk_id']), (2, 'p2-c1'))
            self.assertEqual(claim['document_id'], document['document_id'])
        report = compare_collection('Synthetic topic', docs)
        self.assertEqual(len(report['comparison'].papers), 7)
        self.assertEqual(report['comparison'].source_scope, 'full_text_excerpts')
        self.assertEqual(report['comparison'].papers[0].fields['research_problem'].value, MISSING)
        self.assertEqual(len(report['gaps'].candidates), 7)
        reopened = ResearchCollectionService(SQLiteStudentStore(self.path), self.owner, analyzer=self.analyzer)
        self.assertEqual(reopened.list(), docs)
        self.assertEqual(reopened.analyze_batch(), 0)

    def test_duplicate_hashes_and_profile_isolation(self):
        content = make_pdf()
        identity, status = self.service.add('a.pdf', content)
        self.assertEqual((identity, status), (hashlib.sha256(content).hexdigest(), 'added'))
        self.assertEqual(self.service.add('renamed.pdf', content), (identity, 'duplicate'))
        other = ResearchCollectionService(self.store, self.other)
        self.assertEqual(other.list(), [])
        with self.assertRaises(ValueError):
            other.documents.get(self.other, identity, include_pdf=True)
        other.add('own-copy.pdf', content)
        self.service.remove(identity)
        self.assertEqual(self.service.list(), [])
        self.assertEqual(len(other.list()), 1)
        self.assertEqual(self.service.add('again.pdf', content)[1], 'reactivated')

    def test_invalid_corrupt_encrypted_scanned_and_unknown_metadata(self):
        with self.assertRaises(ValueError):
            self.service.add('fake.pdf', b'not a PDF')
        for name, content in [('corrupt.pdf', b'%PDF-1.7\nbroken'),
                              ('encrypted.pdf', make_pdf(encrypted=True)),
                              ('scan.pdf', make_pdf(pages=[''])),
                              ('unknown.pdf', make_pdf(metadata=False))]:
            self.service.add(name, content)
        self.extract_all()
        records = {d['filename']: d['record'] for d in self.service.list()}
        for name in ('corrupt.pdf', 'encrypted.pdf', 'scan.pdf'):
            self.assertEqual(records[name]['status'], 'rejected')
        self.assertIn('OCR is unavailable', records['scan.pdf']['warnings'][0])
        self.assertIsNone(records['unknown.pdf']['metadata']['title'])
        self.assertIsNone(records['unknown.pdf']['metadata']['year'])

    def test_limits_count_bytes_pages_and_text_are_enforced(self):
        content = make_pdf()
        limited = ResearchCollectionService(self.store, self.owner,
                    limits=replace(CollectionLimits(), max_file_bytes=len(content) - 1))
        with self.assertRaises(ValueError):
            limited.add('too-large.pdf', content)
        limited = ResearchCollectionService(self.store, self.owner,
                    limits=replace(CollectionLimits(), max_documents=1, max_pages=1))
        identity, _ = limited.add('page-limit.pdf', content)
        with self.assertRaises(ValueError):
            limited.add('second.pdf', make_pdf(1))
        limited.extract_batch()
        self.assertEqual(limited.list()[0]['record']['status'], 'rejected')
        limited.remove(identity)
        with self.assertRaises(ValueError):
            limited.add('quota-bypass.pdf', make_pdf(1))
        text_limits = replace(CollectionLimits(), max_text_chars=100, chunk_chars=50)
        text_service = ResearchCollectionService(self.store, self.other, limits=text_limits)
        text_service.add('text-limit.pdf', content)
        text_service.extract_batch()
        self.assertEqual(text_service.list()[0]['record']['status'], 'rejected')
        with self.assertRaises(ValueError):
            ResearchCollectionService(self.store, self.other,
                limits=replace(CollectionLimits(), max_collection_bytes=1)).add('bytes.pdf', make_pdf(3))

    def test_provider_failure_preserves_success_and_retries_only_missing_chunks(self):
        self.service.add('partial.pdf', make_pdf())
        self.extract_all()
        self.analyzer.fail_chunk = 'methodology'
        self.service.analyze_batch()
        first = self.service.list()[0]
        self.assertEqual(len(first['record']['analysis']), 1)
        self.assertEqual(len(first['record']['analysis_errors']), 1)
        self.analyzer.fail_chunk = None
        reopened = ResearchCollectionService(self.store, self.owner, analyzer=self.analyzer)
        reopened.analyze_batch()
        self.assertEqual(len(self.analyzer.calls), 3)
        self.assertEqual(len(reopened.list()[0]['record']['analysis']), 2)
        self.assertEqual(reopened.list()[0]['record']['analysis_errors'], {})

    def test_invented_quotes_rejected_and_deselected_sources_not_analyzed(self):
        identity, _ = self.service.add('grounding.pdf', make_pdf())
        self.extract_all()
        self.service.select(identity, False)
        self.assertEqual(self.service.analyze_batch(), 0)
        self.service.select(identity, True)
        with patch.object(self.analyzer, 'analyze', return_value={'findings': 'Invented absent finding.'}):
            self.service.analyze_batch()
        self.assertFalse(self.service.list()[0]['record']['analysis'])
        self.assertEqual(len(self.service.list()[0]['record']['analysis_errors']), 2)

    def test_removed_or_stale_document_cannot_receive_late_results(self):
        identity, _ = self.service.add('stale.pdf', make_pdf())
        old = self.service.documents.get(self.owner, identity)
        self.service.select(identity, False)
        with self.assertRaises(StaleDocumentError):
            self.service.documents.update(self.owner, identity, old['record'], old['revision'])
        current = self.service.documents.get(self.owner, identity)
        self.service.remove(identity)
        with self.assertRaises(StaleDocumentError):
            self.service.documents.update(self.owner, identity, current['record'], current['revision'])

    def test_schema_three_upgrade_retains_snapshots_and_document_backup(self):
        from test_student_persistence import student_state
        from app.persistence.session_recovery import capture
        from tools.backup_student_data import backup_database
        payload = capture(student_state(self.owner))
        self.store.save(self.owner, payload, 0)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TABLE research_documents')
            db.execute('PRAGMA user_version=3')
        upgraded = SQLiteStudentStore(self.path)
        self.assertEqual(upgraded.load(self.owner), (1, payload))
        ResearchCollectionService(upgraded, self.owner).add('backup.pdf', make_pdf())
        destination = Path(self.temporary.name) / 'backup.sqlite3'
        backup_database(self.path, destination)
        backed_up = SQLiteStudentStore(destination)
        self.assertEqual(backed_up.load(self.owner), (1, payload))
        self.assertEqual(len(ResearchCollectionService(backed_up, self.owner).list()), 1)

    def test_extraction_failure_is_saved_and_explicitly_recoverable(self):
        self.service.add('retry.pdf', make_pdf())
        with patch.object(self.service, 'extractor', side_effect=RuntimeError('fixture')):
            self.service.extract_batch()
        self.assertEqual(self.service.list()[0]['record']['status'], 'extraction_error')
        self.service.extract_batch()
        self.assertEqual(self.service.list()[0]['record']['status'], 'ready')


if __name__ == '__main__':
    unittest.main()
