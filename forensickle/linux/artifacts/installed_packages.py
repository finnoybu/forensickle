"""Artifact: Installed Packages — dpkg and rpm package lists."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "installed_packages"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    entry = collector.collect_file("/var/lib/dpkg/status")
    if entry:
        sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    # dpkg
    dpkg_out = run_command(["dpkg", "-l"], timeout=30)
    for line in dpkg_out.splitlines():
        if not line.startswith("ii"):
            continue
        parts = line.split(None, 4)
        if len(parts) >= 4:
            result.add_entry({
                "manager": "dpkg", "name": parts[1], "version": parts[2],
                "arch": parts[3], "description": parts[4] if len(parts) > 4 else "",
            })
    # rpm
    rpm_out = run_command(["rpm", "-qa", "--queryformat",
                           "%{NAME}\\t%{VERSION}-%{RELEASE}\\t%{ARCH}\\n"], timeout=30)
    for line in rpm_out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            result.add_entry({
                "manager": "rpm", "name": parts[0], "version": parts[1],
                "arch": parts[2], "description": "",
            })
    return result
