"""Artifact: Environment Variables — from /proc/*/environ and /etc/environment."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "environment_vars"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    entry = collector.collect_file("/etc/environment")
    if entry:
        sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    # /etc/environment
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    result.add_entry({"source": "/etc/environment", "pid": None,
                                      "key": k.strip(), "value": v.strip().strip('"')})
    except OSError:
        pass
    # Per-process environ
    for environ_path in glob.glob("/proc/[0-9]*/environ"):
        pid = environ_path.split("/")[2]
        try:
            with open(environ_path, "r") as f:
                data = f.read()
            for pair in data.split("\0"):
                if "=" in pair:
                    k, _, v = pair.partition("=")
                    result.add_entry({"source": environ_path, "pid": int(pid),
                                      "key": k, "value": v})
        except (OSError, PermissionError):
            continue
    return result
