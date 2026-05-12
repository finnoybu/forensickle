"""Artifact: NTFS $LogFile — transaction log from system drive root."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "ntfs_logfile"
SOURCE_PATH = os.path.join(os.environ.get("SystemDrive", "C:") + os.sep, "$LogFile")


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file(SOURCE_PATH, source_type="ntfs_artifact")
    return [entry] if entry else []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
