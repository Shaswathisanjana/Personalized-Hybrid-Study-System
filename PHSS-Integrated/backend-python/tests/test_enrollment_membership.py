"""Enrollment boundary tests without external model or database services."""
import ast
import unittest
from pathlib import Path
from datetime import datetime, timezone

SOURCE = Path(__file__).parents[1] / "app/agents/learning/service.py"

class Collection:
    def __init__(self, docs=()):
        self.docs = list(docs)
    def find_one(self, query):
        return next((d for d in self.docs if all(d.get(k) == v for k,v in query.items())), None)
    def update_one(self, query, update, upsert=False):
        if not self.find_one(query):
            self.docs.append({**query, **update["$setOnInsert"]})

class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        class DB: pass
        self.db = DB()
        self.db.learning_plans = Collection([
            {"userId":"alice", "topic":"Python", "steps":[{"title":"Loops"}]},
            {"userId":"bob", "topic":"SQL", "steps":[{"title":"Joins"}]},
            {"userId":"alice", "topic":"Empty", "steps":[]},
        ])
        self.db.course_enrollments = Collection()
        tree = ast.parse(SOURCE.read_text())
        node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="enroll_course")
        namespace = {"get_db":lambda:self.db, "datetime":datetime, "timezone":timezone}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),"exec"),namespace)
        self.enroll = namespace["enroll_course"]
    def test_preview_does_not_enroll(self):
        self.assertEqual(self.db.course_enrollments.docs, [])
    def test_repeat_enroll_is_idempotent(self):
        self.enroll("alice","Python")
        self.enroll("alice","Python")
        self.assertEqual(len(self.db.course_enrollments.docs),1)
    def test_other_users_roadmap_rejected(self):
        with self.assertRaises(ValueError): self.enroll("alice","SQL")
    def test_empty_roadmap_rejected(self):
        with self.assertRaises(ValueError): self.enroll("alice","Empty")
    def test_listing_uses_enrollment_not_history(self):
        source=SOURCE.read_text().split("def get_learning_journeys",1)[1].split("def enroll_course",1)[0]
        self.assertIn('course_enrollments.find({"userId": user_id})',source)
        self.assertIn('"topic": {"$in": enrolled_topics}',source)
        self.assertNotIn("repository.get_learning_journeys",source)

if __name__=="__main__": unittest.main()
