"""Dedicated PDF collection UI, reusable beside the existing abstract workflow."""
import streamlit as st
from app.persistence.research_document_store import StaleDocumentError

from app.research_agent.collection_models import FIELDS, MISSING
from app.research_agent.collection_service import ResearchCollectionService
from app.research_agent.full_text_analysis import compare_collection, document_claims


def display_pdf_collection(student):
    try:
        _display_pdf_collection(student)
    except (StaleDocumentError, ValueError) as exc:
        st.warning(f'PDF collection operation stopped: {exc} Reload before retrying. Saved work is retained.')


def _display_pdf_collection(student):
    st.subheader('Uploaded research papers — PDF collection')
    store = st.session_state.get('_persistence_store')
    if store is None:
        st.info('Select a saved student profile to use persistent PDF collections.')
        return
    service = ResearchCollectionService(store, student.user_id)
    limits = service.limits
    st.caption(f'Configured limits: {limits.max_documents} stored documents per student; '
               f'{limits.max_file_bytes / 1048576:g} MiB per PDF; '
               f'{limits.max_collection_bytes / 1048576:g} MiB total; {limits.max_pages} pages per PDF; '
               f'{limits.max_worker_memory_mb} MiB per extraction worker; '
               f'{limits.max_text_chars:,} extracted characters per PDF. '
               f'Each action processes at most {limits.extraction_batch} PDFs or {limits.analysis_batch} analysis chunks '
               f'of {limits.chunk_chars:,} characters. Extraction timeout: {limits.extraction_timeout}s per PDF; '
               f'provider request timeout: {limits.provider_timeout}s, with SDK retries disabled.')
    st.caption('No OCR is installed. Metadata is reported only when supplied by the PDF. '
               'Analysis uses extracted page text, with partial coverage labelled explicitly. '
               'Uploads and analysis do not update mastery. Treat local PDF processing as trusted local use.')
    prefix = 'research_pdf_' + student.user_id
    uploads = st.file_uploader('Upload multiple research PDFs', type=['pdf'], accept_multiple_files=True,
                               key=prefix + '_uploads', max_upload_size=max(1, limits.max_file_bytes // 1048576))
    if st.button('Add uploaded PDFs to collection', key=prefix + '_add'):
        batch = uploads or []
        if len(batch) > limits.max_documents or sum(upload.size for upload in batch) > limits.max_collection_bytes:
            st.warning('This upload selection exceeds the configured document-count or total-byte limit. '
                       'Choose a smaller selection; existing documents were retained.')
            batch = []
        for upload in batch:
            try:
                if upload.size > limits.max_file_bytes:
                    raise ValueError('PDF exceeds the configured per-file limit.')
                _, status = service.add(upload.name, upload.getvalue())
                st.success(f'{upload.name}: {status}.')
            except ValueError as exc:
                st.warning(f'{upload.name}: {exc}')
    extract = st.button('Extract / retry next PDF batch', key=prefix + '_extract')
    analyze = st.button('Analyze / retry next selected chunk batch', key=prefix + '_analyze',
                        help='Sends selected extracted PDF chunks to the configured Gemini provider. May incur API charges.')
    if extract or analyze:
        bar = st.progress(0.0)
        update = lambda done, count: bar.progress(done / count)
        with st.spinner('Processing a bounded batch. Completed work is saved after each unit.'):
            count = service.extract_batch(update) if extract else service.analyze_batch(update)
        st.info(f'Processed {count} unit(s). Use the button again for remaining or failed work. '
                'Analysis may make Gemini calls; extraction is local.')
    documents = service.list()
    st.write(f'Active documents: {len(documents)}')
    st.caption('Remove excludes a paper from the active collection. Original data is retained in the local '
               'database for recovery and still counts toward storage limits. It affects only this profile. '
               'Clearing study progress does not erase stored PDFs.')
    if documents:
        st.dataframe([dict(filename=d['filename'], document_id=d['document_id'],
                           status=d['record']['status'], analyzed_chunks=len(d['record']['analysis']),
                           total_chunks=len(d['record']['chunks']), selected=d['record'].get('selected', True))
                      for d in documents])
        inspected = st.selectbox('Inspect a PDF document', [d['document_id'] for d in documents],
                                 format_func=lambda identity: next(d['filename'] for d in documents
                                                                  if d['document_id'] == identity),
                                 key=prefix + '_inspect')
    else:
        inspected = None
    for document in (d for d in documents if d['document_id'] == inspected):
        record, document_id = document['record'], document['document_id']
        title = record.get('metadata', {}).get('title') or '[Title unknown] ' + document['filename']
        with st.expander(title):
            st.caption(f"Document ID (SHA-256): {document_id} | {document['filename']} | {record['status']}")
            st.write('PDF-supplied metadata:', record.get('metadata', {}))
            selected = st.checkbox('Include in active analysis', value=record.get('selected', True),
                                   key=prefix + '_select_' + document_id)
            if selected != record.get('selected', True):
                service.select(document_id, selected)
            if st.button('Remove from active collection', key=prefix + '_remove_' + document_id):
                service.remove(document_id)
                st.rerun()
            for warning in record.get('warnings', []):
                st.warning(warning)
            total, completed = len(record['chunks']), len(record['analysis'])
            st.write(f'Analyzed chunks: {completed}/{total}. Source scope: extracted PDF page text.')
            for error in record.get('analysis_errors', {}).values():
                st.warning(error)
            if record['analysis']:
                for field, claims in document_claims(document).items():
                    st.markdown('**' + field.replace('_', ' ').title() + '**')
                    if not claims:
                        st.write(MISSING if completed == total else 'Not yet established from analyzed chunks.')
                    for claim in claims:
                        st.write(claim['quote'])
                        st.caption(f"Page {claim['page']}, chunk {claim['chunk_id']}, document {document_id}")
            if st.checkbox('Show extracted page text', key=prefix + '_showtext_' + document_id):
                if record['chunks']:
                    chunk_id = st.selectbox('Page/chunk to inspect', [c['chunk_id'] for c in record['chunks']],
                                            key=prefix + '_chunk_' + document_id)
                    chunk = next(c for c in record['chunks'] if c['chunk_id'] == chunk_id)
                    st.caption(f"Page {chunk['page']} — {chunk['chunk_id']}")
                    st.text(chunk['text'])
    selected_docs = [d for d in service.list() if d['record'].get('selected', True) and d['record']['analysis']]
    if selected_docs:
        st.subheader('Collection comparison and evidence synthesis')
        st.caption('PDF excerpt analysis, including unfinished documents where labelled. '
                   'Comparison cells use the first supported excerpt per field; individual analyses retain all excerpts. '
                   'Themes below organize evidence by field, without asserting unverified semantic similarities.')
        report = compare_collection('Uploaded paper collection', selected_docs)
        if report['comparison']:
            from app.research_agent.methodology_comparator import MethodologyComparator
            st.markdown(MethodologyComparator.to_markdown(report['comparison']))
        for field in FIELDS:
            supported = [d for d in report['evidence'] if d['claims'][field]]
            if supported:
                with st.expander(f"Evidence theme — {field.replace('_', ' ').title()}: "
                                 f"{len(supported)}/{len(selected_docs)} analyzed documents"):
                    wording = {}
                    for source in supported:
                        item = source['claims'][field][0]
                        wording.setdefault(' '.join(item['quote'].casefold().split()), []).append(source['title'])
                        st.write(source['title'] + ': ' + item['quote'])
                        st.caption(f"Document {source['document_id']}, page {item['page']}, chunk {item['chunk_id']}")
                    shared = [titles for titles in wording.values() if len(titles) > 1]
                    if shared:
                        st.write('Matching source wording:', shared)
                    if len(wording) > 1:
                        st.write(f'{len(wording)} distinct source descriptions appear for this field. '
                                 'Different wording alone does not establish different methods or conflicting findings.')
        for candidate in report['gaps'].candidates:
            st.write('Preliminary opportunity based on a reported limitation:', candidate.reported_limitation)
            st.caption(f'{candidate.paper_title} — {candidate.paper_url}; verify broader literature before claiming a gap.')
        for direction in report['proposal'].directions:
            st.write('AI-system suggestion, not a paper finding:', direction.objective)
            st.caption(direction.source_paper + ' — ' + direction.source_url)
