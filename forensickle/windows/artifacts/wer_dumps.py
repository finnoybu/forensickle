"""Artifact: WER Dumps — Windows Error Reporting files."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "wer_dumps"
SOURCE_DIR = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                          "Microsoft", "Windows", "WER")


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for root, _dirs, files in os.walk(SOURCE_DIR):
        for fname in files:
            path = os.path.join(root, fname)
            sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
