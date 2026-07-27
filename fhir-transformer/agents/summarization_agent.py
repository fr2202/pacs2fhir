"""
Summarization Agent — FHIR R4 integration layer.

Orchestrates extractive summarization, optional abstractive summarization,
and optional PT→EN translation, then packages the results as a FHIR
DiagnosticReport extension conforming to:

    http://chuln.pt/fhir/StructureDefinition/radiology-summary

The extension is designed to be inserted into an existing DiagnosticReport
resource without modifying any required fields.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from summarization.config import (
    FHIR_SUMMARY_EXT_URL,
    SummarizationConfig,
    TRANSLATION_MODEL_PT_EN,
)
from summarization.extractive import ExtractiveSummarizer
from summarization.abstractive import AbstractiveSummarizer
from summarization.translation import PT2ENTranslator

logger = logging.getLogger(__name__)


class SummarizationAgent:
    """
    Produces a FHIR extension dict enriching DiagnosticReport with summaries.

    Minimal usage (extractive only, no GPU required):
        agent = SummarizationAgent()
        ext = agent.build_extension(source_text)
        diagnostic_report.setdefault("extension", []).append(ext)

    Full pipeline (abstractive + translation):
        cfg = SummarizationConfig(run_abstractive=True, run_translation=True)
        agent = SummarizationAgent(cfg)
    """

    def __init__(self, config: Optional[SummarizationConfig] = None) -> None:
        self._cfg = config or SummarizationConfig()
        self._extractive = ExtractiveSummarizer(self._cfg)
        self._abstractive: Optional[AbstractiveSummarizer] = None
        self._translator: Optional[PT2ENTranslator] = None

        if self._cfg.run_abstractive:
            self._abstractive = AbstractiveSummarizer(
                model_name=self._cfg.abstractive_model_key,
                device=self._cfg.device,
            )
        if self._cfg.run_translation:
            self._translator = PT2ENTranslator(
                model_name=TRANSLATION_MODEL_PT_EN,
                device=self._cfg.device,
            )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def build_extension(self, source_text: str) -> Optional[dict]:
        """
        Build the FHIR radiology-summary extension dict for *source_text*.

        Returns None if the text is too short to summarize meaningfully.
        """
        if not source_text or len(source_text) < self._cfg.min_source_chars:
            return None

        extractive_pt = self._extractive.summarize_as_text(source_text)
        abstractive_pt = ""
        if self._abstractive:
            abstractive_pt = self._abstractive.summarize(source_text, config=self._cfg)
            if abstractive_pt:
                logger.debug("Abstractive summary (%d chars).", len(abstractive_pt))

        # Translate the best available PT summary
        translation_en = ""
        if self._translator:
            to_translate = abstractive_pt or extractive_pt
            translation_en = self._translator.translate(
                to_translate, max_length=self._cfg.translation_max_length
            )
            if translation_en:
                logger.debug("EN translation (%d chars).", len(translation_en))

        return self._assemble_extension(
            extractive_pt=extractive_pt,
            abstractive_pt=abstractive_pt,
            translation_en=translation_en,
        )

    def enrich_bundle(self, bundle: dict) -> dict:
        """
        Add summarization extension to every DiagnosticReport in *bundle*.

        Modifies and returns the bundle in place.
        """
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "DiagnosticReport":
                continue
            source = resource.get("conclusion", "")
            if not source:
                continue
            ext = self.build_extension(source)
            if ext is not None:
                resource.setdefault("extension", []).append(ext)
        return bundle

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _assemble_extension(
        self,
        extractive_pt: str,
        abstractive_pt: str,
        translation_en: str,
    ) -> dict:
        sub_extensions = []

        if extractive_pt:
            sub_extensions.append(
                {"url": "extractive_pt", "valueString": extractive_pt}
            )
        if abstractive_pt:
            sub_extensions.append(
                {"url": "abstractive_pt", "valueString": abstractive_pt}
            )
            sub_extensions.append(
                {
                    "url": "model_abstractive_pt",
                    "valueString": self._cfg.abstractive_model_key,
                }
            )
        if translation_en:
            sub_extensions.append(
                {"url": "translation_en", "valueString": translation_en}
            )
            sub_extensions.append(
                {"url": "model_translation_en", "valueString": "opus-mt-ROMANCE-en"}
            )

        sub_extensions.append(
            {
                "url": "generated_at",
                "valueDateTime": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S+00:00"
                ),
            }
        )

        return {"url": FHIR_SUMMARY_EXT_URL, "extension": sub_extensions}
