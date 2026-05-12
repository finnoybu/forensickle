"""Artifact: WordWheelQuery — Explorer search bar history from NTUSER.DAT."""
import logging
import re
import struct

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "word_wheel_query"
NTUSER_PATHS = [r"%USERPROFILE%\NTUSER.DAT"]
SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\WordWheelQuery"

try:
    from Registry import Registry
except ImportError:
    Registry = None


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
            key = reg.open(SUBKEY)
            key_modified = int(key.timestamp().timestamp() * 1000) if key.timestamp() else None

            mru_order = []
            for v in key.values():
                if v.name() == "MRUListEx":
                    data = v.value()
                    for off in range(0, len(data) - 4, 4):
                        idx = struct.unpack_from("<I", data, off)[0]
                        if idx == 0xFFFFFFFF:
                            break
                        mru_order.append(idx)

            for v in key.values():
                if v.name() == "MRUListEx":
                    continue
                try:
                    idx = int(v.name())
                except ValueError:
                    continue
                raw = v.value()
                query = raw.decode("utf-16-le", errors="replace").rstrip("\x00") if isinstance(raw, bytes) else str(raw)
                rank = mru_order.index(idx) if idx in mru_order else None
                result.add_entry({
                    "entry": str(idx),
                    "query": query,
                    "mru_rank": rank,
                    "last_modified": key_modified,
                    "value_path": SUBKEY,
                    "user": user,
                    "user_sid": user_sid,
                })
        except Exception as e:
            log.debug("WordWheelQuery not found in %s: %s", sf["path"], e)

    return result


def _extract_user(path: str) -> tuple[str, str]:
    m = re.search(r"[/\\]Users[/\\]([^/\\]+)[/\\]", path, re.IGNORECASE)
    return ("", m.group(1) if m else "")
