"""Durable assessment stages. Successful stages are never rerun on retry.

The app supplies a persistence callback; standalone runtimes work in memory.
A provider response lost before it was saved may require another provider call.
Committed cognitive evidence is protected separately by its stable evidence ID.
"""
from copy import deepcopy
from dataclasses import asdict, is_dataclass
import hashlib
import json
from threading import RLock
from uuid import uuid4


def fingerprint(value):
    def convert(item):
        if is_dataclass(item):
            return asdict(item)
        raise TypeError("Unsupported assessment request value.")
    return hashlib.sha256(json.dumps(value, default=convert, sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def lock_for(engine):
    if "_assessment_lock" not in vars(engine):
        engine._assessment_lock = RLock()
    return engine._assessment_lock


def persist(engine):
    callback = vars(engine).get("persist_state")
    if callback is not None:
        callback()


def assessment(engine, student, assessment_id, request):
    if not isinstance(assessment_id, str) or not assessment_id:
        raise ValueError("Assessment ID is required.")
    with lock_for(engine):
        if "assessment_records" not in vars(engine):
            engine.assessment_records = {}
        key = (student.user_id, assessment_id)
        digest = fingerprint(request)
        record = engine.assessment_records.get(key)
        if record is not None:
            if record["fingerprint"] != digest:
                raise ValueError("This assessment ID already belongs to a different answer or question.")
            return record
        record = {"user_id": student.user_id, "assessment_id": assessment_id,
                  "fingerprint": digest, "request": deepcopy(request), "stages": {}}
        engine.assessment_records[key] = record
        try:
            persist(engine)
        except BaseException:
            del engine.assessment_records[key]
            raise
        return record


def once(engine, record, name, operation):
    with lock_for(engine):
        stages = record["stages"]
        if name in stages:
            return stages[name]
        # A new claim forces a SQLite revision check before any provider work.
        record["attempt_token"] = uuid4().hex
        persist(engine)
        result = operation()
        stages[name] = result
        try:
            persist(engine)
        except BaseException:
            stages.pop(name, None)
            raise
        return result
