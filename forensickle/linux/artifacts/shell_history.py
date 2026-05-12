"""Artifact: Shell History — bash and zsh history for all users."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import get_users, get_file_owner

log = logging.getLogger(__name__)
NAME = "shell_history"
HISTORY_FILES = [".bash_history", ".zsh_history"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for user in get_users():
        for hist_name in HISTORY_FILES:
            path = os.path.join(user["home"], hist_name)
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        path = sf["path"]
        owner = get_file_owner(path)
        shell_type = "zsh" if "zsh" in path else "bash"
        try:
            with open(path, "r", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    result.add_entry({
                        "user": owner,
                        "shell_type": shell_type,
                        "line_number": i,
                        "command": line,
                        "source_file": path,
                    })
        except OSError:
            continue
    return result
