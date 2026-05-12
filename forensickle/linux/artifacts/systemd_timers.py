"""Artifact: Systemd Timers — active timers and timer unit files."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command, expand_user_paths

log = logging.getLogger(__name__)
NAME = "systemd_timers"
TIMER_DIRS = ["/etc/systemd/system", "/lib/systemd/system", "/usr/lib/systemd/system"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for d in TIMER_DIRS:
        for path in glob.glob(f"{d}/*.timer"):
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    for path in expand_user_paths("~/.config/systemd/user/*.timer"):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    output = run_command(
        ["systemctl", "list-timers", "--all", "--no-pager", "--no-legend"]
    )
    for line in output.strip().splitlines():
        parts = line.split()
        if len(parts) >= 5:
            result.add_entry({
                "next": " ".join(parts[:3]) if len(parts) > 5 else "",
                "unit": parts[-1] if parts else "",
                "raw_line": line.strip(),
            })
    return result
