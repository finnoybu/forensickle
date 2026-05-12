from __future__ import annotations

import json
import logging
import os

from .timestamp_utils import epoch_ms_now

log = logging.getLogger(__name__)


def write_result(
    results_dir: str,
    artifact_name: str,
    entries: list[dict],
    source_files: list[dict],
    parse_time: int | None = None,
    identity: dict | None = None,
) -> str:
    """Write standard result JSON with identity stamped. Returns file path."""
    if parse_time is None:
        parse_time = epoch_ms_now()

    result = {
        artifact_name: {
            **(identity or {}),
            "data": {"entries": entries},
            "parse_time": parse_time,
            "source_files": source_files,
        }
    }

    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, f"{artifact_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("Wrote result: %s (%d entries)", path, len(entries))
    return path


class ResultBuilder:
    """Accumulate entries and source files, then write as standard result JSON."""

    def __init__(self, artifact_name: str, identity: dict | None = None):
        self.artifact_name = artifact_name
        self.identity = identity or {}
        self.entries: list[dict] = []
        self.source_files: list[dict] = []
        self._start_time = epoch_ms_now()

    def add_entry(self, entry: dict) -> None:
        self.entries.append(entry)

    def add_entries(self, entries: list[dict]) -> None:
        self.entries.extend(entries)

    def add_source(self, source: dict) -> None:
        self.source_files.append(source)

    def add_sources(self, sources: list[dict]) -> None:
        self.source_files.extend(sources)

    def save(self, results_dir: str) -> str:
        return write_result(
            results_dir,
            self.artifact_name,
            self.entries,
            self.source_files,
            parse_time=self._start_time,
            identity=self.identity,
        )
