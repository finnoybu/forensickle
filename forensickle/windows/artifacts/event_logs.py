"""Artifact: Event Logs — collect all EVTX files."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "event_logs"
SOURCE_DIR = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                          "System32", "winevt", "Logs")


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob(os.path.join(SOURCE_DIR, "*.evtx")):
        if os.path.isfile(path):
            sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
