"""Deterministic Milestone 1 checks; run as a standalone script or with unittest."""
import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.progress_tracker import LearningProgressTracker
from app.persistence.session_recovery import capture, restore
from app.persistence.sqlite_store import SQLiteStudentStore, StaleSnapshotError
from app.persistence.streamlit_state import load_profile, save_state


def offline_orchestrator(engine):
    return SimpleNamespace(cognitive_engine=engine)


def student_state(student_id):
    return dict(student=StudentCognitiveModel(student_id),
                orchestrator=offline_orchestrator(CognitiveEngine()),
                learning_progress_tracker=LearningProgressTracker())


class StudentPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_persistence_test_")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "students.sqlite3"
        self.store = SQLiteStudentStore(self.path)
        self.alice = self.store.create_profile("Alice")
        self.bob = self.store.create_profile("Bob")

    def populated(self):
        state = student_state(self.alice)
        for source, performance in (("learning", .95), ("coding", .15)):
            state["orchestrator"].cognitive_engine.process_evidence(
                state["student"], LearningEvidence(self.alice, "Recursion", source,
                    "quiz", performance, .6, .9, ["Missing base case"]))
        tracker = state["learning_progress_tracker"]
        tracker.complete_practice_session(self.alice, "Recursion", 5, "quiz-1")
        return state

    def test_full_roundtrip_and_reopen_without_replaying_evidence(self):
        state = self.populated()
        payload = capture(state)
        self.store.save(self.alice, payload, 0)
        revision, loaded = SQLiteStudentStore(self.path).load(self.alice)
        restored = restore(loaded, self.alice, offline_orchestrator)
        self.assertEqual(revision, 1)
        self.assertEqual(capture(restored), payload)
        self.assertEqual(restored["student"].get_concept("Recursion").attempts, 2)
        self.assertTrue(restored["orchestrator"].cognitive_engine.has_conflict(self.alice, "Recursion"))
        tracker = restored["learning_progress_tracker"]
        tracker.complete_practice_session(self.alice, "Recursion", 5, "quiz-1")
        self.assertEqual(tracker.get_progress(self.alice, "Recursion").completed_practice_sessions, 1)

    def test_students_and_profile_switch_are_isolated(self):
        self.store.save(self.alice, capture(self.populated()), 0)
        self.store.save(self.bob, capture(student_state(self.bob)), 0)
        state = {}
        load_profile(state, self.store, self.alice, offline_orchestrator)
        state["advanced_coding_editor"] = "Alice draft"
        save_state(state)
        load_profile(state, self.store, self.bob, offline_orchestrator)
        self.assertNotIn("advanced_coding_editor", state)
        self.assertEqual(state["student"].concepts, {})
        load_profile(state, self.store, self.alice, offline_orchestrator)
        self.assertEqual(state["advanced_coding_editor"], "Alice draft")
        self.assertEqual(state["student"].get_concept("Recursion").attempts, 2)

    def test_stale_write_and_invalid_payload_preserve_saved_record(self):
        payload = capture(self.populated())
        self.store.save(self.alice, payload, 0)
        with self.assertRaises(StaleSnapshotError):
            self.store.save(self.alice, payload, 0)
        malformed = copy.deepcopy(payload)
        malformed["data"] = {"kind": "data", "type": "os.system", "fields": {}}
        with self.assertRaises(ValueError):
            self.store.save(self.alice, malformed, 1)
        with self.assertRaises(ValueError):
            self.store.save(self.bob, payload, 0)
        self.assertEqual(self.store.load(self.alice), (1, payload))

    def test_foreign_evidence_rejected(self):
        state = self.populated()
        state["orchestrator"].cognitive_engine.evidence_store.evidence_history[0].user_id = self.bob
        with self.assertRaises(ValueError):
            capture(state)

    def test_corrupt_load_leaves_current_session_intact(self):
        self.store.save(self.alice, capture(self.populated()), 0)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE snapshots SET payload = ? WHERE student_id = ?", ('{}', self.alice))
        state = student_state(self.bob)
        before = state["student"]
        with self.assertRaises(ValueError):
            load_profile(state, self.store, self.alice, offline_orchestrator)
        self.assertIs(state["student"], before)

    def test_unsupported_database_version_is_not_rewritten(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA user_version = 999")
        with self.assertRaises(ValueError):
            SQLiteStudentStore(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 999)

    def test_separate_python_process_restores_saved_state(self):
        self.store.save(self.alice, capture(self.populated()), 0)
        code = """
import sys
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.session_recovery import restore
revision, payload = SQLiteStudentStore(sys.argv[2]).load(sys.argv[3])
state = restore(payload, sys.argv[3], lambda e: SimpleNamespace(cognitive_engine=e))
assert revision == 1
assert state['student'].get_concept('Recursion').attempts == 2
assert len(state['orchestrator'].cognitive_engine.evidence_store.get_all_evidence()) == 2
assert state['orchestrator'].cognitive_engine.has_conflict(sys.argv[3], 'Recursion')
print('RESTORED')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code,
            str(Path('.venv/Lib/site-packages').resolve()), str(self.path), self.alice],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESTORED", result.stdout)


if __name__ == "__main__":
    unittest.main()
