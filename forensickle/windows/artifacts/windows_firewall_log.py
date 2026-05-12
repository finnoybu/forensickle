"""Artifact: Windows Firewall Log — collect pfirewall.log."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "windows_firewall_log"
SOURCE_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                           "System32", "LogFiles", "Firewall", "pfirewall.log")


def collect(collector: SourceCollector) -> list[dict]:
    if os.path.isfile(SOURCE_PATH):
        return [collector.collect_file(SOURCE_PATH)]
    return []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
