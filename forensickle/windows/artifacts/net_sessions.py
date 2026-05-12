"""Artifact: Net Sessions — active SMB sessions."""
import logging
import re
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "net_sessions"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    try:
        out = subprocess.run(
            ["net", "session"], capture_output=True, text=True, timeout=15, creationflags=_NO_WINDOW,
        )
        lines = out.stdout.splitlines()
        header_found = False
        for line in lines:
            if "---" in line:
                header_found = True
                continue
            if not header_found or not line.strip():
                continue
            if line.startswith("The command completed"):
                break
            parts = line.split()
            if len(parts) >= 3:
                result.add_entry({
                    "computer": parts[0],
                    "user": parts[1],
                    "client_type": parts[2] if len(parts) > 2 else None,
                    "open_files": parts[3] if len(parts) > 3 else None,
                    "idle_time": parts[4] if len(parts) > 4 else None,
                })
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log.error("Failed to run net session: %s", e)
    return result
