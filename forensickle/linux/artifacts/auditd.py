"""Artifact: Auditd — parse /var/log/audit/audit.log."""
import glob
import logging
import re

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.timestamp_utils import normalize_timestamp_ms

log = logging.getLogger(__name__)
NAME = "auditd"
FIELD_RE = re.compile(r'(\w+)=(".*?"|\S+)')


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob("/var/log/audit/audit.log*"):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def _parse_audit_line(line: str) -> dict | None:
    fields = dict(FIELD_RE.findall(line))
    # Extract type from msg=audit(ts:serial): pattern
    type_match = re.search(r'^type=(\S+)', line)
    ts_match = re.search(r'audit\((\d+\.\d+):\d+\)', line)
    if not type_match:
        return None
    entry = {"type": type_match.group(1)}
    if ts_match:
        entry["timestamp_ms"] = normalize_timestamp_ms(int(float(ts_match.group(1)) * 1000))
    for key in ("pid", "uid", "exe", "key", "success", "comm", "auid"):
        if key in fields:
            entry[key] = fields[key].strip('"')
    return entry


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            with open(sf["path"], "r", errors="replace") as f:
                for line in f:
                    entry = _parse_audit_line(line)
                    if entry:
                        result.add_entry(entry)
        except OSError:
            continue
    return result
