"""Profile-owned PDF blobs and JSON jobs in the existing SQLite database."""
import hashlib
import json
from pathlib import Path


class StaleDocumentError(RuntimeError):
    pass


class ResearchDocumentStore:
    def __init__(self, student_store):
        self.store = student_store

    @staticmethod
    def _owner(db, student_id):
        if not db.execute('SELECT 1 FROM profiles WHERE student_id=?', (student_id,)).fetchone():
            raise ValueError('Unknown student profile.')

    def list(self, student_id):
        with self.store._connection() as db:
            self._owner(db, student_id)
            rows = db.execute('SELECT document_id,filename,length(pdf),record,revision FROM research_documents '
                              'WHERE student_id=? AND active=1 ORDER BY rowid', (student_id,)).fetchall()
        return [dict(document_id=i, filename=f, size=size, record=json.loads(r), revision=v)
                for i, f, size, r, v in rows]

    def add(self, student_id, filename, content, limits):
        if not isinstance(content, bytes) or not content or len(content) > limits.max_file_bytes:
            raise ValueError('PDF is empty or exceeds the configured per-file byte limit.')
        if not content.lstrip().startswith(b'%PDF-'):
            raise ValueError('The supplied file does not have a PDF header.')
        document_id = hashlib.sha256(content).hexdigest()
        filename = Path(str(filename).replace('\\', '/')).name[:240] or 'Uploaded document.pdf'
        record = dict(status='queued', selected=True, metadata={}, chunks=[], warnings=[],
                      analysis={}, analysis_errors={})
        with self.store._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self._owner(db, student_id)
            old = db.execute('SELECT active FROM research_documents WHERE student_id=? AND document_id=?',
                             (student_id, document_id)).fetchone()
            if old:
                if not old[0]:
                    db.execute('UPDATE research_documents SET active=1,revision=revision+1 '
                               'WHERE student_id=? AND document_id=?', (student_id, document_id))
                return document_id, 'duplicate' if old[0] else 'reactivated'
            # Include inactive blobs: removal must not bypass stored-byte quotas.
            count, size = db.execute('SELECT count(*),coalesce(sum(length(pdf)),0) FROM research_documents '
                                     'WHERE student_id=?', (student_id,)).fetchone()
            if count >= limits.max_documents or size + len(content) > limits.max_collection_bytes:
                raise ValueError('The configured stored-document count or collection byte limit was reached.')
            db.execute('INSERT INTO research_documents(student_id,document_id,filename,pdf,record) '
                       'VALUES(?,?,?,?,?)', (student_id, document_id, filename, content, json.dumps(record)))
        return document_id, 'added'

    def get(self, student_id, document_id, *, include_pdf=False):
        with self.store._connection() as db:
            self._owner(db, student_id)
            row = db.execute('SELECT filename,record,revision' + (',pdf' if include_pdf else '') +
                             ' FROM research_documents WHERE student_id=? AND document_id=? AND active=1',
                             (student_id, document_id)).fetchone()
        if row is None:
            raise ValueError('Document is not in this student\'s active collection.')
        result = dict(document_id=document_id, filename=row[0], record=json.loads(row[1]), revision=row[2])
        if include_pdf:
            result['pdf'] = row[3]
        return result

    def update(self, student_id, document_id, record, revision):
        encoded = json.dumps(record, ensure_ascii=False, allow_nan=False)
        with self.store._connection() as db:
            changed = db.execute('UPDATE research_documents SET record=?,revision=revision+1 '
                                 'WHERE student_id=? AND document_id=? AND revision=? AND active=1',
                                 (encoded, student_id, document_id, revision)).rowcount
            if changed != 1:
                raise StaleDocumentError('Document changed or was removed. Reload before retrying.')

    def remove(self, student_id, document_id, revision):
        with self.store._connection() as db:
            changed = db.execute('UPDATE research_documents SET active=0,revision=revision+1 '
                                 'WHERE student_id=? AND document_id=? AND revision=? AND active=1',
                                 (student_id, document_id, revision)).rowcount
            if changed != 1:
                raise StaleDocumentError('Document changed or was removed. Reload before retrying.')
