"""Artifact: Hosts File — parse /etc/hosts."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "hosts_file"
HOSTS_PATH = "/etc/hosts"


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file(HOSTS_PATH)
    return [entry] if entry else []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    for sf in sources:
        try:
            with open(sf["path"], "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    parts = stripped.split()
                    ip = parts[0]
                    for hostname in parts[1:]:
                        if hostname.startswith("#"):
                            break
                        result.add_entry({
                            "ip": ip,
                            "hostname": hostname,
                            "line_number": line_no,
                            "source": sf["path"],
                        })
        except OSError as e:
            log.error("Cannot read hosts file %s: %s", sf["path"], e)
    return result
