"""
Configuration for the multilingual summarization module.
All hyperparameters are tuned on the CHULN radiology corpus (9,921 records).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# FHIR StructureDefinition URL for the summarization extension
FHIR_SUMMARY_EXT_URL = (
    "http://chuln.pt/fhir/StructureDefinition/radiology-summary"
)

# Supported abstractive models: key → HuggingFace model ID or local path
ABSTRACTIVE_MODELS: Dict[str, str] = {
    "ptt5-base": "unicamp-dl/ptt5-base-portuguese-vocab",
    "mt5-small": "google/mt5-small",
    "mt5-xlsum": "csebuetnlp/mT5_multilingual_XLSum",
}

# Translation model for PT→EN (MarianMT, CPU-friendly ~330 MB)
TRANSLATION_MODEL_PT_EN = "Helsinki-NLP/opus-mt-ROMANCE-en"

# BERTScore evaluation models
BERTSCORE_MODEL_PT = "neuralmind/bert-base-portuguese-cased"
BERTSCORE_MODEL_MULTILINGUAL = "bert-base-multilingual-cased"

# NLI model for faithfulness scoring
NLI_MODEL = "cross-encoder/nli-deberta-v3-small"

# European Portuguese stopwords (pt-PT)
PT_STOPWORDS: List[str] = [
    "a", "à", "ao", "aos", "as", "o", "os",
    "de", "do", "da", "dos", "das",
    "e", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem",
    "um", "uma", "uns", "umas",
    "que", "se", "não", "nao",
    "é", "são", "ser", "foi", "era", "sendo",
    "como", "mais", "menos", "muito", "pouco",
    "há", "ha", "já", "ja", "também", "tambem",
    "ou", "mas", "porque", "quando", "onde", "qual", "quais",
    "todo", "toda", "todos", "todas",
    "lhe", "lhes", "sua", "seu", "suas", "seus",
    "só", "so",
]

# Clinical keyword list for TF-IDF boost (normalized, no diacritics)
CLINICAL_KEYWORDS_PT: List[str] = [
    "conclusao", "conclusoes", "impressao", "achados",
    "resultado", "sumario", "diagnostico", "avaliacao",
    "interpretacao", "sugere", "compativel",
]


@dataclass
class SummarizationConfig:
    """Runtime configuration for the SummarizationAgent and evaluation scripts."""

    # --- Extractive (TF-IDF) ---
    n_sentences: int = 2
    keyword_boost: float = 1.15
    similarity_threshold: float = 0.72
    short_penalty: float = 0.45
    long_penalty: float = 0.65
    min_sent_len: int = 25
    max_sent_len: int = 230

    # --- Abstractive ---
    # Use a key from ABSTRACTIVE_MODELS or a full HuggingFace / local path.
    # For fine-tuned models, pass the local directory as abstractive_model_key.
    abstractive_model_key: str = "ptt5-base"
    abstractive_max_new_tokens: int = 128
    abstractive_num_beams: int = 4
    abstractive_no_repeat_ngram: int = 3
    abstractive_min_length: int = 20
    # Max chars fed to the abstractive model (truncated before tokenisation)
    abstractive_max_input_chars: int = 2000

    # --- Translation ---
    run_translation: bool = True
    translation_max_length: int = 512

    # --- Feature flags ---
    # Set to True only when a fine-tuned (or validated) abstractive model is available.
    run_abstractive: bool = False

    # --- Hardware ---
    # "auto" → uses CUDA if available, else CPU; "cpu" or "cuda" to force.
    device: str = "auto"

    # --- Filtering ---
    min_source_chars: int = 100

    @property
    def abstractive_model_name(self) -> str:
        """Resolve model key to HuggingFace ID or local path."""
        return ABSTRACTIVE_MODELS.get(
            self.abstractive_model_key, self.abstractive_model_key
        )
