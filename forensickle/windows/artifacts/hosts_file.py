"""Artifact: Hosts File — parse system hosts file for suspicious entries."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "hosts_file"
SOURCE_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                           "System32", "drivers", "etc", "hosts")


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
            with open(sf["path"], "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    parts = stripped.split()
                    if len(parts) >= 2:
                        result.add_entry({
                            "line": line_num,
                            "ip": parts[0],
                            "hostnames": parts[1:],
                            "raw": stripped,
                        })
        except OSError as e:
            log.error("Failed to read hosts file %s: %s", sf["path"], e)
    return result
