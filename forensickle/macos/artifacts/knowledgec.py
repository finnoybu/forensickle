"""Artifact: KnowledgeC — app usage and activity from knowledgeC.db."""
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.timestamp_utils import safari_coredata_to_epoch_ms
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "knowledgec"
DB_PATTERN = "~/Library/Application Support/Knowledge/knowledgeC.db"
QUERY = (
    "SELECT ZOBJECT.ZVALUESTRING AS app_name, "
    "ZOBJECT.ZSTARTDATE AS start_time, "
    "ZOBJECT.ZENDDATE AS end_time, "
    "ZOBJECT.ZSECONDSFROMGMT AS seconds_from_gmt, "
    "(ZOBJECT.ZENDDATE - ZOBJECT.ZSTARTDATE) AS duration, "
    "ZOBJECT.ZSTREAMNAME AS stream_name "
    "FROM ZOBJECT "
    "WHERE ZVALUESTRING IS NOT NULL "
    "ORDER BY ZSTARTDATE DESC"
)
CONVERT = {
    "start_time": safari_coredata_to_epoch_ms,
    "end_time": safari_coredata_to_epoch_ms,
}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in expand_user_paths(DB_PATTERN):
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
