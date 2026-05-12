"""Artifact: DNS Cache — cached DNS resolver entries."""
import logging
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "dns_cache"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    try:
        out = subprocess.run(
            ["ipconfig", "/displaydns"], capture_output=True, text=True, timeout=30, creationflags=_NO_WINDOW,
        )
        entry = {}
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith("Record Name"):
                entry["record_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Record Type"):
                entry["record_type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Time To Live"):
                entry["time_to_live"] = line.split(":", 1)[1].strip()
            elif line.startswith("Data Length"):
                entry["data_length"] = line.split(":", 1)[1].strip()
            elif line.startswith("Section"):
                entry["section"] = line.split(":", 1)[1].strip()
            elif line.startswith("A (Host)") or line.startswith("AAAA") or line.startswith("CNAME"):
                entry["record"] = line.split(":", 1)[1].strip()
            elif not line and entry:
                if "record_name" in entry:
                    result.add_entry(entry)
                entry = {}
        if entry and "record_name" in entry:
            result.add_entry(entry)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log.error("Failed to run ipconfig /displaydns: %s", e)
    return result
