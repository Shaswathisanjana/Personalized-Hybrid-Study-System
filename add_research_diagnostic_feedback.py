from pathlib import Path

path = Path("app/research_agent/streamlit_diagnostic.py")
source = path.read_text(encoding="utf-8-sig")

old = """    if not has_conflict:
        st.success(
            "No unresolved cross-agent cognitive conflict "
            "is currently detected for this concept."
        )
        return
"""

new = """    # Display completed diagnostic feedback before checking whether
    # the conflict still exists. A successful diagnostic may have
    # already removed the conflict from CACM.
    completed = st.session_state.get(
        "research_diagnostic_outcome"
    )
    completed_concept = st.session_state.get(
        "research_diagnostic_concept"
    )

    if completed is not None and completed_concept == concept_name:
        diagnostic = completed.diagnostic_outcome
        evaluation = diagnostic.evaluation

        st.success("Diagnostic assessment completed.")

        st.write(
            "**Diagnostic performance:**",
            f"{evaluation.performance:.2f}",
        )
        st.write(
            "**Evaluation feedback:**",
            evaluation.feedback,
        )

        if diagnostic.conflict_resolved:
            st.success(
                "CACM resolved the cross-agent cognitive conflict."
            )
        elif diagnostic.has_active_conflict:
            st.warning(
                "The conflict remains unresolved. Further diagnostic "
                "intervention may be required."
            )
        else:
            st.info(
                "No active conflict remains after diagnostic processing."
            )

        concept = student.get_concept(concept_name)

        st.markdown("#### Updated CACM State")
        st.write("**Mastery:**", f"{concept.mastery:.3f}")
        st.write("**Confidence:**", f"{concept.confidence:.3f}")
        st.write("**Attempts:**", concept.attempts)

        st.markdown("#### Learning Agent Replanning")
        st.write(
            "**Next recommended action:**",
            completed.next_action.action_type,
        )

        # Keep the completed result visible; do not offer the
        # same diagnostic session for another submission.
        return

    if not has_conflict:
        st.success(
            "No unresolved cross-agent cognitive conflict "
            "is currently detected for this concept."
        )
        return
"""

count = source.count(old)

if count != 1:
    raise RuntimeError(
        f"Expected exactly one conflict display block; found {count}. "
        "No changes were written."
    )

source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = Path(
    "app/research_agent/streamlit_diagnostic_before_feedback.bak"
)

backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Diagnostic feedback display added.")
print("PASS: Completed diagnostic is not offered for resubmission.")
print("PASS: Original interface backed up.")
