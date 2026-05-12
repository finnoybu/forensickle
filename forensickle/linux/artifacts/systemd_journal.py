"""Artifact: Systemd Journal — recent journal entries via journalctl."""
import json
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command
from ..core.timestamp_utils import normalize_timestamp_ms

log = logging.getLogger(__name__)
NAME = "systemd_journal"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    output = run_command(
        ["journalctl", "--no-pager", "-o", "json", "-n", "10000"], timeout=60
    )
    for line in output.strip().splitlines():
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_us = entry.get("__REALTIME_TIMESTAMP")
        result.add_entry({
            "timestamp_ms": normalize_timestamp_ms(int(ts_us)) if ts_us else None,
            "hostname": entry.get("_HOSTNAME", ""),
            "unit": entry.get("_SYSTEMD_UNIT", ""),
            "priority": entry.get("PRIORITY", ""),
            "message": entry.get("MESSAGE", ""),
            "pid": entry.get("_PID", ""),
        })
    return result
