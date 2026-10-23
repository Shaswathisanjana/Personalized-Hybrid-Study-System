"""Synthetic PDFs generated locally for tests; not academic publications."""
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def make_pdf(index=0, *, pages=None, metadata=True, encrypted=False):
    writer = PdfWriter()
    if metadata:
        writer.add_metadata({'/Title': f'Synthetic PDF fixture {index}', '/Author': 'Fixture Author'})
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    reference = writer._add_object(font)
    if pages is None:
        pages = [f'Synthetic document {index}. This controlled fixture investigates retrieval evaluation. '
                 'The objectives are to compare bounded retrieval methods using recorded examples.',
                 'The methodology uses a controlled comparison. The dataset contains synthetic records. '
                 'Evaluation uses exact match accuracy. The findings report an improvement on the fixture. '
                 'The study is limited to synthetic examples.']
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): reference})})
        stream = DecodedStreamObject()
        escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream.set_data(('BT /F1 10 Tf 20 700 Td (' + escaped + ') Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    if encrypted:
        writer.encrypt('fixture-password')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class ExtractiveAnalyzer:
    def __init__(self):
        self.calls = []
        self.fail_chunk = None

    def analyze(self, chunk):
        self.calls.append(chunk['text'])
        if self.fail_chunk and self.fail_chunk in chunk['text']:
            raise RuntimeError('Injected offline provider failure')
        candidates = dict(methodology='The methodology uses a controlled comparison.',
                          dataset='The dataset contains synthetic records.',
                          evaluation_metrics='Evaluation uses exact match accuracy.',
                          findings='The findings report an improvement on the fixture.',
                          limitations='The study is limited to synthetic examples.')
        return {key: quote for key, quote in candidates.items() if quote in chunk['text']}
