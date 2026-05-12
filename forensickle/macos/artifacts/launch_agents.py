"""Artifact: Launch Agents/Daemons — persistence via launchd plists."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "launch_agents"
SYSTEM_PATHS = [
    "/Library/LaunchAgents/*.plist",
    "/Library/LaunchDaemons/*.plist",
    "/System/Library/LaunchAgents/*.plist",
    "/System/Library/LaunchDaemons/*.plist",
]
USER_PATHS = ["~/Library/LaunchAgents/*.plist"]

PLIST_KEYS = [
    "Label", "ProgramArguments", "Program", "RunAtLoad",
    "StartInterval", "StartCalendarInterval", "KeepAlive",
    "WatchPaths", "QueueDirectories", "EnvironmentVariables",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    paths = set()
    for pattern in SYSTEM_PATHS:
        paths.update(glob.glob(pattern))
    for pattern in USER_PATHS:
        paths.update(expand_user_paths(pattern))
    for path in sorted(paths):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    for sf in sources:
        plist = read_plist(sf["path"])
        if not isinstance(plist, dict):
            continue
        entry = {"source_path": sf["path"]}
        for key in PLIST_KEYS:
            if key in plist:
                val = plist[key]
                entry[key.lower()] = val if not isinstance(val, bytes) else val.hex()
        result.add_entry(entry)
    return result
