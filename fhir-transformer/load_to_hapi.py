"""
HAPI FHIR Bulk Loader
Sends all FHIR R4 transaction bundles to a HAPI FHIR server.

Features:
  - Parallel HTTP workers (ThreadPoolExecutor — I/O bound)
  - Retry with exponential backoff on 429 / 5xx
  - Checkpoint file: resume after interruption without re-sending
  - Detailed per-bundle log + final summary JSON
  - Dry-run mode to validate connectivity before sending

Usage:
    python load_to_hapi.py --server http://localhost:8080/fhir
    python load_to_hapi.py --server http://localhost:8080/fhir --workers 4
    python load_to_hapi.py --server http://localhost:8080/fhir --dry-run
    python load_to_hapi.py --server http://localhost:8080/fhir --resume
    python load_to_hapi.py --server http://localhost:8080/fhir --workers 8 --timeout 60
"""
import argparse
import json
import logging
import multiprocessing
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
BUNDLES_DIR = Path("output/fhir_con_conclusion")
LOG_DIR = Path("logs")
CHECKPOINT_FILE = LOG_DIR / "load_checkpoint.json"
LOAD_LOG_FILE = LOG_DIR / "load_results.jsonl"
SUMMARY_FILE = LOG_DIR / "load_summary.json"

DEFAULT_WORKERS = 4          # conservative default — HAPI handles ~4-8 concurrent well
DEFAULT_TIMEOUT = 60         # seconds per request
MAX_RETRIES = 3              # retry attempts on 429 / 5xx
BACKOFF_FACTOR = 2           # exponential backoff: 2, 4, 8 seconds
RETRY_STATUS_CODES = {409, 429, 500, 502, 503, 504}

FHIR_HEADERS = {
    "Content-Type": "application/fhir+json; charset=UTF-8",
    "Accept": "application/fhir+json",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "load_to_hapi.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("hapi_loader")


# ---------------------------------------------------------------------------
# HTTP session with built-in retry
# ---------------------------------------------------------------------------
def make_session(timeout: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(FHIR_HEADERS)
    return session


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------
def load_checkpoint() -> set:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("done", []))
    return set()


def save_checkpoint(done: set) -> None:
    CHECKPOINT_FILE.write_text(
        json.dumps({"done": sorted(done), "updated": datetime.now(timezone.utc).isoformat()},
                   indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Send one bundle
# ---------------------------------------------------------------------------
def send_bundle(args: tuple) -> dict:
    file_path, server_url, timeout, dry_run = args
    file_path = Path(file_path)
    result = {
        "file": file_path.name,
        "status": None,
        "http_code": None,
        "duration_ms": None,
        "error": None,
        "response_id": None,
    }
    try:
        raw = file_path.read_text(encoding="utf-8")
        bundle = json.loads(raw)

        if dry_run:
            result["status"] = "dry_run"
            result["http_code"] = 0
            result["duration_ms"] = 0
            return result

        session = make_session(timeout)
        t0 = time.time()
        resp = session.post(server_url, data=raw.encode("utf-8"), timeout=timeout)
        elapsed = round((time.time() - t0) * 1000)

        result["http_code"] = resp.status_code
        result["duration_ms"] = elapsed

        if resp.status_code in (200, 201):
            result["status"] = "ok"
            try:
                body = resp.json()
                result["response_id"] = body.get("id")
            except Exception:
                pass
        else:
            result["status"] = "error"
            # Capture first 500 chars of HAPI error body for debugging
            try:
                body = resp.json()
                issues = body.get("issue", [])
                result["error"] = "; ".join(
                    i.get("diagnostics", i.get("details", {}).get("text", ""))
                    for i in issues[:3]
                ) or resp.text[:500]
            except Exception:
                result["error"] = resp.text[:500]

    except requests.exceptions.ConnectionError as e:
        result["status"] = "connection_error"
        result["error"] = str(e)[:200]
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Timeout after {timeout}s"
    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# Send a standalone (non-Bundle) resource via PUT /ResourceType/id
# ---------------------------------------------------------------------------
def send_resource(file_path: Path, server_url: str, timeout: int, dry_run: bool) -> dict:
    result = {
        "file": file_path.name,
        "status": None,
        "http_code": None,
        "duration_ms": None,
        "error": None,
        "response_id": None,
    }
    try:
        raw = file_path.read_text(encoding="utf-8")
        resource = json.loads(raw)
        rt = resource.get("resourceType")
        rid = resource.get("id")

        if not rt or not rid:
            result["status"] = "error"
            result["error"] = "Missing resourceType or id"
            return result

        if dry_run:
            result["status"] = "dry_run"
            result["http_code"] = 0
            result["duration_ms"] = 0
            return result

        url = f"{server_url.rstrip('/')}/{rt}/{rid}"
        session = make_session(timeout)
        t0 = time.time()
        resp = session.put(url, data=raw.encode("utf-8"), timeout=timeout)
        elapsed = round((time.time() - t0) * 1000)

        result["http_code"] = resp.status_code
        result["duration_ms"] = elapsed

        if resp.status_code in (200, 201):
            result["status"] = "ok"
            try:
                result["response_id"] = resp.json().get("id")
            except Exception:
                pass
        else:
            result["status"] = "error"
            try:
                body = resp.json()
                issues = body.get("issue", [])
                result["error"] = "; ".join(
                    i.get("diagnostics", i.get("details", {}).get("text", ""))
                    for i in issues[:3]
                ) or resp.text[:500]
            except Exception:
                result["error"] = resp.text[:500]

    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------
def check_server(server_url: str, timeout: int) -> bool:
    meta_url = server_url.rstrip("/") + "/metadata"
    log.info("Checking HAPI FHIR server: %s", meta_url)
    try:
        resp = requests.get(meta_url, headers={"Accept": "application/fhir+json"},
                            timeout=timeout)
        if resp.status_code == 200:
            body = resp.json()
            fhir_version = body.get("fhirVersion", "?")
            software = body.get("software", {}).get("name", "?")
            log.info("Server OK — FHIR version: %s  software: %s", fhir_version, software)
            return True
        else:
            log.error("Server returned HTTP %d on /metadata", resp.status_code)
            return False
    except Exception as e:
        log.error("Cannot reach server: %s", e)
        return False


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------
def run(server_url: str, workers: int, timeout: int, dry_run: bool,
        resume: bool, limit: int = 0) -> None:

    server_url = server_url.rstrip("/")
    log.info("=" * 65)
    log.info("HAPI FHIR Bulk Loader")
    log.info("  Server  : %s", server_url)
    log.info("  Workers : %d", workers)
    log.info("  Timeout : %ds", timeout)
    log.info("  Dry-run : %s", dry_run)
    log.info("  Resume  : %s", resume)
    log.info("=" * 65)

    # 1. Connectivity check (skip on dry-run)
    if not dry_run:
        if not check_server(server_url, timeout):
            log.error("Aborting — server not reachable. Start HAPI FHIR first.")
            sys.exit(1)

    # 2. Collect bundle files (Organization first, then the rest sorted)
    org_file = BUNDLES_DIR / "Organization_chuln.fhir.json"
    bundle_files = sorted(
        f for f in BUNDLES_DIR.glob("*.fhir.json")
        if f.name != "Organization_chuln.fhir.json"
    )
    if limit:
        bundle_files = bundle_files[:limit]

    total = len(bundle_files)
    log.info("Bundles to send: %d (+ 1 Organization)", total)

    # 3. Resume: skip already-sent files
    done_set: set = set()
    if resume and CHECKPOINT_FILE.exists():
        done_set = load_checkpoint()
        skipped = len([f for f in bundle_files if f.name in done_set])
        bundle_files = [f for f in bundle_files if f.name not in done_set]
        log.info("Resume: skipping %d already sent, %d remaining", skipped, len(bundle_files))

    if not bundle_files and not org_file.exists():
        log.info("Nothing to send.")
        return

    # 4. Send Organization first via direct PUT /Organization/{id}
    #    Must complete before parallel workers start to avoid 409 race condition.
    if org_file.exists() and org_file.name not in done_set:
        log.info("Sending Organization resource (PUT /Organization/chuln)...")
        org_result = send_resource(org_file, server_url, timeout, dry_run)
        log.info("  Organization: HTTP %s  %s", org_result["http_code"], org_result["status"])
        if org_result["status"] not in ("ok", "dry_run"):
            log.warning("  Error: %s", org_result.get("error"))
        elif org_result["status"] == "ok":
            done_set.add(org_file.name)

    # 5. Parallel bundle sending
    stats = {"ok": 0, "error": 0, "timeout": 0, "connection_error": 0,
             "exception": 0, "dry_run": 0}
    errors_detail = []
    start_time = time.time()

    log_handle = LOAD_LOG_FILE.open("a", encoding="utf-8")

    try:
        from tqdm import tqdm
        progress = tqdm(total=len(bundle_files), desc="Sending", unit="bundles",
                        dynamic_ncols=True)
    except ImportError:
        progress = None

    send_args = [
        (str(f), server_url, timeout, dry_run)
        for f in bundle_files
    ]

    checkpoint_interval = 100  # save checkpoint every N files

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(send_bundle, args): args[0] for args in send_args}

        for i, future in enumerate(as_completed(future_map), 1):
            result = future.result()
            status = result["status"]
            stats[status] = stats.get(status, 0) + 1

            log_handle.write(json.dumps(result, ensure_ascii=False) + "\n")

            if status == "ok":
                done_set.add(result["file"])
            elif status not in ("dry_run",):
                errors_detail.append(result)
                log.warning("FAIL [%s] HTTP=%s  %s",
                            result["file"][:40], result["http_code"], result.get("error", "")[:80])

            if progress:
                progress.set_postfix(ok=stats["ok"], err=stats.get("error", 0) + stats.get("timeout", 0))
                progress.update(1)
            elif i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                log.info("Progress: %d/%d  ok=%d  err=%d  %.1f/s",
                         i, len(bundle_files), stats["ok"],
                         stats.get("error", 0) + stats.get("timeout", 0), rate)

            if i % checkpoint_interval == 0 and not dry_run:
                save_checkpoint(done_set)

    if progress:
        progress.close()

    log_handle.close()

    if not dry_run:
        save_checkpoint(done_set)

    # 6. Summary
    elapsed = time.time() - start_time
    total_sent = sum(stats.values())
    total_ok = stats.get("ok", 0) + stats.get("dry_run", 0)
    total_err = total_sent - total_ok

    summary = {
        "server": server_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "total_bundles": total,
        "total_sent": total_sent,
        "total_ok": total_ok,
        "total_error": total_err,
        "elapsed_seconds": round(elapsed, 1),
        "bundles_per_second": round(total_sent / elapsed, 1) if elapsed > 0 else 0,
        "stats": stats,
        "errors_sample": errors_detail[:20],
    }
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    log.info("=" * 65)
    log.info("LOAD COMPLETE")
    log.info("  Total sent   : %d", total_sent)
    log.info("  OK           : %d", total_ok)
    log.info("  Errors       : %d", total_err)
    log.info("  Elapsed      : %.1fs", elapsed)
    log.info("  Throughput   : %.1f bundles/s", summary["bundles_per_second"])
    log.info("  Summary      : %s", SUMMARY_FILE)
    log.info("  Detail log   : %s", LOAD_LOG_FILE)
    if total_err:
        log.warning("  %d errors — check %s for details", total_err, LOAD_LOG_FILE)
    log.info("=" * 65)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Bulk-load FHIR R4 bundles into a HAPI FHIR server"
    )
    parser.add_argument(
        "--server", required=True,
        help="HAPI FHIR base URL, e.g. http://localhost:8080/fhir"
    )
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Parallel HTTP threads (default: {DEFAULT_WORKERS})"
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and validate files without sending to server"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip files already sent (uses checkpoint file)"
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Override bundle directory (default: output/fhir_con_conclusion)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Send only first N bundles (for testing)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.input:
        BUNDLES_DIR = Path(args.input)
    run(
        server_url=args.server,
        workers=args.workers,
        timeout=args.timeout,
        dry_run=args.dry_run,
        resume=args.resume,
        limit=args.limit,
    )
