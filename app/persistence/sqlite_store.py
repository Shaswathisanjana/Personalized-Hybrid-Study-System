"""Atomic, versioned student snapshots using only the Python standard library."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


class StaleSnapshotError(RuntimeError):
    """Another tab has saved a newer version of this student's state."""


class SQLiteStudentStore:
    SCHEMA_VERSION = 5

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, 3, 4, self.SCHEMA_VERSION):
                raise ValueError("Unsupported student database version; no changes made.")
            db.execute("CREATE TABLE IF NOT EXISTS profiles "
                       "(student_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS snapshots "
                       "(student_id TEXT PRIMARY KEY REFERENCES profiles(student_id), "
                       "revision INTEGER NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS concept_migration_backups "
                       "(student_id TEXT NOT NULL REFERENCES profiles(student_id), revision INTEGER NOT NULL, "
                       "payload TEXT NOT NULL, saved_at TEXT NOT NULL, PRIMARY KEY(student_id, revision))")
            db.execute("CREATE TABLE IF NOT EXISTS assessment_transaction_backups "
                       "(student_id TEXT NOT NULL REFERENCES profiles(student_id), revision INTEGER NOT NULL, "
                       "payload TEXT NOT NULL, saved_at TEXT NOT NULL, PRIMARY KEY(student_id, revision))")
            db.execute("CREATE TABLE IF NOT EXISTS research_documents "
                       "(student_id TEXT NOT NULL REFERENCES profiles(student_id), "
                       "document_id TEXT NOT NULL, filename TEXT NOT NULL, pdf BLOB NOT NULL, "
                       "record TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, "
                       "active INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(student_id, document_id))")
            db.execute("CREATE TABLE IF NOT EXISTS research_search_sessions "
                       "(student_id TEXT PRIMARY KEY REFERENCES profiles(student_id), "
                       "record TEXT NOT NULL, revision INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS research_academic_sources "
                       "(student_id TEXT NOT NULL REFERENCES profiles(student_id), source_id TEXT NOT NULL, "
                       "record TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1, "
                       "PRIMARY KEY(student_id,source_id))")
            db.execute("CREATE TABLE IF NOT EXISTS research_report_preferences "
                       "(student_id TEXT PRIMARY KEY REFERENCES profiles(student_id), "
                       "record TEXT NOT NULL, revision INTEGER NOT NULL)")
            db.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def create_profile(self, display_name, student_id=None):
        name = display_name.strip()
        if not name or len(name) > 100:
            raise ValueError("Enter a profile name between 1 and 100 characters.")
        student_id = student_id or uuid4().hex
        if not isinstance(student_id, str) or not student_id.strip():
            raise ValueError("Invalid student identity.")
        with self._connection() as db:
            db.execute("INSERT INTO profiles VALUES (?, ?, ?)",
                       (student_id, name, self._now()))
        return student_id

    def list_profiles(self):
        with self._connection() as db:
            return db.execute("SELECT student_id, display_name FROM profiles ORDER BY created_at, student_id").fetchall()

    def load(self, student_id):
        with self._connection() as db:
            if db.execute("SELECT 1 FROM profiles WHERE student_id = ?", (student_id,)).fetchone() is None:
                raise ValueError("Unknown student profile.")
            row = db.execute("SELECT revision, payload FROM snapshots WHERE student_id = ?", (student_id,)).fetchone()
        return (0, None) if row is None else (row[0], json.loads(row[1]))

    def save(self, student_id, payload, expected_revision):
        # Validate before opening a transaction. Unknown values and NaN must not
        # replace a valid saved snapshot.
        if payload.get("student_id") != student_id or payload.get("version") != 1:
            raise ValueError("Snapshot identity or format does not match.")
        from app.persistence.session_recovery import unpack
        unpack(payload, student_id)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM profiles WHERE student_id = ?", (student_id,)).fetchone() is None:
                raise ValueError("Unknown student profile.")
            row = db.execute("SELECT revision, payload FROM snapshots WHERE student_id = ?", (student_id,)).fetchone()
            revision = row[0] if row else 0
            if revision != expected_revision:
                raise StaleSnapshotError("A newer save exists. Reload this profile before continuing.")
            if row and not json.loads(row[1]).get("assessment_transaction_version") and payload.get("assessment_transaction_version"):
                db.execute("INSERT OR IGNORE INTO assessment_transaction_backups VALUES (?, ?, ?, ?)",
                           (student_id, revision, row[1], self._now()))
            if row and not json.loads(row[1]).get("concept_identity_version") and payload.get("concept_identity_version"):
                # Keep the exact original JSON and revision in the same transaction.
                db.execute("INSERT OR IGNORE INTO concept_migration_backups VALUES (?, ?, ?, ?)",
                           (student_id, revision, row[1], self._now()))
            next_revision = revision + 1
            db.execute("INSERT INTO snapshots VALUES (?, ?, ?, ?) "
                       "ON CONFLICT(student_id) DO UPDATE SET revision=excluded.revision, "
                       "payload=excluded.payload, updated_at=excluded.updated_at",
                       (student_id, next_revision, encoded, self._now()))
        return next_revision

    def migration_backups(self, student_id):
        with self._connection() as db:
            rows = db.execute("SELECT revision, payload FROM concept_migration_backups "
                              "WHERE student_id = ? ORDER BY revision", (student_id,)).fetchall()
        return [(revision, json.loads(payload)) for revision, payload in rows]

    def transaction_backups(self, student_id):
        with self._connection() as db:
            rows = db.execute("SELECT revision, payload FROM assessment_transaction_backups "
                              "WHERE student_id = ? ORDER BY revision", (student_id,)).fetchall()
        return [(revision, json.loads(payload)) for revision, payload in rows]
