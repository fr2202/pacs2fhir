"""
Batch post-processor: adds summarization extensions to existing FHIR bundles.

Reads bundles from fhir_transformer/output/fhir_con_conclusion/ (bundles that
already have a DiagnosticReport.conclusion field) and writes enriched copies to
fhir_transformer/output/fhir_bundles_summarized/.

Usage examples:

  # Extractive only (fast, no GPU, default):
  python -m scripts.run_summarization

  # Extractive + PT→EN translation:
  python -m scripts.run_summarization --translate

  # Full pipeline with a fine-tuned local model:
  python -m scripts.run_summarization --abstractive --model path/to/checkpoint --translate

  # Test on first 50 bundles:
  python -m scripts.run_summarization --limit 50

Run from fhir_transformer/ directory.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Allow running from fhir_transformer/ root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.summarization_agent import SummarizationAgent
from summarization.config import SummarizationConfig
from utils.logger_utils import get_logger

logger = get_logger("run_summarization", Path("logs"))

_DEFAULT_INPUT = Path(__file__).resolve().parent.parent / "output" / "fhir_con_conclusion"
_DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "output" / "fhir_bundles_summarized"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enrich FHIR bundles with summarization extensions.")
    p.add_argument("--input", type=Path, default=_DEFAULT_INPUT,
                   help="Directory with input .fhir.json bundles (default: output/fhir_con_conclusion)")
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT,
                   help="Output directory for enriched bundles (default: output/fhir_bundles_summarized)")
    p.add_argument("--abstractive", action="store_true",
                   help="Enable abstractive summarization (requires GPU or patience)")
    p.add_argument("--model", default="ptt5-base",
                   help="Abstractive model key or local checkpoint path (default: ptt5-base)")
    p.add_argument("--translate", action="store_true",
                   help="Enable PT→EN translation of the best available PT summary")
    p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                   help="Hardware device (default: auto)")
    p.add_argument("--limit", type=int, default=0,
                   help="Process only first N bundles (0 = all)")
    p.add_argument("--workers", type=int, default=1,
                   help="Parallel workers (abstractive models are not thread-safe; keep 1 for GPU)")
    return p.parse_args()


def process_bundle(bundle_path: Path, agent: SummarizationAgent, out_dir: Path) -> bool:
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read %s: %s", bundle_path.name, exc)
        return False

    agent.enrich_bundle(bundle)
    out_path = out_dir / bundle_path.name
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def main() -> None:
    args = parse_args()

    cfg = SummarizationConfig(
        run_abstractive=args.abstractive,
        abstractive_model_key=args.model,
        run_translation=args.translate,
        device=args.device,
    )
    agent = SummarizationAgent(cfg)

    input_dir: Path = args.input
    output_dir: Path = args.output

    if not input_dir.exists():
        logger.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_files = sorted(input_dir.glob("*.fhir.json"))
    if not bundle_files:
        bundle_files = sorted(input_dir.glob("*.json"))

    if args.limit > 0:
        bundle_files = bundle_files[: args.limit]

    total = len(bundle_files)
    logger.info(
        "Processing %d bundles from %s → %s", total, input_dir, output_dir
    )
    logger.info(
        "Config: abstractive=%s, model=%s, translate=%s, device=%s",
        cfg.run_abstractive,
        cfg.abstractive_model_key if cfg.run_abstractive else "—",
        cfg.run_translation,
        cfg.device,
    )

    success = 0
    for i, path in enumerate(bundle_files, 1):
        if process_bundle(path, agent, output_dir):
            success += 1
        if i % 100 == 0:
            logger.info("Progress: %d / %d", i, total)

    logger.info("Done. %d / %d bundles enriched → %s", success, total, output_dir)
    print(f"\nDone: {success}/{total} bundles enriched → {output_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
