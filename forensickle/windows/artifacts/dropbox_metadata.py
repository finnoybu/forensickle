"""Artifact: Dropbox Metadata — config and sync metadata."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "dropbox_metadata"
PATTERNS = [
    r"%APPDATA%\Dropbox",
    r"%LOCALAPPDATA%\Dropbox",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in PATTERNS:
        for expanded in expand_user_paths(pattern):
            if not os.path.isdir(expanded):
                continue
            for root, _dirs, files in os.walk(expanded):
                for fname in files:
                    path = os.path.join(root, fname)
                    sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
