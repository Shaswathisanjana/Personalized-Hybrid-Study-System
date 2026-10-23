from pathlib import Path

path = Path("test_research_diagnostic_streamlit_ui.py")
source = path.read_text(encoding="utf-8-sig")

old = """    app.text_area(
        key="research_diagnostic_answer_form-Your diagnostic answer"
    ).input("The stopping condition.").run()

    app.button(
        key="research_diagnostic_answer_form-Submit Diagnostic Answer"
    ).click().run()
"""

new = """    # Locate widgets using their actual displayed labels rather
    # than assuming Streamlit's internally generated form keys.
    answer_fields = [
        item for item in app.text_area
        if item.label == "Your diagnostic answer"
    ]

    assert len(answer_fields) == 1, (
        "Expected exactly one diagnostic answer field."
    )

    answer_fields[0].input("The stopping condition.").run()

    submit_buttons = [
        item for item in app.button
        if item.label == "Submit Diagnostic Answer"
    ]

    assert len(submit_buttons) == 1, (
        "Expected exactly one diagnostic submit button."
    )

    submit_buttons[0].click().run()
"""

count = source.count(old)

if count != 1:
    raise RuntimeError(
        f"Expected one widget interaction block; found {count}. "
        "No changes were written."
    )

source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = Path(
    "test_research_diagnostic_streamlit_ui_before_widget_fix.bak"
)

backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Diagnostic answer field now located by label.")
print("PASS: Submit button now located by label.")
print("PASS: Previous test backed up.")
print("PASS: Corrected test syntax validated.")
