"""Artifact: Firefox History — browsing history via SQLite."""
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.timestamp_utils import firefox_time_to_epoch_ms
from ..core.system_utils import find_browser_profiles
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "firefox_history"
QUERY = (
    "SELECT id, url, title, rev_host, visit_count, hidden, typed, last_visit_date "
    "FROM moz_places"
)
CONVERT = {"last_visit_date": firefox_time_to_epoch_ms, "hidden": bool, "typed": bool}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for db in find_browser_profiles(
        "~/Library/Application Support/Firefox/Profiles", "places.sqlite"
    ):
        sources.extend(copy_sqlite_db(db, collector))
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
