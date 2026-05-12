"""Artifact: Open Files — lsof output."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "open_files"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    output = run_command(["lsof", "-nP"], timeout=60)
    lines = output.strip().splitlines()
    if len(lines) < 2:
        return result
    for line in lines[1:]:
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue
        result.add_entry({
            "command": parts[0],
            "pid": parts[1],
            "user": parts[2],
            "fd": parts[3],
            "type": parts[4],
            "device": parts[5],
            "size_off": parts[6],
            "node": parts[7],
            "name": parts[8],
        })
    return result
