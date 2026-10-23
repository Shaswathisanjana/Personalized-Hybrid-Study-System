"""Explicit identity migration; old scores are never averaged or replayed.

The most recently updated assessed state is the operational estimate when old
aliases collide. All original states/records remain in the identity archive.
Counts combine only when complete, disjoint session IDs prove independence.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import timezone

from app.cognitive.concept_identity import concept_id, IDENTITY_VERSION


def _time(value):
    return value.replace(tzinfo=timezone.utc).timestamp() if value.tzinfo is None else value.timestamp()


def migrate_concepts(data):
    """Migrate detached decoded data in place. Repeated calls are idempotent."""
    student = data["student"]
    before = deepcopy({key: data[key] for key in ("progress", "completions", "conflicts")})
    before["concepts"] = deepcopy(student.concepts)
    notes = []
    groups = defaultdict(list)
    for name, state in student.concepts.items():
        groups[concept_id(name)].append((name, state))
    concepts = {}
    for identity, entries in groups.items():
        # A newly viewed neutral prior must not replace assessed knowledge.
        name, winner = max(entries, key=lambda item: (
            item[1].attempts > 0, _time(item[1].last_updated), item[0]))
        concepts[name] = winner
        if len(entries) > 1:
            notes.append(f"{identity}: retained the newest assessed estimate ({name}); "
                         "all original estimates are archived. No scores were combined.")
    student.concepts = concepts

    progress = {}
    groups = defaultdict(list)
    for (owner, name), record in data["progress"].items():
        groups[(owner, concept_id(name))].append(((owner, name), record))
    for key, entries in groups.items():
        if len(entries) == 1:
            progress[key] = entries[0][1]
            continue
        ids_by_record = [
            {cid for owner, topic, cid in data["completions"] if (owner, topic) == old_key}
            for old_key, _ in entries
        ]
        complete = all(len(ids) == record.completed_practice_sessions
                       for ids, (_, record) in zip(ids_by_record, entries))
        independent = sum(map(len, ids_by_record)) == len(set().union(*ids_by_record))
        if complete and independent:
            # Every counted session is identified, and the identifiers don't overlap.
            record = deepcopy(min(entries, key=lambda item: _time(item[1].started_at))[1])
            record.last_activity_at = max((r.last_activity_at for _, r in entries), key=_time)
            record.completed_practice_sessions = sum(r.completed_practice_sessions for _, r in entries)
            record.total_practice_questions = sum(r.total_practice_questions for _, r in entries)
            record.events = sorted([e for _, r in entries for e in r.events], key=lambda e: _time(e.recorded_at))
            notes.append(f"{key[1]}: combined progress with complete, disjoint session IDs.")
        else:
            record = max(entries, key=lambda item: _time(item[1].last_activity_at))[1]
            notes.append(f"{key[1]}: progress counts need review because session IDs overlap "
                         "or are incomplete. The newest record is displayed; originals are archived.")
        progress[key] = record
    data["progress"] = progress
    data["completions"] = {(owner, concept_id(topic), cid)
                           for owner, topic, cid in data["completions"]}

    conflicts = {}
    for (owner, name), records in data["conflicts"].items():
        conflicts.setdefault((owner, concept_id(name)), []).extend(records)
    data["conflicts"] = conflicts
    archive = data.setdefault("identity_archive", {})
    if notes and not archive:
        archive.update(version=IDENTITY_VERSION, originals=before, notes=notes)
    elif notes:
        # Retain the first pre-migration archive and any later collision separately.
        archive.setdefault("later_collisions", []).append({"originals": before, "notes": notes})
    return data
