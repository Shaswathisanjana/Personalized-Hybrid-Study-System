from pathlib import Path

source = Path("review_ui.py").read_text(
    encoding="utf-8-sig"
)

dashboard = 'with st.expander("My Learning Progress"'
browser = 'with st.expander("Browse Learning Topics"'

assert source.count(dashboard) == 1, (
    "Dashboard must appear exactly once."
)

assert source.index(dashboard) < source.index(browser), (
    "Dashboard must appear before the topic browser."
)

assert "progress_tracker.snapshot(" in source, (
    "CACM snapshot integration is missing."
)

assert "snapshot.mastery is None" in source, (
    "Missing-estimate handling is absent."
)

print("PASS: Dashboard installed before the topic browser.")
print("PASS: CACM snapshot and missing-estimate handling present.")
print("STEP 75 VERIFIED")
