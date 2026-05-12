"""Artifact: Windows Defender Logs — scan history and support logs."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "defender_logs"
BASE = os.environ.get("ProgramData", r"C:\ProgramData")
SOURCE_DIRS = [
    os.path.join(BASE, "Microsoft", "Windows Defender", "Scans", "History"),
    os.path.join(BASE, "Microsoft", "Windows Defender", "Support"),
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for src_dir in SOURCE_DIRS:
        if not os.path.isdir(src_dir):
            continue
        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                path = os.path.join(root, fname)
                sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
