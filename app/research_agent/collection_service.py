"""Bounded, resumable collection operations, deliberately independent of CACM."""
from app.persistence.research_document_store import ResearchDocumentStore
from app.research_agent.collection_models import CollectionLimits
from app.research_agent.pdf_extractor import extract_pdf
from app.research_agent.full_text_analysis import GroundedChunkAnalyzer, validate_claims


class ResearchCollectionService:
    def __init__(self, student_store, student_id, limits=None, extractor=None, analyzer=None, document_store=None):
        self.documents = document_store or ResearchDocumentStore(student_store)
        self.student_id = student_id
        self.limits = limits or CollectionLimits.from_environment()
        self.extractor = extractor or extract_pdf
        self.analyzer = analyzer

    def list(self):
        return self.documents.list(self.student_id)

    def add(self, filename, content):
        return self.documents.add(self.student_id, filename, content, self.limits)

    def select(self, document_id, selected):
        document = self.documents.get(self.student_id, document_id)
        document['record']['selected'] = bool(selected)
        self.documents.update(self.student_id, document_id, document['record'], document['revision'])

    def remove(self, document_id):
        document = self.documents.get(self.student_id, document_id)
        self.documents.remove(self.student_id, document_id, document['revision'])

    def extract_batch(self, progress=None):
        pending = [d for d in self.list() if d['record']['status'] in ('queued', 'extraction_error')]
        pending = pending[:self.limits.extraction_batch]
        for index, item in enumerate(pending, 1):
            document = self.documents.get(self.student_id, item['document_id'], include_pdf=True)
            record = document['record']
            if record['status'] not in ('queued', 'extraction_error'):
                continue
            try:
                result = self.extractor(document['pdf'], self.limits)
            except Exception:
                result = dict(status='extraction_error', metadata={}, chunks=[],
                              warnings=['Extraction failed. Explicit retry is available.'])
            record.update(result)
            self.documents.update(self.student_id, document['document_id'], record, document['revision'])
            if progress:
                progress(index, len(pending))
        return len(pending)

    def analyze_batch(self, progress=None):
        pending = [(d['document_id'], c) for d in self.list()
                   if d['record']['status'] == 'ready' and d['record'].get('selected', True)
                   for c in d['record']['chunks'] if c['chunk_id'] not in d['record']['analysis']]
        errors = {d['document_id']: d['record']['analysis_errors'] for d in self.list()}
        pending.sort(key=lambda item: item[1]['chunk_id'] in errors[item[0]])
        pending = pending[:self.limits.analysis_batch]
        for index, (document_id, chunk) in enumerate(pending, 1):
            document = self.documents.get(self.student_id, document_id)
            record = document['record']
            if chunk['chunk_id'] in record['analysis'] or not record.get('selected', True):
                continue
            try:
                if self.analyzer is None:
                    self.analyzer = GroundedChunkAnalyzer(timeout_seconds=self.limits.provider_timeout)
                fields = validate_claims(chunk, self.analyzer.analyze(chunk))
                record['analysis'][chunk['chunk_id']] = fields
                record['analysis_errors'].pop(chunk['chunk_id'], None)
            except Exception as exc:
                record['analysis_errors'][chunk['chunk_id']] = f'{type(exc).__name__}: {exc}'[:1000]
            self.documents.update(self.student_id, document_id, record, document['revision'])
            if progress:
                progress(index, len(pending))
        return len(pending)
