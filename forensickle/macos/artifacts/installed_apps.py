"""Artifact: Installed Apps — applications from /Applications and ~/Applications."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.system_utils import get_users, get_file_metadata
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "installed_apps"
APP_DIRS = ["/Applications"]


def _scan_apps(base_dir: str) -> list[str]:
    """Find .app bundles in a directory (non-recursive)."""
    results = []
    try:
        for entry in os.scandir(base_dir):
            if entry.is_dir() and entry.name.endswith(".app"):
                results.append(entry.path)
    except OSError:
        pass
    return results


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    app_dirs = list(APP_DIRS)
    for user in get_users():
        user_apps = os.path.join(user["home"], "Applications")
        if os.path.isdir(user_apps):
            app_dirs.append(user_apps)

    for app_dir in app_dirs:
        for app_path in _scan_apps(app_dir):
            plist_path = os.path.join(app_path, "Contents", "Info.plist")
            if os.path.isfile(plist_path):
                entry = collector.collect_file(plist_path)
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
        # Derive app path from Info.plist location
        app_path = os.path.dirname(os.path.dirname(sf["path"]))
        meta = get_file_metadata(app_path)
        result.add_entry({
            "name": plist.get("CFBundleName", os.path.basename(app_path)),
            "path": app_path,
            "bundle_id": plist.get("CFBundleIdentifier"),
            "version": plist.get("CFBundleShortVersionString"),
            "build": plist.get("CFBundleVersion"),
            "min_os": plist.get("LSMinimumSystemVersion"),
            "created_ms": meta.get("created_ms"),
            "modified_ms": meta.get("modified_ms"),
        })
    return result
