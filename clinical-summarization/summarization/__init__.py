"""
Multilingual Summarization Module for CHULN Radiology Reports.

Provides extractive, abstractive (multi-model), and PT→EN translation
pipelines integrated with FHIR R4 DiagnosticReport extensions.
"""
from summarization.config import SummarizationConfig
from summarization.extractive import ExtractiveSummarizer
from summarization.abstractive import AbstractiveSummarizer
from summarization.translation import PT2ENTranslator
from summarization.evaluation import MultilingualEvaluator, SummaryMetrics

__all__ = [
    "SummarizationConfig",
    "ExtractiveSummarizer",
    "AbstractiveSummarizer",
    "PT2ENTranslator",
    "MultilingualEvaluator",
    "SummaryMetrics",
]
