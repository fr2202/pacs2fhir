"""
Extractive summarization via TF-IDF scoring with keyword boost and Jaccard deduplication.

Ported and hardened from sumarizacion/pipeline/summarization.py.
Tuned hyperparameters yield ROUGE-1 F=0.390 on CHULN radiology test set (n=169).
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

from summarization.config import (
    SummarizationConfig,
    PT_STOPWORDS,
    CLINICAL_KEYWORDS_PT,
)

_ABBREV_WITH_DOT = [
    "dr.", "dra.", "sr.", "sra.", "srta.", "prof.", "profa.",
    "etc.", "p.ex.", "ex.", "fig.", "no.", "nos.", "vs.", "v.s.",
]


def _normalize(text: str) -> str:
    """Lowercase and strip combining diacritics for comparison."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _split_sentences(text: str) -> List[str]:
    """Sentence splitter for European Portuguese clinical text."""
    if not isinstance(text, str) or not text.strip():
        return []
    s = re.sub(r"\s+", " ", text.strip())
    # Protect numeric decimals and known abbreviations before splitting on '.'
    s = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", s)
    for abbr in _ABBREV_WITH_DOT:
        safe = abbr.replace(".", "<DOT>")
        s = re.sub(rf"\b{re.escape(abbr)}", safe, s, flags=re.IGNORECASE)
    parts = re.split(r"(?<=[.!?])\s+", s)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]


def _jaccard_similarity(a: str, b: str) -> float:
    """Token-level Jaccard similarity on normalised strings."""
    a_tok = set(re.findall(r"\w+", _normalize(a)))
    b_tok = set(re.findall(r"\w+", _normalize(b)))
    if not a_tok or not b_tok:
        return 0.0
    return len(a_tok & b_tok) / max(len(a_tok), len(b_tok))


class ExtractiveSummarizer:
    """TF-IDF based extractive summarizer for Portuguese radiology reports."""

    def __init__(self, config: Optional[SummarizationConfig] = None) -> None:
        self._cfg = config or SummarizationConfig()

    def summarize(self, text: str) -> List[str]:
        """Return up to n_sentences representative sentences from *text*."""
        try:
            import numpy as np
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError as exc:
            raise RuntimeError(
                "numpy and scikit-learn are required for extractive summarization. "
                "pip install numpy scikit-learn"
            ) from exc

        sents = _split_sentences(text)
        if not sents:
            return []
        n = self._cfg.n_sentences
        if len(sents) <= n:
            return sents

        vec = TfidfVectorizer(stop_words=PT_STOPWORDS)
        tfidf = vec.fit_transform(sents)
        scores: np.ndarray = np.asarray(tfidf.sum(axis=1)).ravel()

        key_set = {_normalize(k) for k in CLINICAL_KEYWORDS_PT}
        for i, sent in enumerate(sents):
            length = len(sent)
            if length < self._cfg.min_sent_len:
                scores[i] *= self._cfg.short_penalty
            elif length > self._cfg.max_sent_len:
                scores[i] *= self._cfg.long_penalty
            if any(k in _normalize(sent) for k in key_set):
                scores[i] *= self._cfg.keyword_boost

        ranked = list(scores.argsort())[::-1]
        picked: List[int] = []
        for idx in ranked:
            if len(picked) >= n:
                break
            if all(
                _jaccard_similarity(sents[idx], sents[j]) < self._cfg.similarity_threshold
                for j in picked
            ):
                picked.append(idx)

        picked.sort()
        return [sents[i] for i in picked]

    def summarize_as_text(self, text: str) -> str:
        """Convenience wrapper returning a single joined string."""
        return " ".join(self.summarize(text))
