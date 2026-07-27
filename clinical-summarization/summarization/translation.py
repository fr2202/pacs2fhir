"""
Portuguese → English translation via MarianMT (Helsinki-NLP/opus-mt-tc-big-pt-en).

Model size: ~330 MB. Runs on CPU at acceptable speed for single summaries.
Designed for translating short clinical summaries (< 512 tokens), not full reports.
"""
from __future__ import annotations

import logging
from typing import Optional

from summarization.config import TRANSLATION_MODEL_PT_EN

logger = logging.getLogger(__name__)

# Maximum characters fed to the translator before truncation.
# MarianMT tokeniser limit is 512 subword tokens; ~1500 chars is a safe proxy.
_MAX_INPUT_CHARS = 1500


class PT2ENTranslator:
    """
    Lazy-loading PT→EN translator backed by a MarianMT pipeline.

    The model is downloaded and loaded only on the first call to `translate()`.
    """

    def __init__(
        self,
        model_name: str = TRANSLATION_MODEL_PT_EN,
        device: str = "auto",
    ) -> None:
        self._model_name = model_name
        self._device_arg = device
        self._pipe = None

    def _resolve_device(self) -> int:
        if self._device_arg == "cpu":
            return -1
        if self._device_arg == "cuda":
            return 0
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
                "transformers is required for translation. "
                "pip install transformers sentencepiece"
            ) from exc

        device = self._resolve_device()
        logger.info(
            "Loading translation model '%s' on %s",
            self._model_name,
            "CUDA" if device >= 0 else "CPU",
        )
        self._pipe = hf_pipeline(
            "translation",
            model=self._model_name,
            device=device,
        )
        logger.info("Translation model loaded.")

    def translate(
        self,
        text: str,
        max_length: int = 512,
    ) -> str:
        """
        Translate *text* from Portuguese to English.

        Returns empty string on error or empty input.
        """
        if not text or not text.strip():
            return ""
        self._load()
        try:
            out = self._pipe(
                text[:_MAX_INPUT_CHARS],
                max_length=min(max_length, 512),  # MarianMT hard cap
                truncation=True,
            )
            if out and isinstance(out, list):
                return out[0].get("translation_text", "")
        except Exception as exc:
            logger.warning("Translation failed: %s", exc)
        return ""
