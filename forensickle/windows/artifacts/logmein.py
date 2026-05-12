"""Artifact: LogMeIn — remote access connection logs."""
import glob
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "logmein"
SOURCE_PATTERNS = [
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                 "LogMeIn", "**", "*.log"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 "LogMeIn", "**", "*.log"),
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATTERNS:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isfile(path):
                sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            with open(sf["path"], "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if re.search(r"(session|connect|auth|login|remote)", line, re.IGNORECASE):
                        result.add_entry({
                            "raw": line,
                            "source": sf["path"],
                        })
        except OSError as e:
            log.error("Failed to read LogMeIn log %s: %s", sf["path"], e)
    return result
