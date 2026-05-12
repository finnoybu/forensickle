import logging
import os
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


def copy_sqlite_db(source_path: str, collector) -> list[dict]:
    """Copies main DB plus -wal and -shm if they exist. Returns source entries."""
    paths = [source_path]
    for suffix in ("-wal", "-shm"):
        companion = source_path + suffix
        if os.path.isfile(companion):
            paths.append(companion)
    return collector.collect_files(paths)


def query_sqlite(db_path: str, query: str, params: tuple | list | None = None) -> list[dict]:
    """Opens DB immutable, returns list of row dicts."""
    uri = f"file:{db_path}?immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params or ())
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        log.error("SQLite query failed on %s: %s", db_path, e)
        return []


def transform_results(
    rows: list[dict],
    rename: dict[str, str] | None = None,
    convert: dict[str, Any] | None = None,
) -> list[dict]:
    """Renames columns per rename dict, applies conversion functions per convert dict."""
    result = []
    for row in rows:
        entry = {}
        for key, value in row.items():
            out_key = rename.get(key, key) if rename else key
            if convert and out_key in convert:
                try:
                    value = convert[out_key](value)
                except (TypeError, ValueError, OverflowError) as e:
                    log.debug("Conversion failed for %s=%s: %s", out_key, value, e)
            entry[out_key] = value
        result.append(entry)
    return result
