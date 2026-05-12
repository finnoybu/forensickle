"""Artifact: Cron Jobs — system and user crontabs."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import get_users

log = logging.getLogger(__name__)
NAME = "cron_jobs"
SYSTEM_PATHS = ["/etc/crontab"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for p in SYSTEM_PATHS:
        entry = collector.collect_file(p)
        if entry:
            sources.append(entry)
    for p in glob.glob("/etc/cron.d/*"):
        entry = collector.collect_file(p)
        if entry:
            sources.append(entry)
    for p in glob.glob("/var/spool/cron/crontabs/*"):
        entry = collector.collect_file(p)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            with open(sf["path"], "r") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    result.add_entry({"source_file": sf["path"], "line_number": i,
                                      "content": line})
        except OSError:
            continue
    return result
