"""Artifact: Launch Daemons — persistence via system-level launchd plists."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "launch_daemons"
SYSTEM_PATHS = [
    "/Library/LaunchDaemons/*.plist",
    "/System/Library/LaunchDaemons/*.plist",
]

PLIST_KEYS = [
    "Label", "ProgramArguments", "Program", "RunAtLoad",
    "StartInterval", "StartCalendarInterval", "KeepAlive",
    "WatchPaths", "QueueDirectories",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    paths = set()
    for pattern in SYSTEM_PATHS:
        paths.update(glob.glob(pattern))
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
