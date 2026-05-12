"""Artifact: Environment Variables — current process env + per-user plists."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "environment_vars"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in expand_user_paths("~/Library/Preferences/.MacOSX/environment.plist"):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    # Current process environment
    for key, value in os.environ.items():
        result.add_entry({"source": "process", "key": key, "value": value})

    # Per-user environment plists
    for sf in sources:
        plist = read_plist(sf["path"])
        if isinstance(plist, dict):
            for key, value in plist.items():
                result.add_entry({
                    "source": sf["path"],
                    "key": key,
                    "value": str(value),
                })
    return result
