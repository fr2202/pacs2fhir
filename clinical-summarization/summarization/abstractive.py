"""
Abstractive summarization with lazy-loaded HuggingFace seq2seq models.

Supported backends (configure via SummarizationConfig.abstractive_model_key):
  "ptt5-base"  → unicamp-dl/ptt5-base-portuguese-vocab  (GPU preferred, ~490 MB)
  "mt5-small"  → google/mt5-small                        (CPU/GPU, ~300 MB)
  "mt5-xlsum"  → csebuetnlp/mT5_multilingual_XLSum       (GPU, ~1.2 GB, news-only baseline)
  <local path> → fine-tuned checkpoint (recommended for production)

NOTE: Zero-shot performance of ptt5-base and mt5-small is poor without fine-tuning.
They are included for the ablation study (Table 1 in thesis). Use a fine-tuned checkpoint
or the extractive fallback for any production FHIR bundle enrichment.
mT5-XLSum is documented to hallucinate on medical text — include it only as a negative baseline.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from summarization.config import SummarizationConfig, ABSTRACTIVE_MODELS

logger = logging.getLogger(__name__)

_WHITESPACE_HANDLER = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE_HANDLER.sub(" ", text.replace("\n", " ")).strip()


def _build_input(model_name: str, text: str) -> str:
    """Apply model-specific prompt prefix."""
    clean = _normalize_whitespace(text)
    if "xlsum" in model_name.lower():
        # XLSum models require a language token as the first token
        return f"<pt> {clean}"
    # T5 and mT5 without XLSum use a task prefix
    return f"summarize: {clean}"


class AbstractiveSummarizer:
    """
    Seq2seq abstractive summarizer with lazy model loading.

    Models are not downloaded until the first call to `summarize()`.
    This allows importing the class without GPU or network access.
    """

    def __init__(
        self,
        model_name: str,
        device: str = "auto",
    ) -> None:
        # Accept a short key ("ptt5-base") or a full HF/local path
        self._model_name = ABSTRACTIVE_MODELS.get(model_name, model_name)
        self._device_arg = device
        self._pipe = None

    def _resolve_device(self) -> int:
        """Return device int for transformers pipeline (-1=CPU, 0=CUDA:0)."""
        if self._device_arg == "cpu":
            return -1
        if self._device_arg == "cuda":
            return 0
        # "auto": detect at runtime
        try:
            import torch
            return 0 if torch.cuda.is_available() else -1
        except ImportError:
            return -1

    def _load(self) -> None:
        if self._pipe is not None:
            return
        try:
            from transformers import pipeline as hf_pipeline
        except ImportError as exc:
            raise RuntimeError(
                "transformers is required for abstractive summarization. "
                "pip install transformers sentencepiece"
            ) from exc

        device = self._resolve_device()
        device_label = f"CUDA:{device}" if device >= 0 else "CPU"
        logger.info(
            "Loading abstractive model '%s' on %s", self._model_name, device_label
        )
        try:
            self._pipe = hf_pipeline(
                "summarization",
                model=self._model_name,
                device=device,
            )
        except Exception:
            # Some models expose text2text-generation instead of summarization
            self._pipe = hf_pipeline(
                "text2text-generation",
                model=self._model_name,
                device=device,
            )
        logger.info("Model '%s' loaded.", self._model_name)

    def summarize(
        self,
        text: str,
        *,
        config: Optional[SummarizationConfig] = None,
    ) -> str:
        """
        Summarise *text* and return a plain string.

        Returns an empty string on error to avoid crashing the FHIR pipeline.
        """
        if not text or not text.strip():
            return ""

        cfg = config or SummarizationConfig()
        truncated = text[: cfg.abstractive_max_input_chars]
        model_input = _build_input(self._model_name, truncated)

        self._load()
        try:
            out = self._pipe(
                model_input,
                max_new_tokens=cfg.abstractive_max_new_tokens,
                min_length=cfg.abstractive_min_length,
                num_beams=cfg.abstractive_num_beams,
                no_repeat_ngram_size=cfg.abstractive_no_repeat_ngram,
                do_sample=False,
            )
            if not out:
                return ""
            first = out[0] if isinstance(out, list) else out
            if isinstance(first, dict):
                return first.get("summary_text") or first.get("generated_text") or ""
            return str(first)
        except Exception as exc:
            logger.warning(
                "Abstractive summarization failed for model '%s': %s",
                self._model_name,
                exc,
            )
            return ""
