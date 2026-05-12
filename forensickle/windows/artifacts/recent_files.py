"""Artifact: Recent Files — LNK files from Recent folder with metadata."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "recent_files"
PATTERN = r"%APPDATA%\Microsoft\Windows\Recent\*.lnk"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for expanded in expand_user_paths(PATTERN):
        for path in glob.glob(expanded):
            if os.path.isfile(path):
                sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            stat = os.stat(sf["path"])
            result.add_entry({
                "filename": os.path.basename(sf["path"]),
                "path": sf["path"],
                "size": stat.st_size,
                "created": int(stat.st_ctime * 1000),
                "modified": int(stat.st_mtime * 1000),
                "accessed": int(stat.st_atime * 1000),
            })
        except OSError as e:
            log.debug("Failed to stat %s: %s", sf["path"], e)
    return result
