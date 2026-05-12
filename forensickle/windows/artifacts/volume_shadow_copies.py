"""Artifact: Volume Shadow Copies — list available VSCs via vssadmin."""
import logging
import re
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "volume_shadow_copies"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # No files to collect; information is gathered live


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    try:
        out = subprocess.run(
            ["vssadmin", "list", "shadows"],
            capture_output=True, text=True, timeout=30, creationflags=_NO_WINDOW,
        )
        block = {}
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith("Shadow Copy Volume:"):
                block["volume"] = line.split(":", 1)[1].strip()
            elif line.startswith("Shadow Copy ID:"):
                block["shadow_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("Original Volume:"):
                block["original_volume"] = line.split(":", 1)[1].strip()
            elif line.startswith("Shadow Copy Set ID:"):
                block["set_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("Creation date:") or line.startswith("Contained"):
                # End of a block
                if block:
                    m = re.search(r"Creation date:\s*(.*)", line)
                    if m:
                        block["creation_date"] = m.group(1).strip()
            elif not line and block:
                result.add_entry(block)
                block = {}
        if block:
            result.add_entry(block)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log.error("Failed to list VSCs: %s", e)
    return result
