"""Lightweight lexical vectors for research ranking and clustering.

No pretrained model, weights, HF token, or model download is required.
The historical BGEEmbedder class name remains for internal compatibility.
"""
from sklearn.feature_extraction.text import HashingVectorizer

class BGEEmbedder:
    def __init__(self):
        self.vectorizer = HashingVectorizer(n_features=2048, alternate_sign=False,
            norm="l2", stop_words="english", ngram_range=(1, 2))

    def embed_documents(self, texts):
        return self.vectorizer.transform(list(texts)).toarray()

    def embed_query(self, text):
        return self.embed_documents([text])[0]

    def encode(self, texts, **kwargs):
        """Compatibility with retrieval callers that previously used a model."""
        if isinstance(texts, str):
            return self.embed_query(texts)
        return self.embed_documents(texts)


def get_embedding_model():
    """Return a lightweight transform; no model weights are loaded."""
    return BGEEmbedder()
