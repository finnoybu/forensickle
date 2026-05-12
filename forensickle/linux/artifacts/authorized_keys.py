"""Artifact: SSH Authorized Keys — for all users."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import get_users, get_file_owner

log = logging.getLogger(__name__)
NAME = "authorized_keys"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for user in get_users():
        path = f"{user['home']}/.ssh/authorized_keys"
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        owner = get_file_owner(sf["path"])
        try:
            with open(sf["path"], "r") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(None, 2)
                    result.add_entry({
                        "user": owner,
                        "file": sf["path"],
                        "line_number": i,
                        "key_type": parts[0] if parts else "",
                        "key_data": parts[1] if len(parts) > 1 else "",
                        "comment": parts[2] if len(parts) > 2 else "",
                    })
        except OSError:
            continue
    return result
