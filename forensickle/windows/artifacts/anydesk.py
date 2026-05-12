"""Artifact: AnyDesk — remote access connection traces and logs."""
import glob
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "anydesk"
SOURCE_PATHS = [
    os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "AnyDesk", "ad_svc.trace"),
    r"%APPDATA%\AnyDesk\ad.trace",
    r"%APPDATA%\AnyDesk\connection_trace.txt",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        paths = expand_user_paths(pattern) if "%" in pattern else [pattern]
        for expanded in paths:
            for path in glob.glob(expanded):
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
                    # connection_trace.txt has structured connection entries
                    if "connection_trace" in sf["path"]:
                        result.add_entry({"type": "connection_trace", "raw": line, "source": sf["path"]})
                    else:
                        # Trace logs: look for connection-related lines
                        if re.search(r"(Logged in|Connection|Incoming|Accept|Reject)", line, re.IGNORECASE):
                            result.add_entry({"type": "trace", "raw": line, "source": sf["path"]})
        except OSError as e:
            log.error("Failed to read AnyDesk log %s: %s", sf["path"], e)
    return result
