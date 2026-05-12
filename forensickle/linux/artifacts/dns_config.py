"""Artifact: DNS Config — parse /etc/resolv.conf."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "dns_config"


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file("/etc/resolv.conf")
    return [entry] if entry else []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    try:
        with open("/etc/resolv.conf", "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                result.add_entry({
                    "line_number": i,
                    "directive": parts[0],
                    "value": parts[1] if len(parts) > 1 else "",
                })
    except OSError:
        pass
    return result
