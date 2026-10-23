from pathlib import Path
import shutil
import subprocess
import sys

path = Path("review_ui.py")
original = path.read_text(encoding="utf-8-sig")

start_marker = "def display_resource_recommendations(recommendation):"
end_marker = "\ndef "

start = original.find(start_marker)

if start == -1:
    raise RuntimeError(
        "Resource display function not found. No changes made."
    )

end = original.find(end_marker, start + len(start_marker))

if end == -1:
    raise RuntimeError(
        "Could not identify the end of the function. No changes made."
    )

if original.count(start_marker) != 1:
    raise RuntimeError(
        "Expected exactly one resource display function."
    )

import_line = (
    "from app.learning_agent.resources.format_filter import (\n"
    "    RESOURCE_FORMATS,\n"
    "    filter_ranked_resources,\n"
    ")\n"
)

if "from app.learning_agent.resources.format_filter import" in original:
    raise RuntimeError(
        "Format filter already imported. Inspect before modifying."
    )

backup = Path("review_ui.py.step45.bak")
shutil.copy2(path, backup)

new_function = '''def display_resource_recommendations(recommendation):
    """
    Display CACM-personalized learning resources.

    Students can filter by resource format.
    Each format initially displays up to three resources.
    View More reveals the remaining matching resources.

    Filtering does not change the original ranking scores.
    """

    if recommendation is None:
        return

    resources = getattr(recommendation, "resources", [])

    if not resources:
        st.info("No suitable external learning resources were returned.")
        return

    st.markdown("### Recommended Learning Resources")

    target_level = getattr(recommendation, "student_level", None)

    if target_level:
        st.caption(
            "CACM target resource level: "
            f"{clean_label(target_level)}"
        )

    concept_name = getattr(
        recommendation,
        "concept_name",
        "general",
    )

    format_key = (
        "learning_resource_format_"
        + str(concept_name)
    )

    selected_format = st.selectbox(
        "Choose resource format",
        options=RESOURCE_FORMATS,
        key=format_key,
    )

    filtered_resources = filter_ranked_resources(
        ranked_resources=resources,
        selected_format=selected_format,
    )

    display_key = (
        "learning_resources_expanded_"
        + str(concept_name)
        + "_"
        + selected_format.replace(" ", "_")
    )

    if display_key not in st.session_state:
        st.session_state[display_key] = False

    expanded = st.session_state[display_key]

    if not filtered_resources:
        st.info(
            f"No suitable {selected_format.lower()} "
            "were returned for this topic."
        )
        return

    visible_count = (
        len(filtered_resources)
        if expanded
        else min(3, len(filtered_resources))
    )

    st.caption(
        f"Showing {visible_count} of "
        f"{len(filtered_resources)} resources "
        f"in {selected_format}."
    )

    for index, ranked_resource in enumerate(
        filtered_resources[:visible_count],
        start=1,
    ):
        resource = getattr(
            ranked_resource,
            "resource",
            ranked_resource,
        )

        title = getattr(resource, "title", f"Resource {index}")
        url = getattr(resource, "url", "")
        source = getattr(resource, "source", "")
        difficulty = getattr(resource, "difficulty", "unknown")
        description = getattr(resource, "description", "")
        reason = getattr(ranked_resource, "reason", "")

        with st.container(border=True):
            st.markdown(f"#### {index}. {title}")

            col1, col2 = st.columns(2)

            with col1:
                st.write(
                    "**Estimated difficulty:**",
                    clean_label(difficulty),
                )

            with col2:
                if source:
                    st.write("**Source:**", source)

            if description:
                st.write(description)

            if reason:
                st.caption(f"Why recommended: {reason}")

            if url:
                st.link_button("Open Resource", url)

    if len(filtered_resources) > 3:
        if expanded:
            if st.button(
                "Show Less",
                key=display_key + "_collapse",
            ):
                st.session_state[display_key] = False
                st.rerun()
        else:
            remaining = len(filtered_resources) - 3

            if st.button(
                f"View More Resources ({remaining} more)",
                key=display_key + "_expand",
            ):
                st.session_state[display_key] = True
                st.rerun()
'''

updated = (
    original[:start]
    + new_function
    + original[end:]
)

# Insert the import before the resource display function.
# This is valid Python and avoids modifying unrelated imports.
new_start = updated.find(start_marker)

updated = (
    updated[:new_start]
    + import_line
    + "\n"
    + updated[new_start:]
)

path.write_text(updated, encoding="utf-8")

print("\n========== SYNTAX CHECK ==========")

result = subprocess.run(
    [sys.executable, "-m", "py_compile", str(path)],
    check=False,
)

if result.returncode != 0:
    shutil.copy2(backup, path)
    raise RuntimeError(
        "Syntax check failed. Original UI restored."
    )

print("Syntax check passed.")

print("\n========== INTEGRATION CHECK ==========")

assert "Choose resource format" in updated
assert "filter_ranked_resources(" in updated
assert "View More Resources" in updated
assert "Show Less" in updated

print("Format selector: present")
print("Filtering integration: present")
print("View More: present")
print("Show Less: present")

print("\nSTEP 45 UI INTEGRATION VERIFIED")
