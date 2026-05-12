"""Artifact: $MFT — Master File Table from system drive root."""
import logging
import os
import tempfile

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "mft"
SOURCE_PATH = os.path.join(os.environ.get("SystemDrive", "C:"), os.sep, "$MFT")


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    dest = os.path.join(tempfile.gettempdir(), "forensickle_mft")
    try:
        collector.raw_copy(SOURCE_PATH, dest)
        sources.append({"path": dest, "original_path": SOURCE_PATH})
    except OSError as e:
        log.error("Failed to raw-copy $MFT: %s", e)
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
