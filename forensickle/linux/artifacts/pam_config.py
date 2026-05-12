"""Artifact: PAM Config — /etc/pam.d/ and /etc/pam.conf module entries."""
import glob
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "pam_config"
PAM_LINE_RE = re.compile(
    r'^(auth|account|password|session)\s+(requisite|required|sufficient|optional|include|\[.*?\])\s+(\S+)(.*)')


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob("/etc/pam.d/*"):
        if os.path.isfile(path):
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    if os.path.isfile("/etc/pam.conf"):
        entry = collector.collect_file("/etc/pam.conf")
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            with open(sf["path"], "r", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    m = PAM_LINE_RE.match(line)
                    if m:
                        result.add_entry({
                            "source_file": sf["path"],
                            "line_number": i,
                            "type": m.group(1),
                            "control": m.group(2),
                            "module": m.group(3),
                            "args": m.group(4).strip(),
                        })
        except OSError:
            continue
    return result
