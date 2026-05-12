"""Artifact: Recent Items — recent apps, documents, places from SFL2 plists."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "recent_items"
SFL_PATTERN = "~/Library/Application Support/com.apple.sharedfilelist/*.sfl2"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in expand_user_paths(SFL_PATTERN):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    # Also try legacy .sfl files
    for path in expand_user_paths(SFL_PATTERN.replace(".sfl2", ".sfl")):
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
        if not plist:
            continue
        items = plist if isinstance(plist, list) else plist.get("$objects", [])
        for i, item in enumerate(items):
            if isinstance(item, dict):
                result.add_entry({
                    "source_path": sf["path"],
                    "index": i,
                    "data": {k: str(v) for k, v in item.items()},
                })
            elif isinstance(item, str) and item.strip():
                result.add_entry({
                    "source_path": sf["path"],
                    "index": i,
                    "value": item,
                })
    return result
