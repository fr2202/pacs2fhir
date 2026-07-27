"""
FHIR Transformer — Entry Point
Converts CHULN PACS JSON records to FHIR R4 Bundles using multiple parallel agents.

Usage:
    python main.py                        # Run with defaults
    python main.py --workers 8            # Override worker count
    python main.py --batch-size 200       # Override batch size
    python main.py --input /path/to/json  # Override input directory
    python main.py --limit 100            # Process only first N files (for testing)
"""
import argparse
import multiprocessing
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def parse_args():
    parser = argparse.ArgumentParser(
        description="PACS JSON → FHIR R4 multi-agent transformer"
    )
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel worker processes")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Files per batch per worker")
    parser.add_argument("--input", type=str, default=None,
                        help="Override input directory")
    parser.add_argument("--output", type=str, default=None,
                        help="Override output directory")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to first N files (for testing)")
    return parser.parse_args()


def main():
    args = parse_args()

    import config.settings as settings

    if args.input:
        settings.INPUT_DIR = Path(args.input)
    if args.output:
        settings.OUTPUT_DIR = Path(args.output) / "fhir_bundles"

    from agents.coordinator_agent import CoordinatorAgent

    kwargs = {}
    if args.workers is not None:
        kwargs["num_workers"] = args.workers
    if args.batch_size is not None:
        kwargs["batch_size"] = args.batch_size

    coordinator = CoordinatorAgent(**kwargs)

    if args.limit:
        all_files = sorted(settings.INPUT_DIR.glob("*.txt"))[: args.limit]
        coordinator.logger.info("--limit: processing only %d files", len(all_files))
        import json, time
        from agents.coordinator_agent import _process_batch, ORGANIZATION_RESOURCE

        settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        org_path = settings.OUTPUT_DIR / "Organization_chuln.fhir.json"
        org_path.write_text(
            json.dumps(ORGANIZATION_RESOURCE, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        batches = coordinator._split_batches(all_files)
        start = time.time()
        all_stats = []
        for idx, batch in enumerate(batches):
            stats = _process_batch((
                [str(f) for f in batch], idx,
                str(settings.OUTPUT_DIR), str(settings.LOG_DIR)
            ))
            all_stats.append(stats)
        coordinator._write_summary(all_stats, len(all_files), time.time() - start)
    else:
        coordinator.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
