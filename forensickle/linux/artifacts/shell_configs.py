"""Artifact: Shell Configs — shell configuration files for all users."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import get_users, get_file_metadata

log = logging.getLogger(__name__)
NAME = "shell_configs"
USER_CONFIGS = [".bashrc", ".bash_profile", ".zshrc", ".profile"]
SYSTEM_CONFIGS = ["/etc/profile", "/etc/bash.bashrc"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in SYSTEM_CONFIGS:
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    for user in get_users():
        for cfg in USER_CONFIGS:
            path = f"{user['home']}/{cfg}"
            entry = collector.collect_file(path)
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        meta = get_file_metadata(sf["path"])
        try:
            with open(sf["path"], "r", errors="replace") as f:
                content = f.read()
            result.add_entry({
                "path": sf["path"],
                "size": meta.get("size"),
                "modified_ms": meta.get("modified_ms"),
                "content": content,
            })
        except OSError:
            continue
    return result
