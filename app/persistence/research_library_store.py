"""Persistent abstract-only additions to the existing PDF research collection."""
import json

from app.persistence.research_document_store import ResearchDocumentStore, StaleDocumentError
from app.research_agent.abstract_quality_validator import AbstractQualityValidator
from app.research_agent.search_session import SearchLimits, entry_for
from app.research_agent.collection_models import CollectionLimits


class UnifiedResearchDocumentStore:
    def __init__(self, store, limits=None):
        self.store, self.pdfs = store, ResearchDocumentStore(store)
        self.limits = limits or SearchLimits.from_environment()

    def list(self, student_id):
        pdfs = self.pdfs.list(student_id)
        with self.store._connection() as db:
            ResearchDocumentStore._owner(db, student_id)
            rows = db.execute('SELECT source_id,record,revision FROM research_academic_sources '
                              'WHERE student_id=? AND active=1 ORDER BY rowid', (student_id,)).fetchall()
        return pdfs + [dict(document_id=i, filename=json.loads(r)['metadata']['title'],
                           record=json.loads(r), revision=v) for i, r, v in rows]

    def add_paper(self, student_id, paper):
        if len(paper.abstract) > self.limits.max_abstract_chars:
            raise ValueError('Abstract exceeds the configured character limit.')
        entry = entry_for(paper)
        quality = AbstractQualityValidator().validate(paper.abstract, paper.title)
        width = CollectionLimits.from_environment().chunk_chars
        identity = 'academic:' + entry['id']
        record = dict(source_scope='abstract_only', status='ready' if quality.is_usable else 'excluded',
                      metadata=dict(title=paper.title, authors=paper.authors, author=', '.join(paper.authors),
                                    year=paper.year, doi=paper.doi, url=paper.url, provider=paper.source,
                                    paper_id=paper.paper_id),
                      selected=True, publication_keys=entry['keys'],
                      chunks=[dict(chunk_id=f'abstract-c{start // width + 1}', page=None,
                                   text=paper.abstract[start:start + width], source_scope='abstract_only')
                              for start in range(0, len(paper.abstract), width)] if quality.is_usable else [],
                      warnings=['Abstract-only source; no full-text PDF was retrieved or analyzed.'] +
                               ([] if quality.is_usable else [quality.reason]),
                      analysis={}, analysis_errors={})
        with self.store._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            ResearchDocumentStore._owner(db, student_id)
            rows = db.execute('SELECT source_id,record,active FROM research_academic_sources WHERE student_id=?',
                              (student_id,)).fetchall()
            for old_id, raw, active in rows:
                old = json.loads(raw)
                if set(old['publication_keys']) & set(entry['keys']):
                    if old['status'] == 'excluded' and quality.is_usable:
                        db.execute('UPDATE research_academic_sources SET record=?,active=1,revision=revision+1 '
                                   'WHERE student_id=? AND source_id=?', (json.dumps(record), student_id, old_id))
                        return old_id, 'upgraded'
                    if not active:
                        db.execute('UPDATE research_academic_sources SET active=1,revision=revision+1 '
                                   'WHERE student_id=? AND source_id=?', (student_id, old_id))
                    return old_id, 'duplicate' if active else 'reactivated'
            if len(rows) >= self.limits.max_sources:
                raise ValueError('Configured stored academic-source limit reached (including inactive sources).')
            db.execute('INSERT INTO research_academic_sources(student_id,source_id,record) VALUES(?,?,?)',
                       (student_id, identity, json.dumps(record)))
        return identity, 'added' if quality.is_usable else 'added metadata only; abstract rejected'

    def get(self, student_id, document_id, **kwargs):
        if not document_id.startswith('academic:'):
            return self.pdfs.get(student_id, document_id, **kwargs)
        with self.store._connection() as db:
            row = db.execute('SELECT record,revision FROM research_academic_sources '
                             'WHERE student_id=? AND source_id=? AND active=1', (student_id, document_id)).fetchone()
        if row is None:
            raise ValueError('Source is not in this student\'s active collection.')
        record = json.loads(row[0])
        return dict(document_id=document_id, filename=record['metadata']['title'], record=record, revision=row[1])

    def update(self, student_id, document_id, record, revision):
        if not document_id.startswith('academic:'):
            return self.pdfs.update(student_id, document_id, record, revision)
        with self.store._connection() as db:
            if db.execute('UPDATE research_academic_sources SET record=?,revision=revision+1 '
                          'WHERE student_id=? AND source_id=? AND revision=? AND active=1',
                          (json.dumps(record, allow_nan=False), student_id, document_id, revision)).rowcount != 1:
                raise StaleDocumentError('Academic source changed or was removed; reload before retrying.')

    def remove(self, student_id, document_id, revision):
        if not document_id.startswith('academic:'):
            return self.pdfs.remove(student_id, document_id, revision)
        with self.store._connection() as db:
            if db.execute('UPDATE research_academic_sources SET active=0,revision=revision+1 '
                          'WHERE student_id=? AND source_id=? AND revision=? AND active=1',
                          (student_id, document_id, revision)).rowcount != 1:
                raise StaleDocumentError('Academic source changed or was removed; reload before retrying.')
