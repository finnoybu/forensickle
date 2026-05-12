from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forensickle.windows.core.collector import SourceCollector

log = logging.getLogger(__name__)


def copy_sqlite_db(source_path: str, collector: "SourceCollector") -> list[dict]:
    """Copy SQLite DB plus -wal and -shm companions if they exist."""
    paths = [source_path]
    for suffix in ("-wal", "-shm"):
        companion = source_path + suffix
        if os.path.isfile(companion):
            paths.append(companion)
    return collector.collect_files(paths)


def query_sqlite(db_path: str, query: str, params: tuple | None = None) -> list[dict]:
    """Query SQLite DB in immutable mode. Returns list of row dicts."""
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
    convert: dict[str, callable] | None = None,
) -> list[dict]:
    """Rename columns and apply conversion functions to result rows."""
    rename = rename or {}
    convert = convert or {}
    out = []
    for row in rows:
        entry = {}
        for key, val in row.items():
            new_key = rename.get(key, key)
            if key in convert:
                try:
                    val = convert[key](val)
                except (TypeError, ValueError, OverflowError) as e:
                    log.debug("Conversion failed for %s=%r: %s", key, val, e)
            entry[new_key] = val
        out.append(entry)
    return out
