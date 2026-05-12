"""Artifact: Spotlight Shortcuts — Spotlight search shortcuts from user prefs."""
import logging

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "spotlight_shortcuts"
PLIST_PATTERNS = [
    "~/Library/Preferences/com.apple.Spotlight.plist",
    "~/Library/Preferences/com.apple.spotlight.plist",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in PLIST_PATTERNS:
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
        plist = read_plist(sf["path"])
        if not isinstance(plist, dict):
            continue
        shortcuts = plist.get("UserShortcuts", plist.get("shortcuts", {}))
        if isinstance(shortcuts, dict):
            for key, value in shortcuts.items():
                result.add_entry({
                    "source_path": sf["path"],
                    "shortcut": key,
                    "value": str(value),
                })
        # Also capture ordering preferences
        for pref_key in ("orderedItems", "CategoryOrder"):
            if pref_key in plist:
                result.add_entry({
                    "source_path": sf["path"],
                    "preference": pref_key,
                    "value": str(plist[pref_key]),
                })
    return result
