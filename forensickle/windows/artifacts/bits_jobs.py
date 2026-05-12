"""Artifact: BITS Jobs — Background Intelligent Transfer Service jobs."""
import logging
import re
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "bits_jobs"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    try:
        out = subprocess.run(
            ["bitsadmin", "/list", "/allusers", "/verbose"],
            capture_output=True, text=True, timeout=30, creationflags=_NO_WINDOW,
        )
        entry = {}
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                if entry:
                    result.add_entry(entry)
                    entry = {}
                continue
            m = re.match(r"^(GUID|DISPLAY|TYPE|STATE|OWNER|FILES|URL|LOCAL NAME|BYTES TRANSFERRED):\s*(.*)", line, re.IGNORECASE)
            if m:
                key = m.group(1).lower().replace(" ", "_")
                entry[key] = m.group(2).strip()
        if entry:
            result.add_entry(entry)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log.error("Failed to run bitsadmin: %s", e)
    return result
