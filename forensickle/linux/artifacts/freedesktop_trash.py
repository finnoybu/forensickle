"""Artifact: Freedesktop Trash — parse .trashinfo files for all users."""
import glob
import logging
import os
from configparser import ConfigParser

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import get_users, get_file_owner

log = logging.getLogger(__name__)
NAME = "freedesktop_trash"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for user in get_users():
        trash_dir = os.path.join(user["home"], ".local", "share", "Trash", "info")
        for path in glob.glob(os.path.join(trash_dir, "*.trashinfo")):
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
        try:
            cp = ConfigParser()
            cp.read(path)
            if cp.has_section("Trash Info"):
                result.add_entry({
                    "source_file": path,
                    "original_path": cp.get("Trash Info", "Path", fallback=""),
                    "deletion_date": cp.get("Trash Info", "DeletionDate", fallback=""),
                    "user": get_file_owner(path),
                })
        except (OSError, Exception) as e:
            log.debug("Failed to parse %s: %s", path, e)
    return result
