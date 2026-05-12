"""Artifact: SSH Config — sshd_config and per-user ssh config files."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import get_users

log = logging.getLogger(__name__)
NAME = "ssh_config"
SSHD_CONFIG = "/etc/ssh/sshd_config"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    if os.path.isfile(SSHD_CONFIG):
        entry = collector.collect_file(SSHD_CONFIG)
        if entry:
            sources.append(entry)
    for user in get_users():
        path = os.path.join(user["home"], ".ssh", "config")
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def _parse_config(path: str) -> list[dict]:
    entries = []
    try:
        with open(path, "r", errors="replace") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    entries.append({
                        "source_file": path,
                        "line_number": i,
                        "key": parts[0],
                        "value": parts[1],
                    })
    except OSError:
        pass
    return entries


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        result.add_entries(_parse_config(sf["path"]))
    return result
