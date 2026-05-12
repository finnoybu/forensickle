"""Artifact: Recycle Bin — deleted file metadata from $I/$R file pairs.

Parses $I binary format v1 (Vista/7) and v2 (Win8+). Resolves user SID to
username, collects file system timestamps from the companion $R file.
"""
import glob
import logging
import os
import struct
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.timestamp_utils import filetime_to_epoch_ms, epoch_ms_now

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "recycle_bin"


def _drive_letters() -> list[str]:
    """Return available drive letters on Windows."""
    if sys.platform != "win32":
        return ["C:"]
    import ctypes
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    return [f"{chr(65 + i)}:" for i in range(26) if bitmask & (1 << i)]


def _resolve_sid(sid: str) -> str | None:
    """Resolve a SID string to a username via PowerShell."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(New-Object System.Security.Principal.SecurityIdentifier('{sid}')).Translate("
             "[System.Security.Principal.NTAccount]).Value"],
            capture_output=True, text=True, timeout=10, creationflags=_NO_WINDOW,
        )
        name = r.stdout.strip()
        return name if name else None
    except Exception:
        return None


def _stat_timestamps(path: str) -> dict:
    """Return created/modified/accessed/entry_modified epoch ms from os.stat."""
    out = {"created": None, "modified": None, "accessed": None, "entry_modified": None}
    try:
        st = os.stat(path)
        out["created"] = int(getattr(st, "st_birthtime", st.st_ctime) * 1000)
        out["modified"] = int(st.st_mtime * 1000)
        out["accessed"] = int(st.st_atime * 1000)
        out["entry_modified"] = int(st.st_ctime * 1000)
    except OSError:
        pass
    return out


def _parse_i_file(data: bytes) -> tuple | None:
    """Parse $I binary. Returns (original_path, deleted_epoch_ms, size) or None."""
    if len(data) < 24:
        return None
    version = struct.unpack_from("<Q", data, 0)[0]
    size = struct.unpack_from("<Q", data, 8)[0]
    deleted_ft = struct.unpack_from("<Q", data, 16)[0]
    if version == 2:
        if len(data) < 28:
            return None
        path_len = struct.unpack_from("<I", data, 24)[0]
        end = 28 + path_len * 2
        if end > len(data):
            end = len(data)
        original_path = data[28:end].decode("utf-16-le", errors="replace").rstrip("\x00")
    elif version == 1:
        original_path = data[24:24 + 520].decode("utf-16-le", errors="replace").rstrip("\x00")
    else:
        return None
    return original_path, filetime_to_epoch_ms(deleted_ft), size


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for drive in _drive_letters():
        pattern = os.path.join(drive, os.sep, "$Recycle.Bin", "*", "$I*")
        for path in glob.glob(pattern):
            if os.path.isfile(path):
                entry = collector.collect_file(path)
                if entry:
                    sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    sid_cache: dict[str, str | None] = {}
    for sf in sources:
        cp = collector.collected_path(sf)
        if not cp:
            continue
        try:
            with open(cp, "rb") as f:
                data = f.read()
        except OSError as e:
            log.debug("Cannot read %s: %s", cp, e)
            continue
        parsed = _parse_i_file(data)
        if not parsed:
            continue
        original_path, deleted_ms, size = parsed
        # SID from parent directory name
        sid = os.path.basename(os.path.dirname(sf["path"]))
        if sid not in sid_cache:
            sid_cache[sid] = _resolve_sid(sid)
        # $R companion file timestamps
        r_path = sf["path"].replace("$I", "$R", 1)
        timestamps = _stat_timestamps(r_path)
        result.add_entry({
            "original_path": original_path,
            "user_sid": sid,
            "user": sid_cache[sid],
            "deleted": deleted_ms,
            "size": size,
            "path": sf["path"],
            **timestamps,
        })
    return result
