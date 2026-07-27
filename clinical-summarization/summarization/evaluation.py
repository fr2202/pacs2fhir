"""
Evaluation metrics for multilingual summarization.

Metrics:
  - ROUGE-1 / ROUGE-2 / ROUGE-L  (lexical overlap, standard in summarization)
  - BERTScore F1                  (semantic similarity; PT model for Portuguese,
                                   multilingual model for cross-lingual EN vs PT reference)
  - Faithfulness                  (NLI entailment score: P(summary entailed by source),
                                   detects hallucinations without human annotation)
  - Compression ratio             (source_chars / summary_chars)
  - Average summary length (chars)

Usage:
    evaluator = MultilingualEvaluator()
    metrics = evaluator.evaluate(
        sources=["Relatório de TC tórax..."],
        summaries=["Achados sugestivos de..."],
        references=["Conclusão: edema pulmonar..."],
        lang="pt",
    )
    print(metrics)
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from summarization.config import (
    BERTSCORE_MODEL_PT,
    BERTSCORE_MODEL_MULTILINGUAL,
    NLI_MODEL,
)

logger = logging.getLogger(__name__)


@dataclass
class SummaryMetrics:
    rouge1_p: float = 0.0
    rouge1_r: float = 0.0
    rouge1_f: float = 0.0
    rouge2_p: float = 0.0
    rouge2_r: float = 0.0
    rouge2_f: float = 0.0
    rougeL_p: float = 0.0
    rougeL_r: float = 0.0
    rougeL_f: float = 0.0
    bertscore_p: float = 0.0
    bertscore_r: float = 0.0
    bertscore_f: float = 0.0
    faithfulness_mean: float = 0.0
    faithfulness_std: float = 0.0
    compression_ratio_mean: float = 0.0
    avg_summary_length: float = 0.0
    n_evaluated: int = 0
    bertscore_model: str = ""

    def as_dict(self) -> Dict:
        return asdict(self)

    def markdown_row(self, label: str) -> str:
        """Return a single markdown table row for this metric set."""
        return (
            f"| {label} "
            f"| {self.rouge1_f:.3f} "
            f"| {self.rouge2_f:.3f} "
            f"| {self.rougeL_f:.3f} "
            f"| {self.bertscore_f:.3f} "
            f"| {self.faithfulness_mean:.3f} "
            f"| {self.compression_ratio_mean:.1f} "
            f"| {int(self.avg_summary_length)} |"
        )


class MultilingualEvaluator:
    """
    Evaluates summarization quality across Portuguese and English.

    All models are lazy-loaded to avoid mandatory GPU/network dependency
    when only a subset of metrics is needed.
    """

    def __init__(self) -> None:
        self._rouge_scorer = None
        self._nli_model = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        sources: List[str],
        summaries: List[str],
        references: Optional[List[str]] = None,
        lang: str = "pt",
    ) -> SummaryMetrics:
        """
        Compute all metrics for *summaries* against optional *references*.

        When *references* is None, ROUGE is skipped and BERTScore compares
        summaries against sources (coverage proxy). Faithfulness is always
        computed against sources.

        Args:
            sources:    Original report texts.
            summaries:  Generated summaries (same order as sources).
            references: Reference summaries (human or heuristic). May be None.
            lang:       "pt" or "en". Selects BERTScore model.
        """
        assert len(sources) == len(summaries), "sources and summaries must align"
        if references is not None:
            assert len(sources) == len(references), "references must align with sources"

        pairs = [
            (src, sm, ref)
            for src, sm, ref in zip(
                sources,
                summaries,
                references if references is not None else [None] * len(sources),
            )
            if src and sm
        ]
        if not pairs:
            return SummaryMetrics()

        filtered_sources = [p[0] for p in pairs]
        filtered_summaries = [p[1] for p in pairs]
        filtered_refs = [p[2] for p in pairs] if references is not None else None

        metrics = SummaryMetrics(n_evaluated=len(pairs))

        # ROUGE (requires references)
        if filtered_refs and all(r for r in filtered_refs):
            rouge = self._compute_rouge(filtered_summaries, filtered_refs)
            metrics.rouge1_p = rouge["rouge1"]["p"]
            metrics.rouge1_r = rouge["rouge1"]["r"]
            metrics.rouge1_f = rouge["rouge1"]["f"]
            metrics.rouge2_p = rouge["rouge2"]["p"]
            metrics.rouge2_r = rouge["rouge2"]["r"]
            metrics.rouge2_f = rouge["rouge2"]["f"]
            metrics.rougeL_p = rouge["rougeL"]["p"]
            metrics.rougeL_r = rouge["rougeL"]["r"]
            metrics.rougeL_f = rouge["rougeL"]["f"]

        # BERTScore
        bert_refs = filtered_refs if (filtered_refs and all(r for r in filtered_refs)) else filtered_sources
        bertscore_model = BERTSCORE_MODEL_PT if lang == "pt" else BERTSCORE_MODEL_MULTILINGUAL
        bs = self._compute_bertscore(filtered_summaries, bert_refs, model_type=bertscore_model)
        metrics.bertscore_p = bs["p"]
        metrics.bertscore_r = bs["r"]
        metrics.bertscore_f = bs["f"]
        metrics.bertscore_model = bertscore_model

        # Faithfulness (NLI-based)
        faith_scores = self._compute_faithfulness(filtered_sources, filtered_summaries)
        if faith_scores:
            import statistics
            metrics.faithfulness_mean = statistics.mean(faith_scores)
            metrics.faithfulness_std = (
                statistics.stdev(faith_scores) if len(faith_scores) > 1 else 0.0
            )

        # Descriptive stats
        ratios = [
            len(src) / max(len(sm), 1)
            for src, sm in zip(filtered_sources, filtered_summaries)
        ]
        metrics.compression_ratio_mean = sum(ratios) / len(ratios)
        metrics.avg_summary_length = sum(len(s) for s in filtered_summaries) / len(filtered_summaries)

        return metrics

    # ------------------------------------------------------------------
    # ROUGE
    # ------------------------------------------------------------------

    def _get_rouge_scorer(self):
        if self._rouge_scorer is None:
            try:
                from rouge_score import rouge_scorer as rs_lib
            except ImportError as exc:
                raise RuntimeError(
                    "rouge-score is required. pip install rouge-score"
                ) from exc
            self._rouge_scorer = rs_lib.RougeScorer(
                ["rouge1", "rouge2", "rougeL"], use_stemmer=True
            )
        return self._rouge_scorer

    def _compute_rouge(
        self, predictions: List[str], references: List[str]
    ) -> Dict[str, Dict[str, float]]:
        scorer = self._get_rouge_scorer()
        agg: Dict[str, Dict[str, List[float]]] = {
            k: {"p": [], "r": [], "f": []} for k in ["rouge1", "rouge2", "rougeL"]
        }
        for pred, ref in zip(predictions, references):
            if not pred or not ref:
                continue
            scores = scorer.score(ref, pred)
            for key in agg:
                s = scores[key]
                agg[key]["p"].append(s.precision)
                agg[key]["r"].append(s.recall)
                agg[key]["f"].append(s.fmeasure)

        result: Dict[str, Dict[str, float]] = {}
        for key, vals in agg.items():
            n = len(vals["f"]) or 1
            result[key] = {
                "p": sum(vals["p"]) / n,
                "r": sum(vals["r"]) / n,
                "f": sum(vals["f"]) / n,
            }
        return result

    # ------------------------------------------------------------------
    # BERTScore
    # ------------------------------------------------------------------

    def _compute_bertscore(
        self,
        predictions: List[str],
        references: List[str],
        model_type: str = BERTSCORE_MODEL_PT,
    ) -> Dict[str, float]:
        try:
            from bert_score import score as bert_score_fn, model2layers
        except ImportError as exc:
            raise RuntimeError(
                "bert-score is required. pip install bert-score"
            ) from exc

        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(
            "Computing BERTScore with model '%s' on %d pairs...",
            model_type,
            len(predictions),
        )

        # BERT max is 512 tokens (~1800 chars). Truncate to avoid OOM/shape errors.
        # References in this corpus can reach 3000+ chars (full RTF conclusion sections).
        _MAX_CHARS = 1500
        predictions_t = [p[:_MAX_CHARS] for p in predictions]
        references_t  = [r[:_MAX_CHARS] for r in references]

        # bert_score only knows num_layers for its built-in models.
        # For external HF models (e.g. neuralmind/*), pass num_layers explicitly.
        # BERT-base = 9 optimal layers; BERT-large = 17.
        if model_type in model2layers:
            P, R, F = bert_score_fn(
                predictions_t, references_t,
                model_type=model_type, verbose=False, device=device,
            )
        else:
            num_layers = 17 if "large" in model_type else 9
            P, R, F = bert_score_fn(
                predictions_t, references_t,
                model_type=model_type, num_layers=num_layers,
                verbose=False, device=device,
            )

        return {
            "p": float(P.mean()),
            "r": float(R.mean()),
            "f": float(F.mean()),
        }

    # ------------------------------------------------------------------
    # Faithfulness (NLI-based)
    # ------------------------------------------------------------------

    def _get_nli_model(self):
        if self._nli_model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for faithfulness scoring. "
                    "pip install sentence-transformers"
                ) from exc
            logger.info("Loading NLI model '%s'...", NLI_MODEL)
            self._nli_model = CrossEncoder(NLI_MODEL)
            logger.info("NLI model loaded.")
        return self._nli_model

    def _compute_faithfulness(
        self, sources: List[str], summaries: List[str]
    ) -> List[float]:
        """
        Compute per-sample faithfulness as P(summary entailed by source).

        Label order for cross-encoder/nli-deberta-v3-small:
            [contradiction, entailment, neutral]
        """
        try:
            import numpy as np
            nli = self._get_nli_model()
        except Exception as exc:
            logger.warning("Faithfulness scoring unavailable: %s", exc)
            return []

        # Truncate source to 800 chars to stay within NLI model context
        pairs = [(src[:800], sm) for src, sm in zip(sources, summaries) if src and sm]
        if not pairs:
            return []

        logits = nli.predict(pairs)
        # Apply softmax and return entailment probability (index 1)
        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp / exp.sum(axis=1, keepdims=True)
        return probs[:, 1].tolist()
