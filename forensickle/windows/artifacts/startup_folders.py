"""Artifact: Startup Folders — entries from all users' Startup directories."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.hash_utils import file_hashes
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "startup_folders"
SOURCE_PATHS = [
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*",
    os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                 r"Microsoft\Windows\Start Menu\Programs\StartUp\*"),
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        paths = expand_user_paths(pattern) if "%" in pattern else [pattern]
        for expanded in paths:
            for path in glob.glob(expanded):
                if os.path.isfile(path):
                    sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        entry = {
            "path": sf["path"],
            "name": os.path.basename(sf["path"]),
            "content_hash": sf.get("content_hash"),
        }
        result.add_entry(entry)
    return result
