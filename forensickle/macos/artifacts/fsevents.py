"""Artifact: FSEvents — file system event logs (binary, collected only)."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "fsevents"
FSEVENTSD_PATH = "/.fseventsd"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in sorted(glob.glob(f"{FSEVENTSD_PATH}/*")):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    """Collect FSEvents files. Parsing is stubbed — binary format."""
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        result.add_entry({"source_path": sf["path"], "note": "binary format, requires server-side parsing"})
    return result
