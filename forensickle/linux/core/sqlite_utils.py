import logging
import os
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


def copy_sqlite_db(source_path: str, collector: Any) -> list[dict]:
    """Copy a SQLite DB and its WAL/SHM files via the collector."""
    entries = []
    for suffix in ("", "-wal", "-shm"):
        p = source_path + suffix
        if os.path.isfile(p):
            entry = collector.collect_file(p)
            if entry:
                entries.append(entry)
    return entries


def query_sqlite(db_path: str, query: str, params: tuple | None = None) -> list[dict]:
    """Query a SQLite DB in immutable mode. Returns list of dicts."""
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
    """Rename columns and apply conversion functions to result rows."""
    rename = rename or {}
    convert = convert or {}
    out = []
    for row in rows:
        entry = {}
        for key, val in row.items():
            new_key = rename.get(key, key)
            if new_key in convert:
                try:
                    val = convert[new_key](val)
                except (TypeError, ValueError, OSError) as e:
                    log.debug("Conversion failed for %s: %s", new_key, e)
            entry[new_key] = val
        out.append(entry)
    return out
