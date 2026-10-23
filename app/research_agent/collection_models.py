"""Explicit resource bounds for locally uploaded papers (no provider calls)."""
from dataclasses import asdict, dataclass
import os

MISSING = 'Not specified in the supplied paper.'
FIELDS = ('overview', 'research_problem', 'objectives', 'methodology', 'dataset',
          'experimental_setup', 'models_algorithms', 'evaluation_metrics', 'findings', 'limitations')


@dataclass(frozen=True)
class CollectionLimits:
    max_file_bytes: int = 20 * 1024 * 1024
    max_documents: int = 100
    max_collection_bytes: int = 200 * 1024 * 1024
    max_pages: int = 300
    max_text_chars: int = 1_000_000
    chunk_chars: int = 10_000
    min_text_chars: int = 80
    extraction_batch: int = 3
    analysis_batch: int = 6
    extraction_timeout: int = 45
    provider_timeout: int = 60
    max_worker_memory_mb: int = 512

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in asdict(self).values()):
            raise ValueError('PDF collection limits must be positive integers.')
        if self.chunk_chars > self.max_text_chars:
            raise ValueError('chunk_chars cannot exceed max_text_chars.')

    @classmethod
    def from_environment(cls):
        defaults = asdict(cls())
        return cls(**{name: int(os.environ.get('PHSS_PDF_' + name.upper(), value))
                      for name, value in defaults.items()})
