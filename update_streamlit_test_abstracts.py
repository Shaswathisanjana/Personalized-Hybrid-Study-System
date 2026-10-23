from pathlib import Path

files = [
    Path("test_research_streamlit_app.py"),
    Path("test_research_streamlit_renderer.py"),
]

old_cnn = '''            "CNN classification. "
            "1000 labelled images. "
            "Evaluation used data from only one institution."
'''

new_cnn = '''            "This synthetic study investigates automated "
            "medical image classification using deep learning. "
            "CNN classification. "
            "The experimental dataset contains "
            "1000 labelled images. "
            "The study examines how image-based features "
            "can support diagnostic classification and "
            "compares predictions against reference labels. "
            "Evaluation used data from only one institution. "
            "This restricted evaluation setting limits "
            "the conclusions that can be drawn about "
            "generalization to other institutions."
'''

old_transformer = '''            "Transformer classification. "
            "2000 labelled images."
'''

new_transformer = '''            "This synthetic research paper investigates "
            "deep learning approaches for classifying "
            "medical images into diagnostic categories. "
            "Transformer classification. "
            "The experimental dataset contains "
            "2000 labelled images. "
            "The study explores attention-based image "
            "representations and examines their usefulness "
            "for automated classification. "
            "Predictions are compared against labelled "
            "reference examples to study the proposed "
            "approach in a controlled experimental setting."
'''

updates = []

for path in files:
    source = path.read_text(encoding="utf-8-sig")

    # Match either indentation level without changing Python structure.
    cnn_count = source.count(old_cnn)
    transformer_count = source.count(old_transformer)

    if path.name == "test_research_streamlit_renderer.py":
        expected = 0

        old_cnn_indented = old_cnn.replace(
            "            ", "                "
        )
        new_cnn_indented = new_cnn.replace(
            "            ", "                "
        )
        old_transformer_indented = old_transformer.replace(
            "            ", "                "
        )
        new_transformer_indented = new_transformer.replace(
            "            ", "                "
        )

        if source.count(old_cnn_indented) != 1:
            raise RuntimeError("Renderer CNN fixture mismatch.")

        if source.count(old_transformer_indented) != 1:
            raise RuntimeError("Renderer Transformer fixture mismatch.")

        updated = source.replace(
            old_cnn_indented, new_cnn_indented, 1
        ).replace(
            old_transformer_indented,
            new_transformer_indented,
            1,
        )

    else:
        if cnn_count != 1 or transformer_count != 1:
            raise RuntimeError(
                f"Fixture mismatch in {path.name}."
            )

        updated = source.replace(
            old_cnn, new_cnn, 1
        ).replace(
            old_transformer, new_transformer, 1
        )

    compile(updated, str(path), "exec")
    updates.append((path, source, updated))

# Write only after both files have passed validation.
for path, source, updated in updates:
    backup = path.with_suffix(".before_quality_filter.bak")
    backup.write_text(source, encoding="utf-8")
    path.write_text(updated, encoding="utf-8")
    print("SUCCESS: Updated", path.name)

print("SUCCESS: Both test fixtures passed syntax verification.")
