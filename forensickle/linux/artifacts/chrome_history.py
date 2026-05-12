"""Artifact: Chrome History — Chrome/Chromium browsing history on Linux."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.timestamp_utils import chrome_time_to_epoch_ms
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "chrome_history"
SOURCE_PATHS = [
    "~/.config/google-chrome/*/History",
    "~/.config/chromium/*/History",
]
QUERY = (
    "SELECT v.visit_time, v.from_visit, v.transition, "
    "u.url, u.title, u.visit_count, u.last_visit_time, u.hidden "
    "FROM visits v JOIN urls u ON v.url = u.id"
)
CONVERT = {
    "visit_time": chrome_time_to_epoch_ms,
    "last_visit_time": chrome_time_to_epoch_ms,
    "hidden": bool,
}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for path in expand_user_paths(pattern):
            sources.extend(copy_sqlite_db(path, collector))
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        if sf["path"].endswith(("-wal", "-shm")):
            continue
        rows = query_sqlite(sf["path"], QUERY)
        result.add_entries(transform_results(rows, convert=CONVERT))
    return result
