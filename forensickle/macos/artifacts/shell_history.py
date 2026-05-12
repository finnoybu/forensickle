"""Artifact: Shell History — bash and zsh history for all users."""
import logging

from ..core.collector import SourceCollector
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "shell_history"
HISTORY_FILES = [
    "~/.bash_history",
    "~/.zsh_history",
    "~/.sh_history",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in HISTORY_FILES:
        for path in expand_user_paths(pattern):
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    for sf in sources:
        try:
            with open(sf["path"], "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, 1):
                    stripped = line.rstrip("\n")
                    if not stripped:
                        continue
                    result.add_entry({
                        "source_path": sf["path"],
                        "line_number": line_no,
                        "command": stripped,
                    })
        except OSError as e:
            log.error("Cannot read history file %s: %s", sf["path"], e)
    return result
