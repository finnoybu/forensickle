"""Artifact: TCC Database — Transparency, Consent, and Control permissions."""
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "tcc_database"
USER_DB = "~/Library/Application Support/com.apple.TCC/TCC.db"
SYSTEM_DB = "/Library/Application Support/com.apple.TCC/TCC.db"
QUERY = (
    "SELECT service, client, client_type, auth_value, "
    "auth_reason, last_modified "
    "FROM access ORDER BY last_modified DESC"
)
RENAME = {
    "client_type": "client_type",
    "auth_reason": "auth_reason",
}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in expand_user_paths(USER_DB):
        sources.extend(copy_sqlite_db(path, collector))
    sources.extend(copy_sqlite_db(SYSTEM_DB, collector))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        if sf["path"].endswith(("-wal", "-shm")):
            continue
        rows = query_sqlite(sf["path"], QUERY)
        for row in rows:
            row["source_path"] = sf["path"]
        result.add_entries(rows)
    return result
