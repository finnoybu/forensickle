"""Artifact: Safari History — browsing history via SQLite."""
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.timestamp_utils import safari_coredata_to_epoch_ms
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "safari_history"
QUERY = (
    "SELECT hv.id, hv.visit_time, hv.title AS visit_title, "
    "hv.redirect_source, hv.redirect_destination, "
    "hi.url, hi.domain_expansion, hi.visit_count, hi.daily_visit_counts "
    "FROM history_visits hv JOIN history_items hi ON hv.history_item = hi.id"
)
CONVERT = {"visit_time": safari_coredata_to_epoch_ms}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in expand_user_paths("~/Library/Safari/History.db"):
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
