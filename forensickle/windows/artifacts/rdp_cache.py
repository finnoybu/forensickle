"""Artifact: RDP Bitmap Cache — Terminal Server Client cache files."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "rdp_cache"
PATTERN = r"%USERPROFILE%\AppData\Local\Microsoft\Terminal Server Client\Cache\*"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for expanded in expand_user_paths(PATTERN):
        for path in glob.glob(expanded):
            sources.append(collector.collect_file(path))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
