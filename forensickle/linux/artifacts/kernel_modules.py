"""Artifact: Kernel Modules — loaded modules from /proc/modules plus modinfo."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "kernel_modules"


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file("/proc/modules")
    return [entry] if entry else []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    try:
        with open("/proc/modules", "r") as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                mod_name = parts[0]
                info = run_command(["modinfo", "-F", "description", mod_name]).strip()
                result.add_entry({
                    "name": mod_name,
                    "size": int(parts[1]) if len(parts) > 1 else 0,
                    "used_by": parts[3].rstrip(",") if len(parts) > 3 else "",
                    "state": parts[4] if len(parts) > 4 else "",
                    "description": info,
                })
    except OSError:
        pass
    return result
