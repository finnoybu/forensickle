import json
import os

from .timestamp_utils import epoch_ms_now


def write_result(
    results_dir: str,
    artifact_name: str,
    entries: list[dict],
    source_files: list[dict],
    parse_time: int | None = None,
) -> str:
    """Write standard result JSON. Returns the file path."""
    result = {
        artifact_name: {
            "data": {"entries": entries},
            "parse_time": parse_time or epoch_ms_now(),
            "source_files": source_files,
        }
    }
    path = os.path.join(results_dir, f"{artifact_name}.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return path


class ResultBuilder:
    """Accumulates entries and source_files for an artifact."""

    def __init__(self, artifact_name: str):
        self.artifact_name = artifact_name
        self.entries: list[dict] = []
        self.source_files: list[dict] = []
        self._start = epoch_ms_now()

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
            results_dir, self.artifact_name, self.entries, self.source_files, self._start
        )
