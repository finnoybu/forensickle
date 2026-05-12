"""Artifact: RecentFileCache.bcf — program execution evidence."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "recentfilecache"
SOURCE_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                           "AppCompat", "Programs", "RecentFileCache.bcf")


def collect(collector: SourceCollector) -> list[dict]:
    if os.path.isfile(SOURCE_PATH):
        return [collector.collect_file(SOURCE_PATH)]
    return []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            with open(sf["path"], "rb") as f:
                header = f.read(4)  # Skip signature
                data = f.read()
            # Entries are null-terminated UTF-16LE strings preceded by 4-byte length
            pos = 0
            while pos < len(data) - 4:
                length = int.from_bytes(data[pos:pos + 4], "little")
                pos += 4
                if length <= 0 or pos + length * 2 > len(data):
                    break
                raw = data[pos:pos + length * 2]
                path = raw.decode("utf-16-le", errors="replace").rstrip("\x00")
                pos += length * 2
                if path:
                    result.add_entry({"path": path})
        except OSError as e:
            log.error("Failed to parse RecentFileCache.bcf: %s", e)
    return result
