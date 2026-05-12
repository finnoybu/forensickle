"""Artifact: IE/Edge Legacy History — WebCacheV01.dat via ESE."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.ese_utils import copy_ese_db, query_ese_table
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "ie_history"
SOURCE_PATHS = [r"%LOCALAPPDATA%\Microsoft\Windows\WebCache\WebCacheV01.dat"]
TABLE = "Containers"
HISTORY_TABLE_PREFIX = "Container_"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for expanded in expand_user_paths(pattern):
            if os.path.isfile(expanded):
                sources.extend(copy_ese_db(expanded, collector))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        # First get container directory to find history tables
        containers = query_ese_table(sf["path"], TABLE, ["ContainerId", "Name", "Directory"])
        for c in containers:
            name = c.get("Name", "")
            if name and "History" in str(name):
                table_name = f"{HISTORY_TABLE_PREFIX}{c.get('ContainerId', '')}"
                rows = query_ese_table(sf["path"], table_name,
                                       ["Url", "AccessedTime", "ModifiedTime", "ExpiryTime"])
                result.add_entries(rows)
    return result
