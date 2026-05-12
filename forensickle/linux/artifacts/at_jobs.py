"""Artifact: At Jobs — scheduled one-time jobs from /var/spool/at/."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "at_jobs"
SPOOL_DIRS = ["/var/spool/at", "/var/spool/atjobs"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for d in SPOOL_DIRS:
        if not os.path.isdir(d):
            continue
        for path in glob.glob(f"{d}/*"):
            if os.path.isfile(path):
                entry = collector.collect_file(path)
                if entry:
                    sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        path = sf["path"]
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read(4096)
            result.add_entry({
                "name": os.path.basename(path),
                "path": path,
                "content_preview": content[:1024],
            })
        except OSError:
            continue
    return result
