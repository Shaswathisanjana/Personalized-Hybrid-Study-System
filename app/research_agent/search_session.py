"""Bounded, profile-persisted academic search using the existing provider layer."""
from dataclasses import asdict, dataclass
import hashlib
import json
import os
import sqlite3
from uuid import uuid4

from app.persistence.research_document_store import StaleDocumentError
from app.research_agent.abstract_quality_validator import AbstractQualityValidator
from app.research_agent.models import ResearchPaper
from app.research_agent.paper_search import AcademicPaperSearch
from app.research_agent.source_identity import source_keys


@dataclass(frozen=True)
class SearchLimits:
    max_target: int = 1000
    page_size: int = 20
    max_pages: int = 50
    max_results: int = 2000
    max_sources: int = 200
    max_abstract_chars: int = 100000
    max_report_sources: int = 100

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in asdict(self).values()) or self.page_size > 100:
            raise ValueError('Research limits must be positive integers; page size cannot exceed 100.')

    @classmethod
    def from_environment(cls):
        return cls(**{name: int(os.getenv('PHSS_RESEARCH_' + name.upper(), default))
                      for name, default in asdict(cls()).items()})


def entry_for(paper):
    keys = sorted(source_keys(paper))
    identity = hashlib.sha256(keys[0].encode()).hexdigest()
    return dict(id=identity, paper=asdict(paper), keys=keys, selected=False)


class ResearchSearchSession:
    def __init__(self, store, student_id, provider=None, limits=None):
        self.store, self.student_id = store, student_id
        self.provider = provider or AcademicPaperSearch()
        self.limits = limits or SearchLimits.from_environment()

    def load(self):
        with self.store._connection() as db:
            if not db.execute('SELECT 1 FROM profiles WHERE student_id=?', (self.student_id,)).fetchone():
                raise ValueError('Unknown student profile.')
            row = db.execute('SELECT record,revision FROM research_search_sessions WHERE student_id=?',
                             (self.student_id,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else (None, 0)

    def save(self, record, revision):
        encoded = json.dumps(record, ensure_ascii=False, allow_nan=False)
        with self.store._connection() as db:
            if revision == 0:
                try:
                    db.execute('INSERT INTO research_search_sessions VALUES(?,?,1)', (self.student_id, encoded))
                except sqlite3.IntegrityError as exc:
                    raise StaleDocumentError('Search changed; reload before continuing.') from exc
            elif db.execute('UPDATE research_search_sessions SET record=?,revision=revision+1 '
                            'WHERE student_id=? AND revision=?', (encoded, self.student_id, revision)).rowcount != 1:
                raise StaleDocumentError('Search changed; reload before continuing.')

    def start(self, topic, target):
        if not isinstance(topic, str) or not topic.strip() or len(topic) > 500:
            raise ValueError('Enter a topic of 1–500 characters.')
        if type(target) is not int or not 1 <= target <= min(self.limits.max_target, self.limits.max_results):
            raise ValueError('Requested target exceeds the configured search limits.')
        _, revision = self.load()
        self.save(dict(search_id=uuid4().hex, topic=topic.strip(), target=target, results=[], cursor='*',
                       pages=0, exhausted=False, warnings=[], error=None), revision)

    def fetch_next(self):
        record, revision = self.load()
        if record is None:
            raise ValueError('Start a search first.')
        validator = AbstractQualityValidator()
        valid_count = sum(validator.validate(e['paper']['abstract'], e['paper']['title']).is_usable
                          for e in record['results'])
        if (record['exhausted'] or record['pages'] >= self.limits.max_pages
                or valid_count >= record['target'] or len(record['results']) >= self.limits.max_results):
            return record
        try:
            page = self.provider.search_page(record['topic'], limit=min(self.limits.page_size, record['target'] - valid_count),
                                             cursor=record['cursor'])
            for paper in page['papers']:
                if not isinstance(paper, ResearchPaper):
                    raise ValueError('Provider returned an invalid paper record.')
                if len(paper.abstract) > self.limits.max_abstract_chars:
                    record['warnings'].append(f'{paper.title}: abstract exceeded the configured character limit; skipped.')
                    continue
                incoming = entry_for(paper)
                old = next((e for e in record['results'] if set(e['keys']) & set(incoming['keys'])), None)
                if old:
                    old['keys'] = sorted(set(old['keys']) | set(incoming['keys']))
                    if (not validator.validate(old['paper']['abstract'], old['paper']['title']).is_usable
                            and validator.validate(paper.abstract, paper.title).is_usable):
                        old['paper'] = incoming['paper']
                elif len(record['results']) < self.limits.max_results:
                    record['results'].append(incoming)
            next_cursor = page.get('next_cursor')
            record['pages'] += 1
            record['exhausted'] = not next_cursor or next_cursor == record['cursor'] or page.get('raw_count') == 0
            record['cursor'] = next_cursor
            record['warnings'] = list(dict.fromkeys(record['warnings'] + page.get('warnings', [])))
            record['error'] = None
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'[:1000]
        self.save(record, revision)
        return record

    def select(self, identity, selected):
        record, revision = self.load()
        entry = next((e for e in (record or {}).get('results', []) if e['id'] == identity), None)
        if entry is None:
            raise ValueError('Result is not part of this student\'s saved search.')
        entry['selected'] = bool(selected)
        self.save(record, revision)
