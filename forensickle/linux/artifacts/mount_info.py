"""Artifact: Mount Info — parse /proc/mounts and /etc/fstab."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "mount_info"
SOURCE_FILES = ["/proc/mounts", "/etc/fstab"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in SOURCE_FILES:
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def _parse_mount_line(line: str, source: str) -> dict | None:
    parts = line.split()
    if len(parts) < 4:
        return None
    return {
        "device": parts[0],
        "mount_point": parts[1],
        "fs_type": parts[2],
        "options": parts[3],
        "source": source,
    }


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    for path in SOURCE_FILES:
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    entry = _parse_mount_line(line, path)
                    if entry:
                        result.add_entry(entry)
        except OSError:
            continue
    return result
