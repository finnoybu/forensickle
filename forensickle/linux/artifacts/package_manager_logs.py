"""Artifact: Package Manager Logs — apt, dpkg, yum, and dnf logs."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "package_manager_logs"
LOG_PATHS = [
    "/var/log/apt/history.log",
    "/var/log/dpkg.log",
    "/var/log/yum.log",
    "/var/log/dnf.log",
]


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
        path = sf["path"]
        manager = "apt" if "apt" in path else "dpkg" if "dpkg" in path \
            else "yum" if "yum" in path else "dnf"
        try:
            with open(path, "r", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    result.add_entry({
                        "source_file": path,
                        "manager": manager,
                        "line_number": i,
                        "content": line,
                    })
        except OSError:
            continue
    return result
