"""Artifact: Cron Jobs — scheduled tasks from crontab files."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "cron_jobs"
CRON_PATHS = [
    "/etc/crontab",
    "/var/at/tabs/*",
    "/usr/lib/cron/tabs/*",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in CRON_PATHS:
        for path in glob.glob(pattern):
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    return sources


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
                    parts = stripped.split(None, 5)
                    if len(parts) >= 6:
                        result.add_entry({
                            "source_path": sf["path"],
                            "line_number": line_no,
                            "minute": parts[0],
                            "hour": parts[1],
                            "day": parts[2],
                            "month": parts[3],
                            "weekday": parts[4],
                            "command": parts[5],
                            "raw": stripped,
                        })
                    else:
                        result.add_entry({
                            "source_path": sf["path"],
                            "line_number": line_no,
                            "raw": stripped,
                        })
        except OSError as e:
            log.error("Cannot read cron file %s: %s", sf["path"], e)
    return result
