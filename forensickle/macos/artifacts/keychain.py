"""Artifact: Keychain — keychain database files (encrypted, collected only)."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "keychain"
SYSTEM_PATHS = ["/Library/Keychains/*"]
USER_PATHS = ["~/Library/Keychains/*"]


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
    """Collect keychain files. No parsing — contents are encrypted."""
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
