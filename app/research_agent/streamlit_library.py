"""Mixed-source analysis and selectable Word export; no mastery mutations."""
import json
import streamlit as st

from app.persistence.research_document_store import StaleDocumentError
from app.persistence.research_library_store import UnifiedResearchDocumentStore
from app.research_agent.collection_service import ResearchCollectionService
from app.research_agent.docx_exporter import SECTIONS, build_docx
from app.research_agent.full_text_analysis import compare_collection, document_claims
from app.research_agent.research_report import report_sources, workflow_report_sources


def display_research_library(student):
    st.subheader('Research collection — PDFs and academic abstracts')
    store = st.session_state.get('_persistence_store')
    if store is None:
        return
    try:
        documents = UnifiedResearchDocumentStore(store)
        service = ResearchCollectionService(store, student.user_id, document_store=documents)
        prefix = 'research_library_' + student.user_id
        st.caption(f"Stored academic-source limit: {documents.limits.max_sources}; "
                   f"maximum report selection: {documents.limits.max_report_sources} sources. "
                   'PDF upload limits remain displayed in the PDF section. '
                   'Analysis sends selected chunks to Gemini and may incur charges. Viewing/exporting adds no mastery evidence.')
        if st.button('Analyze / retry mixed collection batch', key=prefix + '_analyze'):
            bar = st.progress(0.0)
            count = service.analyze_batch(lambda done, total: bar.progress(done / total))
            st.info(f'Processed {count} chunk(s); successful results are saved for retry/refresh.')
        all_documents = service.list()
        st.dataframe([dict(title=d['record']['metadata'].get('title') or d['filename'],
                           source_scope=d['record'].get('source_scope', 'full_text_excerpts'),
                           analyzed_chunks=len(d['record']['analysis']), total_chunks=len(d['record']['chunks']),
                           selected=d['record'].get('selected', True), status=d['record']['status']) for d in all_documents])
        abstracts = [d for d in all_documents if d['record'].get('source_scope') == 'abstract_only']
        if abstracts:
            identity = st.selectbox('Inspect academic collection source', [d['document_id'] for d in abstracts],
                                    format_func=lambda i: next(d['filename'] for d in abstracts if d['document_id'] == i),
                                    key=prefix + '_inspect')
            source = documents.get(student.user_id, identity)
            record = source['record']
            selected = st.checkbox('Include academic source in analysis', value=record['selected'], key=prefix + '_include_' + identity)
            if selected != record['selected']:
                service.select(identity, selected)
            if st.button('Remove academic source from active collection', key=prefix + '_remove'):
                service.remove(identity)
                st.rerun()
            for warning in record['warnings'] + list(record['analysis_errors'].values()):
                st.warning(warning)
            for field, claims in document_claims(source).items():
                for claim in claims:
                    st.write(field.replace('_', ' ').title() + ': ' + claim['quote'])
                    st.caption('Abstract-only, ' + claim['chunk_id'] + '; ' + (record['metadata'].get('url') or identity))
        current = [d for d in service.list() if d['record'].get('selected', True)]
        sources = report_sources(current)
        legacy = st.session_state.get('advanced_research_result')
        if legacy is not None:
            existing_urls = {s['url'] for s in sources if s['url']}
            sources += [s for s in workflow_report_sources(legacy) if not s['url'] or s['url'] not in existing_urls]
        if not sources:
            st.info('Add or select collection sources to prepare a research report.')
            return
        if any(d['record']['analysis'] for d in current):
            comparison = compare_collection('Selected research collection', current)['comparison']
            if comparison:
                from app.research_agent.methodology_comparator import MethodologyComparator
                st.caption('Mixed-source comparison; full text and abstract coverage are labelled independently.')
                st.markdown(MethodologyComparator.to_markdown(comparison))
        with store._connection() as db:
            row = db.execute('SELECT record,revision FROM research_report_preferences WHERE student_id=?',
                             (student.user_id,)).fetchone()
        preferences, revision = (json.loads(row[0]), row[1]) if row else ({}, 0)
        identities = [s['id'] for s in sources]
        labels = {s['id']: s['title'] + ' — ' + s['scope'] for s in sources}
        with st.form(prefix + '_report'):
            title = st.text_input('Word report title', value=preferences.get('title', 'Research Analysis Report'),
                                  max_chars=200, key=prefix + '_title')
            topic = st.text_input('Word report research topic', value=preferences.get('topic', ''),
                                  max_chars=500, key=prefix + '_topic')
            chosen = st.multiselect('Papers to include in Word report', identities,
                                     default=[i for i in preferences.get('sources', identities) if i in identities],
                                     format_func=labels.get, key=prefix + '_sources')
            sections = st.multiselect('Word report sections', list(SECTIONS),
                                       default=preferences.get('sections', list(SECTIONS)),
                                       format_func=SECTIONS.get, key=prefix + '_sections')
            generate = st.form_submit_button('Generate Research Report (.docx)')
        if generate:
            if len(chosen) > documents.limits.max_report_sources:
                raise ValueError('Report selection exceeds the configured source-count limit.')
            output = build_docx(title, topic, [s for s in sources if s['id'] in chosen], sections)
            saved = json.dumps(dict(title=title, topic=topic, sources=chosen, sections=sections))
            with store._connection() as db:
                if revision == 0:
                    db.execute('INSERT INTO research_report_preferences VALUES(?,?,1)', (student.user_id, saved))
                elif db.execute('UPDATE research_report_preferences SET record=?,revision=revision+1 '
                                'WHERE student_id=? AND revision=?', (saved, student.user_id, revision)).rowcount != 1:
                    raise StaleDocumentError('Report selection changed in another tab; reload.')
            st.download_button('Download Research Report (.docx)', output, file_name='research_report.docx',
                               mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            st.caption('Report includes available selected evidence only. Missing sections are omitted rather than invented. '
                       'Coverage notices and claim attribution remain even when optional sections are unchecked.')
    except (ValueError, StaleDocumentError) as exc:
        st.warning('Collection/report operation stopped: ' + str(exc))
