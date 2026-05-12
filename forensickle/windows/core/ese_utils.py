from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

if TYPE_CHECKING:
    from forensickle.windows.core.collector import SourceCollector

log = logging.getLogger(__name__)

try:
    import pyesedb
except ImportError:
    pyesedb = None


def copy_ese_db(source_path: str, collector: "SourceCollector") -> list[dict]:
    """Copy ESE DB using esentutl.exe for clean shutdown, falling back to raw copy."""
    dest_hash = collector.path_hash(source_path)
    ext = os.path.splitext(source_path)[1] or ".dat"
    dest_path = os.path.join(collector.sources_dir, f"{dest_hash}{ext}")

    if _copy_with_esentutl(source_path, dest_path):
        log.info("ESE DB copied via esentutl: %s", source_path)
    else:
        log.info("esentutl failed, falling back to raw copy: %s", source_path)
        return [collector.collect_file(source_path)]

    # Register in manifest manually since we bypassed the normal copy
    from forensickle.windows.core.hash_utils import file_hashes
    hashes = file_hashes(dest_path)
    entry = {
        "path": source_path,
        "path_hash": dest_hash,
        "content_hash": hashes["sha256"] if hashes else None,
    }
    collector._manifest["sources"][dest_hash] = entry
    collector.save_manifest()
    return [entry]


def _copy_with_esentutl(source_path: str, dest_path: str) -> bool:
    """Attempt esentutl.exe /y copy with /vssrec."""
    try:
        temp_dir = tempfile.mkdtemp(prefix="forensickle_ese_")
        temp_dest = os.path.join(temp_dir, os.path.basename(dest_path))
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        cmd = [
            "esentutl.exe", "/y", source_path,
            "/vssrec", base_name,
            os.path.dirname(source_path),
            "/d", temp_dest,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=_NO_WINDOW)
        if proc.returncode == 0:
            os.replace(temp_dest, dest_path)
            return True
        log.debug("esentutl returned %d: %s", proc.returncode, proc.stderr.strip())
        return False
    except (OSError, subprocess.TimeoutExpired) as e:
        log.debug("esentutl failed: %s", e)
        return False
    finally:
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass


def query_ese_table(
    db_path: str, table_name: str, columns: list[str] | None = None
) -> list[dict]:
    """Open ESE DB via pyesedb, read table rows, return list of dicts."""
    if pyesedb is None:
        log.error("pyesedb not available")
        return []

    try:
        db = pyesedb.file()
        db.open(db_path)
    except Exception as e:
        log.error("Failed to open ESE DB %s: %s", db_path, e)
        return []

    try:
        table = None
        for t in db.tables:
            if t.name == table_name:
                table = t
                break
        if table is None:
            log.warning("Table %s not found in %s", table_name, db_path)
            return []

        col_names = [c.name for c in table.columns]
        target_cols = columns if columns else col_names
        col_indices = {name: i for i, name in enumerate(col_names) if name in target_cols}

        rows = []
        for rec_idx in range(table.number_of_records):
            record = table.get_record(rec_idx)
            row = {}
            for name, idx in col_indices.items():
                row[name] = _get_record_value(record, idx)
            rows.append(row)
        return rows
    except Exception as e:
        log.error("Failed to read table %s from %s: %s", table_name, db_path, e)
        return []
    finally:
        try:
            db.close()
        except Exception:
            pass


def _get_record_value(record, col_idx: int):
    """Extract typed value from ESE record column."""
    try:
        col_type = record.get_column_type(col_idx)
        data = record.get_value_data(col_idx)
        if data is None:
            return None
        # Common ESE column types
        if col_type in (0, 1):  # NULL, Boolean
            return bool(int.from_bytes(data, "little")) if data else None
        if col_type in (2, 3, 4):  # Unsigned byte, Short, Long
            return int.from_bytes(data, "little")
        if col_type == 5:  # Currency (8-byte int)
            return int.from_bytes(data, "little", signed=True)
        if col_type in (6, 7):  # Float, Double
            import struct
            fmt = "<f" if col_type == 6 else "<d"
            return struct.unpack(fmt, data)[0]
        if col_type == 8:  # DateTime
            import struct
            return struct.unpack("<d", data)[0]
        if col_type in (9, 11):  # Binary, Long Binary
            return data
        if col_type in (10, 12):  # Text, Long Text
            try:
                return data.decode("utf-16-le").rstrip("\x00")
            except UnicodeDecodeError:
                return data.decode("utf-8", errors="replace")
        if col_type in (14, 15):  # Unsigned Long, Long Long
            return int.from_bytes(data, "little")
        if col_type == 16:  # GUID
            return data.hex()
        return data
    except Exception:
        return None
