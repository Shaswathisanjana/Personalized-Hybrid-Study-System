"""Local-delivery checks use disposable SQLite data and no providers."""
from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import run_phss
from tools.backup_student_data import backup_database


class LocalDeliveryTests(unittest.TestCase):
    def test_phss_backup_restores_evidence_conflicts_drafts_and_deduplication(self):
        # Synthetic assessed activity, real PHSS services; no provider clients.
        run_phss.prepare_imports()
        from types import SimpleNamespace
        from app.cognitive.cognitive_engine import CognitiveEngine
        from app.cognitive.evidence import LearningEvidence
        from app.cognitive.models import StudentCognitiveModel
        from app.learning_agent.progress_tracker import LearningProgressTracker
        from app.persistence.session_recovery import capture, restore
        from app.persistence.sqlite_store import SQLiteStudentStore

        def orchestrator(engine):
            return SimpleNamespace(cognitive_engine=engine)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.sqlite3'
            target = Path(directory) / 'restored.sqlite3'
            store = SQLiteStudentStore(source)
            first = store.create_profile('Backup fixture one')
            second = store.create_profile('Backup fixture two')
            student, engine = StudentCognitiveModel(first), CognitiveEngine()
            tracker = LearningProgressTracker()
            observations = [LearningEvidence(first, 'Recursion', agent, 'quiz', score, .6, .9)
                            for agent, score in [('learning', .95), ('coding', .1)]]
            for observation in observations:
                engine.process_evidence(student, observation)
            tracker.complete_practice_session(first, 'Recursion', 5, 'backup-fixture-quiz')
            state = dict(student=student, orchestrator=orchestrator(engine),
                         learning_progress_tracker=tracker,
                         advanced_coding_editor='# synthetic unfinished draft',
                         learning_goal='Recursion')
            payload = capture(state)
            store.save(first, payload, 0)
            backup_database(source, target)

            backup = SQLiteStudentStore(target)
            revision, saved = backup.load(first)
            restored = restore(saved, first, orchestrator)
            self.assertEqual(revision, 1)
            self.assertEqual(capture(restored), payload)
            restored_engine = restored['orchestrator'].cognitive_engine
            self.assertTrue(restored_engine.has_conflict(first, 'Recursion'))
            self.assertEqual(restored['student'].find_concept('Python Recursion').attempts, 2)
            self.assertEqual(restored['advanced_coding_editor'], '# synthetic unfinished draft')
            self.assertEqual(backup.load(second), (0, None))

            # Restored receipts/completion guards must reject duplicate scoring.
            restored_engine.process_evidence(restored['student'], observations[0])
            restored_tracker = restored['learning_progress_tracker']
            restored_tracker.complete_practice_session(first, 'Recursion', 5, 'backup-fixture-quiz')
            self.assertEqual(capture(restored), payload)
            self.assertEqual(restored_tracker.get_progress(first, 'Recursion').completed_practice_sessions, 1)
            self.assertEqual(store.load(first), (1, payload))

    def test_backup_includes_committed_wal_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'student.sqlite3'
            target = Path(directory) / 'backup.sqlite3'
            with closing(sqlite3.connect(source)) as writer:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('CREATE TABLE snapshots (value TEXT)')
                writer.execute('INSERT INTO snapshots VALUES (?)', ('fixture',))
                writer.commit()
                backup_database(source, target)
                self.assertEqual(writer.execute('SELECT * FROM snapshots').fetchall(), [('fixture',)])
            with closing(sqlite3.connect(target)) as restored:
                self.assertEqual(restored.execute('SELECT * FROM snapshots').fetchall(), [('fixture',)])

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'a.db', Path(directory) / 'b.db'
            source.touch()
            target.write_bytes(b'keep existing backup')
            with self.assertRaises(FileExistsError):
                backup_database(source, target)
            self.assertEqual(target.read_bytes(), b'keep existing backup')

    def test_same_source_and_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'a.db'
            source.touch()
            with self.assertRaises(ValueError):
                backup_database(source, source)

    def test_missing_source_creates_no_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'a.db', Path(directory) / 'b.db'
            with self.assertRaises(FileNotFoundError):
                backup_database(source, target)
            self.assertFalse(target.exists())

    def test_launcher_stays_local_and_disables_telemetry(self):
        with patch('sys.argv', ['run_phss.py', '--port', '8507']), \
                patch.object(run_phss, 'dependency_errors', return_value=[]), \
                patch.object(run_phss.runpy, 'run_module') as launch:
            self.assertEqual(run_phss.main(), 0)
            self.assertIn('--server.address=127.0.0.1', run_phss.sys.argv)
            self.assertIn('--server.port=8507', run_phss.sys.argv)
            self.assertIn('--browser.gatherUsageStats=false', run_phss.sys.argv)
            launch.assert_called_once_with('streamlit', run_name='__main__')


if __name__ == '__main__':
    unittest.main()
