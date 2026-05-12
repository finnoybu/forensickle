"""Artifact: Third-Party AV Logs — Malwarebytes, McAfee, AVG, Avast, Kaspersky, Sophos, Trend Micro."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "av_logs"
PD = os.environ.get("ProgramData", r"C:\ProgramData")
PF = os.environ.get("ProgramFiles", r"C:\Program Files")
PFX = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
SOURCE_PATTERNS = [
    os.path.join(PD, "Malwarebytes", "Malwarebytes Anti-Malware", "Logs", "*"),
    os.path.join(PD, "McAfee", "**", "*.log"),
    os.path.join(PD, "AVG", "**", "*.log"),
    os.path.join(PD, "Avast Software", "**", "*.log"),
    os.path.join(PD, "Kaspersky Lab", "**", "*.log"),
    os.path.join(PF, "Sophos", "**", "*.log"),
    os.path.join(PFX, "Trend Micro", "**", "*.log"),
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
    return result
