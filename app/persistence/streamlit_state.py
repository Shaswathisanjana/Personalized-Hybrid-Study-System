"""Profile loading and explicit checkpoints for the existing Streamlit pages."""
from functools import wraps
from pathlib import Path

from app.persistence.session_recovery import capture, restore, UI_KEYS, SERVICE_KEYS
from app.persistence.sqlite_store import SQLiteStudentStore
from app.cognitive.concept_identity import IDENTITY_VERSION


def load_profile(state, store, student_id, orchestrator_factory):
    from app.cognitive.cognitive_engine import CognitiveEngine
    from app.cognitive.models import StudentCognitiveModel
    from app.learning_agent.progress_tracker import LearningProgressTracker
    current_page = state.get("_app_page")
    revision, payload = store.load(student_id)
    if payload is None:
        engine = CognitiveEngine()
        loaded = dict(student=StudentCognitiveModel(student_id),
                      orchestrator=orchestrator_factory(engine),
                      learning_progress_tracker=LearningProgressTracker())
    else:
        loaded = restore(payload, student_id, orchestrator_factory)
    # Decode/build first so a failed load leaves the current session untouched.
    for key in list(state):
        if key in UI_KEYS | SERVICE_KEYS | {"student", "orchestrator", "learning_progress_tracker", "demo_resolved", "_concept_identity_archive"} or key.startswith(("journey_", "practice_", "advanced_", "research_", "learning_", "last_", "selected_practice_", "submit_practice_")):
            del state[key]
    # Keep the current view for a fresh profile, while its activity data starts
    # independently. A profile's explicitly saved page still takes precedence.
    if "_app_page" not in loaded and current_page is not None:
        loaded["_app_page"] = current_page
    state.update(loaded)
    state["_persistence_store"] = store
    state["_persistence_id"] = student_id
    state["_persistence_revision"] = revision
    state["_persistence_last"] = payload
    state["_persistence_identity_version"] = IDENTITY_VERSION
    state["_persistence_transaction_version"] = 1
    state.pop("_persistence_error", None)
    bind_checkpoint(state)


def bind_checkpoint(state):
    state["orchestrator"].cognitive_engine.persist_state = lambda: save_state(state)


def save_state(state):
    store = state.get("_persistence_store")
    if store is None:
        return  # Standalone pages/tests remain usable without storage.
    if state.get("_persistence_error"):
        raise RuntimeError(state["_persistence_error"])
    payload = capture(state)
    if payload == state.get("_persistence_last"):
        return
    revision = store.save(state["_persistence_id"], payload, state["_persistence_revision"])
    state["_persistence_revision"] = revision
    state["_persistence_last"] = payload


def checkpoint():
    import streamlit as st
    try:
        save_state(st.session_state)
    except Exception as exc:
        st.session_state["_persistence_error"] = str(exc)
        st.error("Progress could not be saved. Further activity is paused to protect the saved record.")
        st.caption(str(exc))
        st.stop()


def persistence_rerun():
    import streamlit as st
    checkpoint()
    st.rerun()


def checkpoint_page(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        finally:
            checkpoint()
    return wrapped


def begin_assessment(kind, request=None):
    import streamlit as st
    if st.session_state.get("_persistence_store") is None:
        return
    if st.session_state.get("_assessment_pending"):
        raise RuntimeError("An interrupted assessment needs review before another submission.")
    st.session_state["_assessment_pending"] = {"kind": kind, "request": request} if request is not None else kind
    checkpoint()


def finish_assessment():
    import streamlit as st
    st.session_state.pop("_assessment_pending", None)


def initialize_profiles(orchestrator_factory):
    import streamlit as st
    path = Path(__file__).resolve().parents[2] / "data" / "student_state" / "phss.sqlite3"
    try:
        store = SQLiteStudentStore(path)
        profiles = store.list_profiles()
        if "student" in st.session_state and "_persistence_id" not in st.session_state:
            st.warning("An existing in-memory session was found. Import it before continuing.")
            if st.button("Import current session into local storage"):
                user_id = st.session_state.student.user_id
                payload = capture(st.session_state)
                exists = any(row[0] == user_id for row in profiles)
                if exists and store.load(user_id)[1] is not None:
                    st.error("A saved profile already has this ID. The current session was left untouched.")
                    st.stop()
                if not exists:
                    store.create_profile("Imported student session", student_id=user_id)
                revision = store.save(user_id, payload, 0)
                st.session_state["_persistence_store"] = store
                st.session_state["_persistence_id"] = user_id
                st.session_state["_persistence_revision"] = revision
                st.session_state["_persistence_last"] = payload
                st.query_params["student"] = user_id
                st.rerun()
            st.stop()
        with st.sidebar:
            st.markdown("### Student profile")
            st.caption("Local profiles on this computer. Profile selection is not a login.")
            with st.form("create_student_profile"):
                name = st.text_input("New profile name", max_chars=100)
                create = st.form_submit_button("Create profile")
            if create:
                if not name.strip():
                    st.warning("Enter a profile name.")
                else:
                    save_state(st.session_state)
                    new_id = store.create_profile(name)
                    st.query_params["student"] = new_id
                    st.session_state.pop("_profile_selector", None)
                    st.rerun()
            if not profiles:
                st.info("Create a student profile to begin.")
                st.stop()
            ids = [p[0] for p in profiles]
            labels = dict(profiles)
            requested = st.query_params.get("student")
            if requested is not None and requested not in ids:
                st.error("The profile in this URL does not exist. Saved records were left untouched.")
                if st.button("Choose an existing profile"):
                    del st.query_params["student"]
                    st.rerun()
                st.stop()
            requested = requested or ids[0]
            if st.session_state.get("_profile_url") != requested:
                st.session_state["_profile_selector"] = requested
                st.session_state["_profile_url"] = requested
            selected = st.selectbox("Current student", ids, format_func=lambda key: labels[key],
                                    key="_profile_selector")
            if selected != requested:
                save_state(st.session_state)
                st.query_params["student"] = selected
                st.session_state["_profile_url"] = selected
                requested = selected
            st.query_params["student"] = requested
        if st.session_state.get("_persistence_id") != requested:
            save_state(st.session_state)
            load_profile(st.session_state, store, requested, orchestrator_factory)
        elif st.session_state.get("_persistence_identity_version") != IDENTITY_VERSION:
            # Upgrade a still-running Milestone 1 session without dropping its work.
            save_state(st.session_state)
            load_profile(st.session_state, store, requested, orchestrator_factory)
        elif st.session_state.get("_persistence_transaction_version") != 1:
            save_state(st.session_state)
            load_profile(st.session_state, store, requested, orchestrator_factory)
        archive = st.session_state.get("_concept_identity_archive", {})
        if archive.get("notes"):
            with st.expander("Saved topic identities were reconciled"):
                st.write("Original records are retained. Existing mastery estimates were not averaged or replayed.")
                for note in archive["notes"]:
                    st.write(note)
        if st.session_state.get("_persistence_error"):
            st.error("Saving is paused. Reload the saved profile before continuing.")
            st.caption(st.session_state["_persistence_error"])
            if st.button("Reload saved profile"):
                load_profile(st.session_state, store, requested, orchestrator_factory)
                st.rerun()
            st.stop()
        bind_checkpoint(st.session_state)
        if st.session_state.get("_assessment_pending"):
            st.warning("An assessment was interrupted. Its cognitive update may already be recorded. "
                       "It will not be submitted automatically.")
            pending = st.session_state["_assessment_pending"]
            if isinstance(pending, dict) and isinstance(pending.get("request"), dict):
                st.caption("Resume uses the saved answer and reuses completed evaluation stages. "
                           "Only unfinished work is retried.")
                if st.button("Resume saved assessment"):
                    from app.persistence.assessment_recovery import resume_assessment
                    try:
                        with st.spinner("Resuming your saved assessment..."):
                            resume_assessment(st.session_state)
                        checkpoint()
                        st.rerun()
                    except Exception as exc:
                        checkpoint()
                        st.error("The assessment is still saved. Unfinished work could not be completed.")
                        st.caption(str(exc))
            else:
                st.caption("This older interruption has no saved answer to resume safely.")
            st.caption("Discarding this activity keeps evidence and mastery.")
            if st.button("Keep progress and discard interrupted activity"):
                for key in list(st.session_state):
                    if key in UI_KEYS | SERVICE_KEYS and key != "learning_goal":
                        del st.session_state[key]
                checkpoint()
                st.rerun()
            st.stop()
    except Exception as exc:
        st.error("Student storage could not be loaded. Existing records were left untouched.")
        st.caption(f"{type(exc).__name__}: {exc}")
        st.stop()
