"""Artifact: Unified Log — macOS unified log via `log show` command."""
import logging

from ..core.collector import SourceCollector
from ..core.system_utils import run_command
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "unified_log"
DEFAULT_MINUTES = 60


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector, minutes: int = DEFAULT_MINUTES) -> dict:
    result = ResultBuilder(NAME)
    output = run_command(
        ["log", "show", "--last", f"{minutes}m", "--style", "ndjson"],
        timeout=120,
    )
    if not output:
        # Fallback to compact style if ndjson unavailable
        output = run_command(
            ["log", "show", "--last", f"{minutes}m", "--style", "compact"],
            timeout=120,
        )

    if not output:
        log.warning("No unified log output collected")
        return result

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Try JSON parse first (ndjson style)
        try:
            import json
            entry = json.loads(stripped)
            result.add_entry(entry)
        except (ValueError, TypeError):
            # Compact text line — store raw
            result.add_entry({"raw": stripped})
    return result
