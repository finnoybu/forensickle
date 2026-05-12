"""Artifact: Firefox History — browsing history via SQLite."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.timestamp_utils import firefox_time_to_epoch_ms
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "firefox_history"
SOURCE_PATHS = [r"%APPDATA%\Mozilla\Firefox\Profiles\*\places.sqlite"]
QUERY = "SELECT id, url, title, rev_host, visit_count, hidden, typed, last_visit_date FROM moz_places"
CONVERT = {"last_visit_date": firefox_time_to_epoch_ms, "hidden": bool, "typed": bool}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for expanded in expand_user_paths(pattern):
            for path in glob.glob(expanded):
                sources.extend(copy_sqlite_db(path, collector))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        if sf["path"].endswith(("-wal", "-shm")):
            continue
        rows = query_sqlite(sf["path"], QUERY)
        result.add_entries(transform_results(rows, convert=CONVERT))
    return result
