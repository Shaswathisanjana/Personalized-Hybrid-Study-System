from streamlit.testing.v1 import AppTest


def main():

    print("STEP 1: Running excluded-paper Streamlit test...")

    app = AppTest.from_file(
        "test_research_streamlit_exclusion_app.py",
        default_timeout=30,
    )

    app.run()

    if len(app.exception):
        for error in app.exception:
            print(error.message)
        raise AssertionError("Streamlit raised an exception.")

    paper_expanders = [
        item for item in app.get("expander")
        if item.label.startswith("Paper ")
    ]

    exclusion_expanders = [
        item for item in app.get("expander")
        if "Excluded Papers and Reasons" in item.label
    ]

    assert len(paper_expanders) == 1, (
        f"Expected 1 accepted paper section, "
        f"found {len(paper_expanders)}."
    )

    assert len(exclusion_expanders) == 1, (
        "Expected an Excluded Papers and Reasons section."
    )

    print("Accepted paper sections:", len(paper_expanders))
    print("Exclusion sections:", len(exclusion_expanders))

    print(
        "\nTEST PASSED: Streamlit displays accepted "
        "papers and the exclusion section correctly."
    )


if __name__ == "__main__":
    main()
