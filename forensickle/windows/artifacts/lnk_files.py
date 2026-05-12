"""Artifact: LNK Files — Windows shortcut files from Recent folder."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "lnk_files"
SOURCE_PATHS = [r"%APPDATA%\Microsoft\Windows\Recent\*.lnk"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for expanded in expand_user_paths(pattern):
            for path in glob.glob(expanded):
                sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    # LNK binary parsing requires shell link header interpretation
    log.warning("LNK binary parsing not yet implemented; collected %d source files", len(sources))
    return result
