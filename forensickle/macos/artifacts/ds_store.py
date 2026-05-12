"""Artifact: .DS_Store — Finder metadata files (binary, collected only)."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "ds_store"
SYSTEM_PATHS = [
    "/Users/*/.DS_Store",
    "/Users/*/Desktop/.DS_Store",
    "/Users/*/Documents/.DS_Store",
    "/Users/*/Downloads/.DS_Store",
]
USER_PATHS = [
    "~/Desktop/.DS_Store",
    "~/Documents/.DS_Store",
    "~/Downloads/.DS_Store",
    "~/.DS_Store",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    paths = set()
    for pattern in SYSTEM_PATHS:
        paths.update(glob.glob(pattern))
    for pattern in USER_PATHS:
        paths.update(expand_user_paths(pattern))
    for path in sorted(paths):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    """Collect .DS_Store files. Parsing is stubbed — binary format."""
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        result.add_entry({"source_path": sf["path"], "note": "binary format, requires server-side parsing"})
    return result
