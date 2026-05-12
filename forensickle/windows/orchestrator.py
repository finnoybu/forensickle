"""Forensickle Windows Orchestrator — runs artifact collection and parsing."""
from __future__ import annotations

import importlib
import logging
import os
import threading
import time
from typing import Callable

from .core.collector import SourceCollector
from .core.identity import get_endpoint_info
from .profiles import all_artifact_ids, load_profile

log = logging.getLogger(__name__)

ARTIFACTS = all_artifact_ids()

# ---------------------------------------------------------------------------
# Legacy API (backward compat)
# ---------------------------------------------------------------------------

def run(working_dir: str, artifacts: list[str] | None = None,
        collect_only: bool = False, return_sources: bool = False,
        tenant_id: str = "") -> dict:
    """Run with simple flags (original API). Wraps run_config()."""
    selected = artifacts or ARTIFACTS
    if collect_only:
        config = {n: {"parse": False, "retain": True} for n in selected}
    elif return_sources:
        config = {n: {"parse": True, "retain": True} for n in selected}
    else:
        config = {n: {"parse": True, "retain": False} for n in selected}
    return run_config(working_dir, config, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Primary API
# ---------------------------------------------------------------------------

def run_config(
    working_dir: str,
    artifact_config: dict[str, dict],
    progress_callback: Callable[[str, str, int, int], None] | None = None,
    cancel_event: threading.Event | None = None,
    tenant_id: str = "",
) -> dict:
    """
    Run forensic collection with per-artifact parse/retain control.

    Args:
        working_dir: Output directory for this run.
        artifact_config: {"artifact_name": {"parse": bool, "retain": bool}, ...}
        progress_callback: Called as (artifact_name, status, current, total).
        cancel_event: Set to request cooperative cancellation.
        tenant_id: Tenant GUID (from installer config). Empty if not configured.

    Returns:
        Summary dict with per-artifact status and overall results.
    """
    # Set up file logging for this collection run
    os.makedirs(working_dir, exist_ok=True)
    _file_handler = _setup_file_logging(working_dir)

    # Build identity — stamped on every output file
    endpoint_info = get_endpoint_info()
    identity = {
        "tenant_id": tenant_id,
        **endpoint_info,
    }
    log.info("Collection identity: tenant=%s, endpoint=%s, host=%s",
             tenant_id[:8] + "..." if tenant_id else "(none)",
             endpoint_info["endpoint_id"][:12] + "...",
             endpoint_info["hostname"])

    collector = SourceCollector(working_dir, identity=identity)
    summary = {
        **identity,
        "artifacts": {},
        "source_package": None,
        "errors": [],
        "cancelled": False,
    }

    # Filter to artifacts that actually do something
    active = {k: v for k, v in artifact_config.items()
              if v.get("parse") or v.get("retain")}
    names = list(active.keys())
    total = len(names)

    # Track which artifacts want retention (for source cleanup later)
    retain_artifacts = {k for k, v in active.items() if v.get("retain")}

    for i, name in enumerate(names):
        # Check cancellation
        if cancel_event and cancel_event.is_set():
            summary["cancelled"] = True
            log.info("Collection cancelled by user")
            break

        flags = active[name]
        if progress_callback:
            progress_callback(name, "starting", i, total)

        # Import artifact module
        try:
            mod = importlib.import_module(f".artifacts.{name}", package=__package__)
        except ImportError as e:
            log.error("Artifact module not found: %s (%s)", name, e)
            summary["errors"].append({"artifact": name, "error": str(e)})
            if progress_callback:
                progress_callback(name, "error", i + 1, total)
            continue

        log.info("Processing artifact: %s (parse=%s, retain=%s)",
                 name, flags["parse"], flags["retain"])
        t0 = time.time()

        # Per-artifact log file
        art_handler = _add_artifact_log(working_dir, name)

        try:
            if flags["parse"]:
                result = mod.parse(collector)
                result.identity = identity
                result_path = result.save(collector.results_dir)
                summary["artifacts"][name] = {
                    "status": "parsed",
                    "entries": len(result.entries),
                    "source_files": len(result.source_files),
                    "result_path": result_path,
                    "duration_ms": int((time.time() - t0) * 1000),
                }
            else:
                # retain=True but parse=False: collect only
                sources = mod.collect(collector)
                summary["artifacts"][name] = {
                    "status": "collected",
                    "source_files": len(sources),
                    "duration_ms": int((time.time() - t0) * 1000),
                }

            if progress_callback:
                status = summary["artifacts"][name]["status"]
                progress_callback(name, status, i + 1, total)

        except Exception as e:
            log.error("Failed to process %s: %s", name, e, exc_info=True)
            summary["artifacts"][name] = {"status": "error", "error": str(e)}
            if progress_callback:
                progress_callback(name, "error", i + 1, total)
        finally:
            if art_handler:
                logging.getLogger().removeHandler(art_handler)
                art_handler.close()

    # Source retention: package if any artifact wants retention, cleanup otherwise
    collector.save_manifest()
    if retain_artifacts:
        try:
            summary["source_package"] = collector.package_sources()
        except Exception as e:
            log.error("Failed to package sources: %s", e)
            summary["errors"].append({"artifact": "_packaging", "error": str(e)})
    else:
        collector.cleanup_sources()

    if progress_callback:
        progress_callback("_complete", "done", total, total)

    log.info("Collection complete: %d artifacts, %d errors",
             len(summary["artifacts"]),
             len([a for a in summary["artifacts"].values() if a.get("status") == "error"]))

    # Remove file log handler
    if _file_handler:
        logging.getLogger().removeHandler(_file_handler)
        _file_handler.close()

    return summary


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_file_logging(working_dir: str):
    """Add a file handler to the root logger. Returns the handler for cleanup."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(working_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, f"collection_{ts}.log")
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    ))
    logging.getLogger().addHandler(handler)
    log.info("Log file: %s", log_path)
    return handler


def _add_artifact_log(working_dir: str, artifact_name: str):
    """Add a per-artifact log file handler. Returns the handler for cleanup."""
    log_dir = os.path.join(working_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{artifact_name}.log")
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    ))
    logging.getLogger().addHandler(handler)
    return handler


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Forensickle Windows Collector")
    import pathlib
    default_output = str(pathlib.Path.home() / "Documents" / "Forensickle")
    parser.add_argument("-o", "--output", default=default_output,
                        help="Working directory for output")
    parser.add_argument("-p", "--profile", default=None,
                        help="Built-in profile name (triage/standard/full) or path to config JSON")
    parser.add_argument("-a", "--artifacts", nargs="*",
                        help="Specific artifacts to run (default: all)")
    parser.add_argument("--collect-only", action="store_true",
                        help="Only collect source files, skip parsing")
    parser.add_argument("--return-sources", action="store_true",
                        help="Package source files for transmission")
    parser.add_argument("--list", action="store_true",
                        help="List available artifacts and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    if args.list:
        for a in ARTIFACTS:
            print(a)
        return

    os.makedirs(args.output, exist_ok=True)

    # Profile mode vs legacy mode
    if args.profile:
        artifact_config = load_profile(args.profile)
        summary = run_config(args.output, artifact_config)
    else:
        summary = run(args.output, args.artifacts, args.collect_only, args.return_sources)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
