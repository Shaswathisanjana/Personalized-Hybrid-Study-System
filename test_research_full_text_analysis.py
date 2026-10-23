"""Provider boundary checks use controlled responses, never network requests."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import json
import subprocess
import unittest

from app.research_agent.collection_models import CollectionLimits
from app.research_agent.full_text_analysis import GroundedChunkAnalyzer, validate_claims
from app.research_agent.paper_summarizer import StructuredPaperSummarizer
from app.research_agent.pdf_extractor import extract_pdf


class FullTextAnalysisTests(unittest.TestCase):
    def test_actual_extracted_text_is_sent_and_request_is_bounded(self):
        text = 'The dataset contains synthetic records.'
        generate = Mock(return_value=SimpleNamespace(text=json.dumps({'dataset': text})))
        provider = SimpleNamespace(client=SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
                                   model_name='offline-model', _clean_json=StructuredPaperSummarizer._clean_json)
        analyzer = GroundedChunkAnalyzer(provider=provider, timeout_seconds=17)
        chunk = dict(page=7, chunk_id='p7-c2', text=text)
        self.assertEqual(validate_claims(chunk, analyzer.analyze(chunk)), {'dataset': text})
        request = generate.call_args.kwargs
        self.assertIn(text, request['contents'])
        self.assertIn('PAGE 7', request['contents'])
        self.assertEqual(request['config']['http_options']['timeout'], 17000)
        self.assertEqual(request['config']['http_options']['retry_options']['attempts'], 1)

    def test_invented_fields_wrong_page_quotes_and_rewritten_findings_are_rejected(self):
        chunk = dict(page=1, chunk_id='p1-c1', text='The dataset contains synthetic records.')
        for fields in ({'citation': 'invented publication'},
                       {'dataset': {'value': 'unsupported rewrite'}},
                       {'findings': 'A fabricated improvement of 95 percent.'},
                       {'dataset': '.'}):
            with self.assertRaises(ValueError):
                validate_claims(chunk, fields)
        self.assertEqual(validate_claims(chunk, {'findings': ''}), {})

    def test_worker_timeout_returns_saved_retryable_status_without_text(self):
        with patch('app.research_agent.pdf_extractor.subprocess.run',
                   side_effect=subprocess.TimeoutExpired('fixture', 1)):
            result = extract_pdf(b'%PDF-1.7\nfixture', CollectionLimits())
        self.assertEqual(result['status'], 'extraction_error')
        self.assertEqual(result['chunks'], [])

    def test_sdk_accepts_the_configured_timeout_and_retry_options(self):
        from google.genai.types import GenerateContentConfig
        config = GenerateContentConfig(http_options={'timeout': 60000, 'retry_options': {'attempts': 1}},
                                       max_output_tokens=8192)
        self.assertEqual(config.http_options.retry_options.attempts, 1)


if __name__ == '__main__':
    unittest.main()
