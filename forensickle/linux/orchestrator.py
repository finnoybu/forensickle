"""Forensickle Linux Orchestrator — runs artifact collection and parsing."""
import importlib
import logging
import os
import time

from .core.collector import SourceCollector

log = logging.getLogger(__name__)

ARTIFACTS = [
    "process_list", "network_connections", "environment_vars", "system_info",
    "systemd_services", "cron_jobs", "authorized_keys", "known_hosts",
    "shell_history", "shell_configs", "login_records",
    "hosts_file", "dns_config", "mount_info", "kernel_modules",
    "auditd", "auth_log",
    "installed_packages", "firewall_rules",
    "open_files",
]


def run(working_dir: str, artifacts: list[str] | None = None,
        collect_only: bool = False, return_sources: bool = False) -> dict:
    selected = artifacts or ARTIFACTS
    collector = SourceCollector(working_dir)
    summary = {"artifacts": {}, "source_package": None, "errors": []}

    for name in selected:
        try:
            mod = importlib.import_module(f".artifacts.{name}", package=__package__)
        except ImportError as e:
            log.error("Artifact module not found: %s (%s)", name, e)
            summary["errors"].append({"artifact": name, "error": str(e)})
            continue

        log.info("Processing artifact: %s", name)
        t0 = time.time()

        try:
            if collect_only:
                sources = mod.collect(collector)
                summary["artifacts"][name] = {
                    "status": "collected",
                    "source_files": len(sources),
                    "duration_ms": int((time.time() - t0) * 1000),
                }
            else:
                result = mod.parse(collector)
                result_path = result.save(collector.results_dir)
                summary["artifacts"][name] = {
                    "status": "parsed",
                    "entries": len(result.entries),
                    "source_files": len(result.source_files),
                    "result_path": result_path,
                    "duration_ms": int((time.time() - t0) * 1000),
                }
        except Exception as e:
            log.error("Failed to process %s: %s", name, e, exc_info=True)
            summary["artifacts"][name] = {"status": "error", "error": str(e)}

    collector.save_manifest()
    if return_sources:
        try:
            summary["source_package"] = collector.package_sources()
        except Exception as e:
            log.error("Failed to package sources: %s", e)
            summary["errors"].append({"artifact": "_packaging", "error": str(e)})
    else:
        collector.cleanup_sources()

    return summary


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Forensickle Linux Collector")
    import pathlib
    default_output = str(pathlib.Path.home() / "Forensickle")
    parser.add_argument("-o", "--output", default=default_output)
    parser.add_argument("-a", "--artifacts", nargs="*")
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--return-sources", action="store_true")
    parser.add_argument("--list", action="store_true")
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
    summary = run(args.output, args.artifacts, args.collect_only, args.return_sources)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
