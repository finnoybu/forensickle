"""Artifact: Systemd Services — unit files and their status."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "systemd_services"
UNIT_DIRS = ["/etc/systemd/system", "/lib/systemd/system", "/usr/lib/systemd/system"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for d in UNIT_DIRS:
        for path in glob.glob(f"{d}/*.service"):
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    # Parse systemctl list-unit-files
    output = run_command(["systemctl", "list-unit-files", "--type=service", "--no-pager",
                          "--no-legend"])
    for line in output.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result.add_entry({"unit": parts[0], "state": parts[1],
                              "preset": parts[2] if len(parts) > 2 else ""})
    return result
