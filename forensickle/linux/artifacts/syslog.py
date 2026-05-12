"""Artifact: Syslog — parse /var/log/syslog or /var/log/messages."""
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "syslog"
LOG_PATHS = ["/var/log/syslog", "/var/log/messages"]
SYSLOG_RE = re.compile(
    r'^(\w+\s+\d+\s+[\d:]+)\s+(\S+)\s+(\S+?)(?:\[\d+\])?:\s+(.*)')


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in LOG_PATHS:
        if os.path.isfile(path):
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            with open(sf["path"], "r", errors="replace") as f:
                for line in f:
                    m = SYSLOG_RE.match(line)
                    if not m:
                        continue
                    result.add_entry({
                        "timestamp_raw": m.group(1),
                        "hostname": m.group(2),
                        "service": m.group(3),
                        "message": m.group(4),
                        "source_file": sf["path"],
                    })
        except OSError:
            continue
    return result
