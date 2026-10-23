"""Synthetic legacy snapshots verify conservative, lossless record preservation."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import socket
import tempfile
import unittest
from unittest.mock import patch

from app.cognitive.models import StudentCognitiveModel, ConceptState
from app.cognitive.evidence import LearningEvidence
from app.cognitive.conflict_detector import CognitiveConflict
from app.learning_agent.progress_tracker import TopicLearningProgress
from app.persistence.session_recovery import capture, restore, unpack
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.state_codec import encode
from app.persistence.streamlit_state import load_profile, save_state
from test_student_persistence import offline_orchestrator


def legacy_payload(owner="alice", overlap=False, missing_ids=False):
    old = datetime(2025, 1, 1)
    new = old + timedelta(days=1)
    student = StudentCognitiveModel(owner, concepts={
        "Recursion": ConceptState("Recursion", mastery=.2, confidence=.3, attempts=2, last_updated=old),
        "Python Recursion": ConceptState("Python Recursion", mastery=.8, confidence=.6, attempts=3, last_updated=new),
        "RECURSION": ConceptState("RECURSION", last_updated=new + timedelta(days=1)),
        "SQL Recursion": ConceptState("SQL Recursion", mastery=.4, attempts=1, last_updated=old),
    })
    evidence = [LearningEvidence(owner, "Recursion", "coding", "quiz", .2, .6, .8, timestamp=old),
                LearningEvidence(owner, "Python Recursion", "learning", "quiz", .8, .6, .8, timestamp=new)]
    conflicts = {(owner, "Recursion"): [CognitiveConflict("Recursion", "coding", "learning", .2, .8, .6, "high")]}
    progress = {
        (owner, "recursion"): TopicLearningProgress("Recursion", old, old, 1, 5),
        (owner, "python recursion"): TopicLearningProgress("Python Recursion", new, new, 1, 10),
    }
    completions = set() if missing_ids else {
        (owner, "recursion", "first"),
        (owner, "python recursion", "first" if overlap else "second"),
    }
    data = dict(student=student, evidence=evidence, conflicts=conflicts, progress=progress,
                completions=completions, ui={}, guards={})
    return {"version": 1, "student_id": owner, "data": encode(data)}


class ConceptMigrationTests(unittest.TestCase):
    def test_collision_preserves_all_originals_without_averaging_or_replay(self):
        original = legacy_payload()
        untouched = deepcopy(original)
        state = restore(original, "alice", offline_orchestrator)
        self.assertEqual(original, untouched)
        self.assertEqual(len(state["student"].concepts), 2)
        selected = state["student"].get_concept("recursion")
        self.assertEqual((selected.mastery, selected.confidence, selected.attempts), (.8, .6, 3))
        self.assertEqual(state["student"].get_concept("SQL Recursion").mastery, .4)
        archive = state["_concept_identity_archive"]["originals"]
        self.assertEqual(len(archive["concepts"]), 4)
        self.assertEqual(archive["concepts"]["Recursion"].mastery, .2)
        self.assertEqual(len(state["orchestrator"].cognitive_engine.evidence_store.get_all_evidence()), 2)
        self.assertTrue(state["orchestrator"].cognitive_engine.has_conflict("alice", "Python Recursion"))
        payload = capture(state)
        self.assertEqual(capture(restore(payload, "alice", offline_orchestrator)), payload)

    def test_progress_combines_only_proven_independent_sessions(self):
        state = restore(legacy_payload(), "alice", offline_orchestrator)
        tracker = state["learning_progress_tracker"]
        progress = tracker.get_progress("alice", "Python Recursion")
        self.assertEqual(progress.completed_practice_sessions, 2)
        self.assertEqual(progress.total_practice_questions, 15)
        tracker.complete_practice_session("alice", "Recursion", 5, "first")
        self.assertEqual(progress.completed_practice_sessions, 2)
        for kwargs in ({"overlap": True}, {"missing_ids": True}):
            recovered = restore(legacy_payload(**kwargs), "alice", offline_orchestrator)
            record = recovered["learning_progress_tracker"].get_progress("alice", "recursion")
            self.assertEqual(record.completed_practice_sessions, 1)
            self.assertEqual(record.total_practice_questions, 10)
            self.assertTrue(any("need review" in note for note in recovered["_concept_identity_archive"]["notes"]))
            self.assertEqual(len(recovered["_concept_identity_archive"]["originals"]["progress"]), 2)

    def test_old_database_upgrade_and_original_snapshot_backup_are_atomic(self):
        with tempfile.TemporaryDirectory(prefix="phss_identity_migration_") as temp:
            path = Path(temp) / "legacy.sqlite3"
            original = legacy_payload()
            with closing(sqlite3.connect(path)) as db, db:
                db.executescript("CREATE TABLE profiles(student_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at TEXT NOT NULL);"
                    "CREATE TABLE snapshots(student_id TEXT PRIMARY KEY REFERENCES profiles(student_id), revision INTEGER NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL);"
                    "PRAGMA user_version = 1;")
                db.execute("INSERT INTO profiles VALUES ('alice', 'Alice', '2025-01-01')")
                db.execute("INSERT INTO snapshots VALUES (?, ?, ?, ?)", ("alice", 7, json.dumps(original), "2025-01-01"))
            store = SQLiteStudentStore(path)
            self.assertEqual(store.load("alice"), (7, original))
            state = {}
            load_profile(state, store, "alice", offline_orchestrator)
            save_state(state)
            self.assertEqual(store.load("alice")[0], 8)
            self.assertEqual(store.migration_backups("alice"), [(7, original)])
            save_state(state)
            self.assertEqual(store.load("alice")[0], 8)
            self.assertEqual(store.migration_backups("alice"), [(7, original)])
            again = {}
            load_profile(again, store, "alice", offline_orchestrator)
            self.assertEqual(again["student"].get_concept("Recursion").attempts, 3)
            self.assertEqual(again["learning_progress_tracker"].get_progress("alice", "recursion").completed_practice_sessions, 2)

    def test_future_identity_version_is_rejected(self):
        payload = legacy_payload()
        payload["concept_identity_version"] = 999
        with self.assertRaises(ValueError):
            unpack(payload, "alice")

    def test_streamlit_migrates_reports_and_restores_aliases_on_refresh(self):
        from streamlit.testing.v1 import AppTest
        from test_persistence_streamlit import OfflineOrchestrator
        with tempfile.TemporaryDirectory(prefix="phss_identity_ui_") as temp:
            store = SQLiteStudentStore(Path(temp) / "students.sqlite3")
            store.create_profile("Alice", student_id="alice")
            original = legacy_payload()
            store.save("alice", original, 0)
            original_connect = socket.socket.connect
            def local_connect(sock, address):
                if address[0] not in ("127.0.0.1", "::1"):
                    self.fail("Unexpected external network call")
                return original_connect(sock, address)
            with patch("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: store), \
                 patch("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", OfflineOrchestrator), \
                 patch("socket.socket.connect", local_connect):
                for _ in range(2):
                    app = AppTest.from_file(str(Path(__file__).parent / "review_ui.py"), default_timeout=15)
                    app.query_params["student"] = "alice"
                    app.run()
                    self.assertFalse(app.exception, app.exception)
                    self.assertFalse(app.error, [e.value for e in app.error])
                    student = app.session_state.student
                    self.assertIs(student.get_concept("recursion"), student.get_concept("Python Recursion"))
                    self.assertEqual(student.get_concept("recursion").attempts, 3)
                    self.assertEqual(app.session_state.learning_progress_tracker.get_progress(
                        "alice", "Recursion").completed_practice_sessions, 2)
                    self.assertTrue(any(e.label == "Saved topic identities were reconciled" for e in app.expander))
                self.assertEqual(store.migration_backups("alice"), [(1, original)])


if __name__ == "__main__":
    unittest.main()
