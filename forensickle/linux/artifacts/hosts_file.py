"""Artifact: Hosts File — parse /etc/hosts."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "hosts_file"


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file("/etc/hosts")
    return [entry] if entry else []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    try:
        with open("/etc/hosts", "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                result.add_entry({
                    "line_number": i,
                    "ip": parts[0],
                    "hostnames": parts[1:],
                })
    except OSError:
        pass
    return result
