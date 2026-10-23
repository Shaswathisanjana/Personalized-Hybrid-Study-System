"""Explicit academic search, incremental retrieval and persistent source selection."""
import streamlit as st

from app.persistence.research_document_store import StaleDocumentError
from app.persistence.research_library_store import UnifiedResearchDocumentStore
from app.research_agent.abstract_quality_validator import AbstractQualityValidator
from app.research_agent.models import ResearchPaper
from app.research_agent.search_session import ResearchSearchSession


def display_topic_search(student):
    st.subheader('Search Research Papers by Topic')
    store = st.session_state.get('_persistence_store')
    if store is None:
        st.info('Select a saved student profile to persist search and collection selections.')
        return
    try:
        session = ResearchSearchSession(store, student.user_id)
        limits = session.limits
        record, _ = session.load()
        prefix = 'research_search_' + student.user_id
        st.caption(f'OpenAlex retrieval; abstract-only coverage. Target up to {min(limits.max_target, limits.max_results)} '
                   f'usable abstracts; at most {limits.page_size} results per explicit request, '
                   f'{limits.max_pages} pages and {limits.max_results} saved results per search. '
                   'Targets depend on available sources and abstract quality; they are not guaranteed.')
        st.caption('For cursor paging beyond the first page, configure a private OPENALEX_API_KEY '
                   'as required by the provider. Keys are never stored in search records or report references.')
        with st.form(prefix + '_form'):
            topic = st.text_input('Academic search topic', value=record['topic'] if record else '', max_chars=500,
                                  key=prefix + '_topic')
            target = st.number_input('Desired number of research papers', min_value=1,
                                     max_value=min(limits.max_target, limits.max_results),
                                     value=min(record['target'] if record else 10, limits.max_target, limits.max_results),
                                     key=prefix + '_target')
            submitted = st.form_submit_button('Search academic papers')
        if submitted:
            session.start(topic, target)
            record = session.fetch_next()
        record, _ = session.load()
        if record is None:
            return
        st.caption('Saved search topic: ' + record['topic'] + '. Use Search academic papers to start a different topic.')
        if record['error']:
            st.warning('Retrieval stopped: ' + record['error'] + '. Earlier results and selections remain saved.')
        for warning in record['warnings']:
            st.warning(warning)
        validator = AbstractQualityValidator()
        valid = sum(validator.validate(e['paper']['abstract'], e['paper']['title']).is_usable for e in record['results'])
        st.write(f"Saved results: {len(record['results'])}; usable abstracts: {valid}/{record['target']} target; pages fetched: {record['pages']}.")
        done = (record['exhausted'] or record['pages'] >= limits.max_pages or valid >= record['target']
                or len(record['results']) >= limits.max_results)
        if done and valid < record['target']:
            st.warning('The provider or configured retrieval bound was reached before the usable-paper target. '
                       'Rejected/missing abstracts and provider warnings are retained; no replacement papers were invented.')
        if st.button('Load more / retry academic search', key=prefix + '_more', disabled=done):
            session.fetch_next()
            st.rerun()
        text = st.text_input('Filter saved results by title or author', key=prefix + '_filter').casefold().strip()
        usable_only = st.checkbox('Show only usable abstracts', key=prefix + '_usable')
        entries = [e for e in record['results'] if not text or text in
                   (e['paper']['title'] + ' ' + ' '.join(e['paper']['authors'])).casefold()]
        if usable_only:
            entries = [e for e in entries if validator.validate(e['paper']['abstract'], e['paper']['title']).is_usable]
        page_count = max(1, (len(entries) + limits.page_size - 1) // limits.page_size)
        page = st.selectbox('Saved result page', list(range(1, page_count + 1)), key=prefix + '_display_page')
        for entry in entries[(page - 1) * limits.page_size:page * limits.page_size]:
            paper = entry['paper']
            with st.expander(paper['title']):
                st.write('Authors:', ', '.join(paper['authors']) or 'Not supplied')
                st.write('Year:', paper['year'] or 'Not supplied')
                st.write('DOI:', paper.get('doi') or 'Not supplied')
                st.write('Source link:', paper['url'] or 'Not supplied')
                st.write('Abstract:', paper['abstract'] or 'Not supplied')
                quality = validator.validate(paper['abstract'], paper['title'])
                st.caption('Abstract-only. ' + ('Usable abstract.' if quality.is_usable else 'Rejected abstract: ' + quality.reason))
                selected = st.checkbox('Select search result', value=entry['selected'],
                                       key=prefix + '_' + record['search_id'] + '_' + entry['id'])
                if selected != entry['selected']:
                    session.select(entry['id'], selected)
        if st.button('Add selected search results to collection', key=prefix + '_add'):
            current, _ = session.load()
            collection = UnifiedResearchDocumentStore(store, limits)
            for entry in current['results']:
                if entry['selected']:
                    try:
                        _, status = collection.add_paper(student.user_id, ResearchPaper(**entry['paper']))
                        st.success(entry['paper']['title'] + ': ' + status)
                    except ValueError as exc:
                        st.warning(str(exc))
    except (ValueError, StaleDocumentError) as exc:
        st.warning('Academic search operation stopped: ' + str(exc))
