"""
Coordinator Agent
Orchestrates the full PACS → FHIR R4 transformation pipeline.

Architecture:
  - Divides 10K+ files into batches
  - Dispatches batches to worker processes (ProcessPoolExecutor)
  - Each worker runs the full agent pipeline on its batch
  - Aggregates results and writes a summary report
"""
import json
import logging
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    INPUT_DIR, OUTPUT_DIR, LOG_DIR, NUM_WORKERS, BATCH_SIZE,
    ORGANIZATION_ID, ORGANIZATION_NAME, ORGANIZATION_SYSTEM, FHIR_BASE_URL,
)
from utils.logger_utils import get_logger

ORGANIZATION_RESOURCE = {
    "resourceType": "Organization",
    "id": ORGANIZATION_ID,
    "meta": {
        "profile": ["http://hl7.org/fhir/StructureDefinition/Organization"]
    },
    "identifier": [
        {
            "use": "official",
            "system": ORGANIZATION_SYSTEM,
            "value": ORGANIZATION_ID
        }
    ],
    "active": True,
    "name": ORGANIZATION_NAME,
    "alias": ["CHULN"],
    "address": [
        {
            "use": "work",
            "type": "physical",
            "city": "Lisboa",
            "country": "PT"
        }
    ],
}


def _process_batch(batch_args: tuple) -> dict:
    """
    Worker function executed in a separate process.
    Processes one batch of files using TransformationPipeline.
    Returns a summary dict.
    """
    batch_files, worker_id, output_dir, log_dir = batch_args

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from agents.pipeline import TransformationPipeline, PipelineInput

    logger = get_logger(f"worker_{worker_id}", Path(log_dir))
    pipeline = TransformationPipeline.build_default()

    stats = {
        "worker_id": worker_id,
        "total": len(batch_files),
        "success": 0,
        "skipped": 0,
        "validation_errors": 0,
        "errors": [],
    }

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for file_path in batch_files:
        file_path = Path(file_path)
        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
            pacs = data.get("PACS_Report", {})
            patient_data = pacs.get("Patient", {})
            report_data = pacs.get("Report", {})

            patient_id = patient_data.get("ID", "")
            accession = report_data.get("AccessionNumber", "")

            if not patient_id or not accession:
                stats["skipped"] += 1
                continue

            inputs = PipelineInput(
                patient_id=patient_id,
                birthdate=patient_data.get("Birthdate", ""),
                accession=accession,
                exam_type=report_data.get("Exam_Type", "Unknown"),
                obs_rtf=report_data.get("Observation", ""),
                rep_rtf=report_data.get("Report", ""),
                validation_ts=report_data.get("Validation_Timestamp", ""),
                extraction_ts=pacs.get("Extraction_Timestamp", ""),
            )

            result = pipeline.run(inputs, ORGANIZATION_RESOURCE)

            if not result.success:
                stats["errors"].append({"file": str(file_path.name), "error": result.error})
                logger.error("Failed %s: %s", file_path.name, result.error)
                continue

            if result.validation_warnings:
                stats["validation_errors"] += 1
                logger.warning("Validation warnings in %s: %s", file_path.name, result.validation_warnings[:3])

            out_file = output_path / f"{file_path.stem}.fhir.json"
            out_file.write_text(
                json.dumps(result.bundle, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            stats["success"] += 1

        except Exception as exc:
            stats["errors"].append({"file": str(file_path.name), "error": str(exc)})
            logger.error("Failed %s: %s", file_path.name, exc)

    logger.info(
        "Worker %d done. success=%d skipped=%d errors=%d",
        worker_id, stats["success"], stats["skipped"], len(stats["errors"])
    )
    return stats


class CoordinatorAgent:
    """
    Orchestrates the full PACS JSON → FHIR R4 transformation.

    Usage:
        coordinator = CoordinatorAgent()
        coordinator.run()
    """

    def __init__(self, num_workers: int = NUM_WORKERS, batch_size: int = BATCH_SIZE):
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.logger = get_logger("coordinator", LOG_DIR)

    def run(self):
        self.logger.info("=" * 60)
        self.logger.info("FHIR Transformation Pipeline starting")
        self.logger.info("Input: %s", INPUT_DIR)
        self.logger.info("Output: %s", OUTPUT_DIR)
        self.logger.info("Workers: %d | Batch size: %d", self.num_workers, self.batch_size)
        self.logger.info("=" * 60)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        self._save_organization()

        all_files = sorted(INPUT_DIR.glob("*.txt"))
        total = len(all_files)
        self.logger.info("Discovered %d input files", total)

        if total == 0:
            self.logger.error("No .txt files found in %s", INPUT_DIR)
            return

        batches = self._split_batches(all_files)
        self.logger.info("Split into %d batches", len(batches))

        start_time = time.time()
        all_stats = []

        try:
            from tqdm import tqdm
            progress = tqdm(total=total, desc="Processing", unit="files")
            use_tqdm = True
        except ImportError:
            use_tqdm = False
            progress = None

        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            batch_args = [
                (
                    [str(f) for f in batch],
                    idx,
                    str(OUTPUT_DIR),
                    str(LOG_DIR),
                )
                for idx, batch in enumerate(batches)
            ]

            future_map = {executor.submit(_process_batch, args): args[1] for args in batch_args}

            for future in as_completed(future_map):
                worker_id = future_map[future]
                try:
                    stats = future.result()
                    all_stats.append(stats)
                    processed = stats["success"] + stats["skipped"] + len(stats["errors"])
                    if use_tqdm and progress:
                        progress.update(processed)
                    else:
                        self.logger.info(
                            "Worker %d finished: %d/%d files",
                            worker_id, processed, total
                        )
                except Exception as exc:
                    self.logger.error("Worker %d crashed: %s", worker_id, exc)

        if use_tqdm and progress:
            progress.close()

        elapsed = time.time() - start_time
        self._write_summary(all_stats, total, elapsed)

    def _split_batches(self, files: list) -> list:
        return [files[i: i + self.batch_size] for i in range(0, len(files), self.batch_size)]

    def _save_organization(self):
        org_path = OUTPUT_DIR / "Organization_chuln.fhir.json"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        org_path.write_text(
            json.dumps(ORGANIZATION_RESOURCE, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        self.logger.info("Organization resource saved: %s", org_path)

    def _write_summary(self, all_stats: list, total_files: int, elapsed: float):
        total_success = sum(s["success"] for s in all_stats)
        total_skipped = sum(s["skipped"] for s in all_stats)
        total_val_errors = sum(s["validation_errors"] for s in all_stats)
        all_errors = [e for s in all_stats for e in s.get("errors", [])]

        summary = {
            "total_input_files": total_files,
            "total_success": total_success,
            "total_skipped": total_skipped,
            "total_validation_warnings": total_val_errors,
            "total_hard_errors": len(all_errors),
            "elapsed_seconds": round(elapsed, 2),
            "files_per_second": round(total_success / elapsed, 1) if elapsed > 0 else 0,
            "workers": self.num_workers,
            "per_worker": all_stats,
            "errors_sample": all_errors[:50],
        }

        summary_path = LOG_DIR / "transformation_summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        self.logger.info("=" * 60)
        self.logger.info("TRANSFORMATION COMPLETE")
        self.logger.info("  Total files:       %d", total_files)
        self.logger.info("  Success:           %d", total_success)
        self.logger.info("  Skipped:           %d", total_skipped)
        self.logger.info("  Validation warns:  %d", total_val_errors)
        self.logger.info("  Hard errors:       %d", len(all_errors))
        self.logger.info("  Elapsed:           %.1fs", elapsed)
        self.logger.info("  Throughput:        %.1f files/sec", summary["files_per_second"])
        self.logger.info("  Summary saved:     %s", summary_path)
        self.logger.info("=" * 60)
