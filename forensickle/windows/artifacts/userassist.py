"""Artifact: UserAssist — program execution tracking from NTUSER.DAT."""
import codecs
import logging
import os
import re
import struct

from ..core.collector import SourceCollector
from ..core.hash_utils import file_hashes
from ..core.registry_utils import expand_user_paths
from ..core.timestamp_utils import filetime_to_epoch_ms
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "userassist"
NTUSER_PATHS = [r"%USERPROFILE%\NTUSER.DAT"]
USERASSIST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
GUIDS = [
    "{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}",  # Executable
    "{F4E57C4B-2036-45F0-A9AB-443BCFE33D9F}",  # Shortcut
]

try:
    from Registry import Registry
except ImportError:
    Registry = None


def _rot13(s: str) -> str:
    return codecs.decode(s, "rot_13")


def _parse_value(data: bytes) -> dict:
    """Parse UserAssist binary value (version 5 — Win7+)."""
    if not data or len(data) < 72:
        return {}
    try:
        session = struct.unpack_from("<I", data, 0)[0]
        run_count = struct.unpack_from("<I", data, 4)[0]
        focus_count = struct.unpack_from("<I", data, 8)[0]
        focus_time_ms = struct.unpack_from("<I", data, 12)[0]
        last_run_ft = struct.unpack_from("<Q", data, 60)[0]
        return {
            "session_id": session,
            "count": run_count,
            "focus_count": focus_count,
            "focus_time_ms": focus_time_ms,
            "last_run_time": filetime_to_epoch_ms(last_run_ft),
        }
    except struct.error:
        return {}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in NTUSER_PATHS:
        for expanded in expand_user_paths(pattern):
            entry = collector.collect_file(expanded, source_type="registry_hive")
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    if not Registry:
        log.error("python-registry not available")
        return result

    for sf in sources:
        copied = collector.collected_path(sf)
        if not copied:
            continue

        user_sid, user = _extract_user(sf["path"])

        try:
            reg = Registry.Registry(copied)
        except Exception as e:
            log.error("Failed to open hive %s: %s", sf["path"], e)
            continue

        for guid in GUIDS:
            subkey_path = f"{USERASSIST_KEY}\\{guid}\\Count"
            try:
                key = reg.open(subkey_path)
                key_modified = int(key.timestamp().timestamp() * 1000) if key.timestamp() else None
                for v in key.values():
                    if v.name().lower() == "(default)":
                        continue
                    item = _rot13(v.name())
                    parsed = _parse_value(v.value()) if isinstance(v.value(), bytes) else {}

                    # Resolve path and hash
                    exe_path = _resolve_path(item)
                    hashes = file_hashes(exe_path) if exe_path and os.path.isfile(exe_path) else None

                    entry = {
                        "item": item,
                        "class_id": guid,
                        "key_last_modified": key_modified,
                        "user": user,
                        "user_sid": user_sid,
                        "path": exe_path or "",
                        **parsed,
                    }
                    if hashes:
                        entry.update({"md5": hashes["md5"], "sha1": hashes["sha1"], "sha256": hashes["sha256"]})

                    result.add_entry(entry)
            except Exception as e:
                log.debug("UserAssist key not found: %s\\%s: %s", sf["path"], subkey_path, e)

    return result


def _extract_user(path: str) -> tuple[str, str]:
    m = re.search(r"[/\\]Users[/\\]([^/\\]+)[/\\]", path, re.IGNORECASE)
    return ("", m.group(1) if m else "")


def _resolve_path(item: str) -> str:
    """Try to resolve a UserAssist item to a filesystem path."""
    # Strip GUID prefixes like {6D809377-...}\
    cleaned = re.sub(r"^\{[A-Fa-f0-9-]+\}\\", "", item)
    expanded = os.path.expandvars(cleaned)
    if os.path.isfile(expanded):
        return expanded
    return cleaned
