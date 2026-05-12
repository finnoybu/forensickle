"""Artifact: IIS Logs — W3C log files and HTTP error logs."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "iis_logs"
SOURCE_DIRS = [
    os.path.join(os.environ.get("SystemDrive", "C:"), os.sep, "inetpub", "logs", "LogFiles"),
    os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                 "System32", "LogFiles", "HTTPERR"),
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
