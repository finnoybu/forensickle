"""Artifact: System Info — uname, dmidecode, memory, kernel version."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "system_info"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in ["/proc/version", "/proc/meminfo", "/etc/os-release"]:
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    result.add_entry({
        "uname": run_command(["uname", "-a"]).strip(),
        "hostname": run_command(["hostname"]).strip(),
        "kernel_version": run_command(["uname", "-r"]).strip(),
        "os_release": run_command(["cat", "/etc/os-release"]).strip(),
        "dmidecode": run_command(["dmidecode", "-t", "system"], timeout=10).strip(),
        "meminfo": run_command(["cat", "/proc/meminfo"]).strip(),
        "uptime": run_command(["uptime"]).strip(),
    })
    return result
