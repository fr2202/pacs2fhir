"""
Multilingual summarization evaluation.

Produces the comparison table used in the thesis (Chapter: Evaluation).
Evaluates all configured models on the test split and outputs:
  - results/eval_multilingual.json       (full metrics per model)
  - results/eval_multilingual_table.md   (markdown table, copy-paste ready)
  - Console table for quick inspection

Dataset: reads sumarizacion/data/processed/dataset_test.jsonl by default.
Only records with `has_reference: true` are used for ROUGE and BERTScore.

Usage:

  # Evaluate only extractive baseline (fast):
  python -m scripts.eval_multilingual --models extractive

  # Full ablation (slow on CPU — use GPU for abstractive models):
  python -m scripts.eval_multilingual --models extractive mt5-xlsum mt5-small ptt5-base

  # Use a fine-tuned checkpoint:
  python -m scripts.eval_multilingual --models extractive path/to/checkpoint --translate

  # Limit to 200 test samples (faster iteration):
  python -m scripts.eval_multilingual --limit 200

Run from fhir_transformer/ directory.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from summarization.config import SummarizationConfig
from summarization.extractive import ExtractiveSummarizer
from summarization.abstractive import AbstractiveSummarizer
from summarization.translation import PT2ENTranslator
from summarization.evaluation import MultilingualEvaluator, SummaryMetrics

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("eval_multilingual")

_SUMARIZACION_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "sumarizacion"
)
_DEFAULT_TEST_JSONL = _SUMARIZACION_ROOT / "data" / "processed" / "dataset_test.jsonl"
_RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

_MARKDOWN_HEADER = (
    "| Model | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore-F | "
    "Faithfulness | Compression | Avg Len (chars) |\n"
    "|-------|---------|---------|---------|-------------|"
    "-------------|-------------|-----------------|"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Evaluate multilingual summarization on the CHULN test set."
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=["extractive"],
        help=(
            "Models to evaluate. Special value 'extractive' runs TF-IDF. "
            "Other values are passed to AbstractiveSummarizer as model keys or paths. "
            "Default: extractive"
        ),
    )
    p.add_argument(
        "--translate",
        action="store_true",
        help="Also evaluate PT→EN translation (requires opus-mt-tc-big-pt-en).",
    )
    p.add_argument(
        "--input",
        type=Path,
        default=_DEFAULT_TEST_JSONL,
        help=f"Test JSONL file (default: {_DEFAULT_TEST_JSONL})",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max samples to evaluate (0 = all with reference).",
    )
    p.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
    )
    p.add_argument(
        "--skip-faithfulness",
        action="store_true",
        help="Skip NLI faithfulness scoring (faster, saves memory).",
    )
    p.add_argument(
        "--skip-bertscore",
        action="store_true",
        help="Skip BERTScore (faster, saves memory).",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_RESULTS_DIR,
    )
    p.add_argument(
        "--name",
        type=str,
        default="multilingual",
        help=(
            "Output file stem. Writes results/eval_<name>.json and "
            "results/eval_<name>_table.md. Use a descriptive id per experiment "
            "(e.g. 'pt_models_n100', 'finetuned_full') so files are not overwritten."
        ),
    )
    return p.parse_args()


def load_test_data(
    jsonl_path: Path, limit: int
) -> Tuple[List[str], List[str]]:
    """Return (sources, references) from the test JSONL (only records with reference)."""
    if not jsonl_path.exists():
        logger.error(
            "Test dataset not found: %s\n"
            "Run the sumarizacion pipeline first:\n"
            "  cd ../sumarizacion && python scripts/build_dataset.py",
            jsonl_path,
        )
        sys.exit(1)

    sources, refs = [], []
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if not rec.get("has_reference"):
                continue
            src = rec.get("source", "").strip()
            ref = rec.get("reference", "").strip()
            if src and ref:
                sources.append(src)
                refs.append(ref)
            if limit and len(sources) >= limit:
                break

    logger.info("Loaded %d test samples with references.", len(sources))
    return sources, refs


def run_extractive(
    sources: List[str], cfg: SummarizationConfig
) -> List[str]:
    summarizer = ExtractiveSummarizer(cfg)
    return [summarizer.summarize_as_text(s) for s in sources]


def run_abstractive(
    sources: List[str], model_key: str, cfg: SummarizationConfig
) -> List[str]:
    summarizer = AbstractiveSummarizer(model_name=model_key, device=cfg.device)
    return [summarizer.summarize(s, config=cfg) for s in sources]


def run_translation(
    summaries: List[str], cfg: SummarizationConfig
) -> List[str]:
    translator = PT2ENTranslator(device=cfg.device)
    return [translator.translate(s, max_length=cfg.translation_max_length) for s in summaries]


def _evaluate_run(
    evaluator: MultilingualEvaluator,
    sources: List[str],
    summaries: List[str],
    references: Optional[List[str]],
    lang: str,
    skip_faithfulness: bool,
    skip_bertscore: bool,
) -> SummaryMetrics:
    """Compute metrics, honouring skip flags."""
    # Temporarily monkey-patch to skip expensive steps if requested
    orig_faith = evaluator._compute_faithfulness
    orig_bs = evaluator._compute_bertscore
    if skip_faithfulness:
        evaluator._compute_faithfulness = lambda *_: []
    if skip_bertscore:
        evaluator._compute_bertscore = lambda *_, **__: {"p": 0.0, "r": 0.0, "f": 0.0}

    metrics = evaluator.evaluate(sources, summaries, references, lang=lang)

    # Restore
    evaluator._compute_faithfulness = orig_faith
    evaluator._compute_bertscore = orig_bs
    return metrics


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cfg = SummarizationConfig(device=args.device)
    sources, references = load_test_data(args.input, args.limit)

    evaluator = MultilingualEvaluator()
    results: Dict[str, dict] = {}
    table_rows: List[str] = []

    for model_key in args.models:
        logger.info("=== Evaluating: %s ===", model_key)

        if model_key == "extractive":
            summaries_pt = run_extractive(sources, cfg)
            label = "Extractive TF-IDF (PT)"
        else:
            summaries_pt = run_abstractive(sources, model_key, cfg)
            label = f"{model_key} (PT)"

        logger.info("  Generated %d PT summaries. Computing metrics...", len(summaries_pt))
        metrics_pt = _evaluate_run(
            evaluator, sources, summaries_pt, references,
            lang="pt",
            skip_faithfulness=args.skip_faithfulness,
            skip_bertscore=args.skip_bertscore,
        )
        results[f"{model_key}_pt"] = metrics_pt.as_dict()
        table_rows.append(metrics_pt.markdown_row(label))
        _print_metrics(label, metrics_pt)

        if args.translate:
            logger.info("  Translating PT summaries to EN...")
            summaries_en = run_translation(summaries_pt, cfg)
            # For EN evaluation, use multilingual BERTScore vs PT reference (cross-lingual)
            metrics_en = _evaluate_run(
                evaluator, sources, summaries_en, references,
                lang="en",
                skip_faithfulness=args.skip_faithfulness,
                skip_bertscore=args.skip_bertscore,
            )
            en_label = f"{model_key} + opus-mt (EN)"
            results[f"{model_key}_en"] = metrics_en.as_dict()
            table_rows.append(metrics_en.markdown_row(en_label))
            _print_metrics(en_label, metrics_en)

    # Write JSON results
    json_out = args.output_dir / f"eval_{args.name}.json"
    json_out.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Results written to %s", json_out)

    # Write markdown table
    md_out = args.output_dir / f"eval_{args.name}_table.md"
    md_lines = [
        "# Multilingual Summarization Evaluation — CHULN Radiology Test Set",
        "",
        f"**Test samples (with reference):** {len(sources)}",
        f"**BERTScore model (PT):** neuralmind/bert-base-portuguese-cased",
        f"**BERTScore model (EN cross-lingual):** bert-base-multilingual-cased",
        f"**Faithfulness:** NLI entailment score (cross-encoder/nli-deberta-v3-small)",
        "",
        _MARKDOWN_HEADER,
    ] + table_rows + [""]
    md_out.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Markdown table written to %s", md_out)

    print(f"\n{'='*70}")
    print("EVALUATION TABLE")
    print('='*70)
    print(_MARKDOWN_HEADER)
    for row in table_rows:
        print(row)
    print(f"\nResults: {json_out}")
    print(f"Table:   {md_out}")


def _print_metrics(label: str, m: SummaryMetrics) -> None:
    print(
        f"\n  {label}\n"
        f"    ROUGE-1 F={m.rouge1_f:.3f}  ROUGE-2 F={m.rouge2_f:.3f}  "
        f"ROUGE-L F={m.rougeL_f:.3f}\n"
        f"    BERTScore F={m.bertscore_f:.3f}  "
        f"Faithfulness={m.faithfulness_mean:.3f}±{m.faithfulness_std:.3f}\n"
        f"    Compression={m.compression_ratio_mean:.1f}x  "
        f"Avg length={int(m.avg_summary_length)} chars  "
        f"n={m.n_evaluated}"
    )


if __name__ == "__main__":
    main()
