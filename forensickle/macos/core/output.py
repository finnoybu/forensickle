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
) -> str:
    """Writes the standard result JSON file. Returns file path."""
    if parse_time is None:
        parse_time = epoch_ms_now()

    result = {
        artifact_name: {
            "data": {"entries": entries},
            "parse_time": parse_time,
            "source_files": source_files,
        }
    }

    path = os.path.join(results_dir, f"{artifact_name}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
    except OSError as e:
        log.error("Failed to write result %s: %s", path, e)
    return path


class ResultBuilder:
    """Accumulates entries and source_files, then writes via save()."""

    def __init__(self, artifact_name: str):
        self.artifact_name = artifact_name
        self.entries: list[dict] = []
        self.source_files: list[dict] = []

    def add_entry(self, entry: dict) -> None:
        self.entries.append(entry)

    def add_entries(self, entries: list[dict]) -> None:
        self.entries.extend(entries)

    def add_source(self, source: dict) -> None:
        self.source_files.append(source)

    def add_sources(self, sources: list[dict]) -> None:
        self.source_files.extend(sources)

    def save(self, results_dir: str, parse_time: int | None = None) -> str:
        return write_result(
            results_dir, self.artifact_name,
            self.entries, self.source_files, parse_time
        )
