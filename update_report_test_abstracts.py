from pathlib import Path

path = Path("test_research_report_exporter.py")
source = path.read_text(encoding="utf-8-sig")

old_cnn = '''                "CNN classification. "
                "1000 labelled images. "
                "Evaluation used data from only one institution."
'''

new_cnn = '''                "This synthetic study investigates automated "
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

old_transformer = '''                "Transformer classification. "
                "2000 labelled images."
'''

new_transformer = '''                "This synthetic research paper investigates "
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

if source.count(old_cnn) != 1:
    raise RuntimeError("CNN fixture not found exactly once.")

if source.count(old_transformer) != 1:
    raise RuntimeError("Transformer fixture not found exactly once.")

updated = source.replace(old_cnn, new_cnn, 1)
updated = updated.replace(old_transformer, new_transformer, 1)

compile(updated, str(path), "exec")

backup = Path(
    "test_research_report_exporter_before_quality_filter.py.bak"
)

backup.write_text(source, encoding="utf-8")
path.write_text(updated, encoding="utf-8")

print("SUCCESS: Report test fixtures updated.")
