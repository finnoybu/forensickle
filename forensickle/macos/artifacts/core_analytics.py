"""Artifact: CoreAnalytics — diagnostic reports from CoreAnalytics files."""
import glob
import json
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "core_analytics"
CA_PATTERN = "/Library/Logs/DiagnosticReports/*.core_analytics"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob(CA_PATTERN):
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
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        data = json.loads(stripped)
                        data["_source_file"] = sf["path"]
                        result.add_entry(data)
                    except (ValueError, TypeError):
                        continue
        except OSError as e:
            log.error("Cannot read CoreAnalytics file %s: %s", sf["path"], e)
    return result
