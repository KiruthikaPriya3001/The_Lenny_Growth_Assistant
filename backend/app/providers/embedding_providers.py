"""
Embedding provider abstraction.

Supports:
  - "simple": TF-IDF cosine similarity (no GPU, works everywhere)
  - "ollama": Ollama embedding API (requires running Ollama + embedding model)

The simple provider is the default for maximum portability on the local demo.
Switch to ollama embeddings when nomic-embed-text is pulled and Ollama is running.
"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from typing import Dict, List, Optional, Tuple

import httpx
import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()


class BaseEmbedder(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Return embeddings for a list of texts. None if failed."""

    @abstractmethod
    def embed_query(self, text: str) -> Optional[List[float]]:
        """Return embedding for a single query."""

    @abstractmethod
    def similarity(self, a: List[float], b: List[float]) -> float:
        """Return cosine similarity between two embeddings."""

    @abstractmethod
    def model_name(self) -> str:
        pass


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


# ─── Simple TF-IDF Embedder ──────────────────────────────────────────────────

class SimpleTFIDFEmbedder(BaseEmbedder):
    """
    Lightweight TF-IDF based similarity search.
    No GPU or ML models required.
    Not as accurate as neural embeddings, but functional for retrieval.
    """

    def __init__(self, vocab_size: int = 4096):
        self._vocab_size = vocab_size
        self._idf: Dict[int, float] = {}
        self._doc_count: int = 0
        self._fitted: bool = False

    def model_name(self) -> str:
        return "simple-tfidf"

    def _tokenize(self, text: str) -> List[str]:
        """Lowercase, remove punctuation, split on whitespace."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()
        # Basic stop-word removal
        stop = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "it", "its", "this", "that", "these", "those", "and", "or", "but",
            "not", "no", "nor", "as", "so", "yet", "both", "either", "neither",
            "each", "more", "most", "other", "some", "such", "only", "same",
            "than", "too", "very", "just", "because", "if", "while", "about",
            "against", "between", "into", "through", "during", "before", "after",
            "above", "below", "up", "down", "out", "off", "over", "under",
        }
        return [t for t in tokens if t not in stop and len(t) > 1]

    def _hash_token(self, token: str) -> int:
        return int(hashlib.md5(token.encode()).hexdigest(), 16) % self._vocab_size

    def _term_freq(self, tokens: List[str]) -> Counter:
        return Counter(self._hash_token(t) for t in tokens)

    def fit(self, texts: List[str]) -> None:
        """Compute IDF weights from a corpus."""
        self._doc_count = len(texts)
        doc_freq: Counter = Counter()
        for text in texts:
            tokens = set(self._tokenize(text))
            for t in tokens:
                doc_freq[self._hash_token(t)] += 1
        self._idf = {
            idx: math.log((self._doc_count + 1) / (freq + 1)) + 1
            for idx, freq in doc_freq.items()
        }
        self._fitted = True

    def _vectorize(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        tf = self._term_freq(tokens)
        total = max(sum(tf.values()), 1)
        vec = [0.0] * self._vocab_size
        for idx, count in tf.items():
            idf = self._idf.get(idx, math.log(self._doc_count + 1) + 1)
            vec[idx] = (count / total) * idf
        return vec

    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        return [self._vectorize(t) for t in texts]

    def embed_query(self, text: str) -> Optional[List[float]]:
        return self._vectorize(text)

    def similarity(self, a: List[float], b: List[float]) -> float:
        return cosine_similarity(a, b)


# ─── Ollama Embedder ─────────────────────────────────────────────────────────

class OllamaEmbedder(BaseEmbedder):
    """Uses Ollama's /api/embed endpoint for neural embeddings."""

    def __init__(self, base_url: str, model: str, timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def model_name(self) -> str:
        return self._model

    def _embed_one(self, text: str) -> Optional[List[float]]:
        try:
            resp = httpx.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": text},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            # Ollama returns {"embeddings": [[...]] }
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
            return None
        except Exception as exc:
            logger.warning("Ollama embed failed: %s", exc)
            return None

    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> Optional[List[float]]:
        return self._embed_one(text)

    def similarity(self, a: List[float], b: List[float]) -> float:
        return cosine_similarity(a, b)


# ─── Factory ─────────────────────────────────────────────────────────────────

_embedder_instance: Optional[BaseEmbedder] = None


def get_embedder() -> BaseEmbedder:
    global _embedder_instance
    if _embedder_instance is None:
        s = _settings
        if s.embedding_provider == "ollama":
            _embedder_instance = OllamaEmbedder(
                base_url=s.ollama_base_url,
                model=s.ollama_embedding_model,
            )
        else:
            _embedder_instance = SimpleTFIDFEmbedder()
    return _embedder_instance
