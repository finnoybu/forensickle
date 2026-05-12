"""Artifact: Login Records — parse last/lastb output."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "login_records"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in ["/var/log/wtmp", "/var/log/btmp"]:
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def _parse_last_output(output: str, source: str) -> list[dict]:
    entries = []
    for line in output.strip().splitlines():
        if not line or line.startswith("wtmp") or line.startswith("btmp"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        entries.append({
            "user": parts[0],
            "terminal": parts[1],
            "host": parts[2] if not parts[2].startswith(("Mon", "Tue", "Wed",
                    "Thu", "Fri", "Sat", "Sun")) else "",
            "raw_line": line,
            "source": source,
        })
    return entries


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    result.add_entries(_parse_last_output(run_command(["last", "-F", "--no-header"]), "last"))
    result.add_entries(_parse_last_output(run_command(["lastb", "-F", "--no-header"]), "lastb"))
    return result
