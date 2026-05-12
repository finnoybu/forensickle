"""Artifact: TeamViewer — remote access connection logs."""
import glob
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "teamviewer"
SOURCE_PATHS = [
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                 "TeamViewer", "Connections_incoming.txt"),
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                 "TeamViewer", "TeamViewer*_Logfile.log"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 "TeamViewer", "Connections_incoming.txt"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 "TeamViewer", "TeamViewer*_Logfile.log"),
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for path in glob.glob(pattern):
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
                    if "Connections_incoming" in sf["path"]:
                        # Tab-separated: ID DisplayName DateTime DateTime
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            result.add_entry({
                                "type": "incoming_connection",
                                "remote_id": parts[0].strip(),
                                "display_name": parts[1].strip() if len(parts) > 1 else None,
                                "start_time": parts[2].strip() if len(parts) > 2 else None,
                                "end_time": parts[3].strip() if len(parts) > 3 else None,
                                "source": sf["path"],
                            })
                    else:
                        # Log files: extract connection-related entries
                        if re.search(r"(punch|connection|session|authenticate)", line, re.IGNORECASE):
                            result.add_entry({"type": "log", "raw": line, "source": sf["path"]})
        except OSError as e:
            log.error("Failed to read TeamViewer log %s: %s", sf["path"], e)
    return result
