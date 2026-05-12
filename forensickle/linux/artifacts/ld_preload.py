"""Artifact: LD Preload — /etc/ld.so.preload entries (persistence indicator)."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "ld_preload"
PRELOAD_PATH = "/etc/ld.so.preload"


def collect(collector: SourceCollector) -> list[dict]:
    if os.path.isfile(PRELOAD_PATH):
        entry = collector.collect_file(PRELOAD_PATH)
        return [entry] if entry else []
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    if not os.path.isfile(PRELOAD_PATH):
        result.add_entry({"status": "file_not_found", "libraries": []})
        return result
    try:
        with open(PRELOAD_PATH, "r") as f:
            libraries = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    libraries.append(line)
        result.add_entry({
            "status": "present" if libraries else "empty",
            "libraries": libraries,
            "critical": len(libraries) > 0,
        })
    except OSError:
        result.add_entry({"status": "read_error", "libraries": []})
    return result
