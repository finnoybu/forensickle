"""Artifact: USN Journal — $UsnJrnl:$J from system drive."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "usn_journal"
SOURCE_PATH = os.path.join(os.environ.get("SystemDrive", "C:") + os.sep,
                           "$Extend", "$UsnJrnl:$J")


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file(SOURCE_PATH, source_type="ntfs_artifact")
    return [entry] if entry else []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
