"""Artifact: ShimCache (AppCompatCache) — program execution evidence from SYSTEM hive."""
import logging
import os
import struct

from ..core.collector import SourceCollector
from ..core.timestamp_utils import filetime_to_epoch_ms
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "shimcache"
SOURCE_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "config", "SYSTEM")
SUBKEY = r"ControlSet001\Control\Session Manager\AppCompatCache"

try:
    from Registry import Registry
except ImportError:
    Registry = None


def _parse_win10(data: bytes) -> list[dict]:
    """Parse Windows 10+ AppCompatCache binary format."""
    entries = []
    if len(data) < 48:
        return entries
    offset = 48
    while offset < len(data) - 12:
        try:
            sig = struct.unpack_from("<I", data, offset)[0]
            if sig != 0x73743030:  # "10ts"
                break
            str_len = struct.unpack_from("<I", data, offset + 8)[0]
            path = data[offset + 12: offset + 12 + str_len].decode("utf-16-le", errors="replace")
            ft_offset = offset + 12 + str_len
            last_mod = struct.unpack_from("<Q", data, ft_offset)[0] if ft_offset + 8 <= len(data) else 0
            entries.append({
                "path": path,
                "last_modified_time": filetime_to_epoch_ms(last_mod),
            })
            data_size = struct.unpack_from("<I", data, ft_offset + 8)[0] if ft_offset + 12 <= len(data) else 0
            offset = ft_offset + 12 + data_size
        except (struct.error, IndexError):
            break
    return entries


def collect(collector: SourceCollector) -> list[dict]:
    entry = collector.collect_file(SOURCE_PATH, source_type="registry_hive")
    return [entry] if entry else []


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
        try:
            reg = Registry.Registry(copied)
            key = reg.open(SUBKEY)
            for v in key.values():
                if v.name() == "AppCompatCache" and isinstance(v.value(), bytes):
                    result.add_entries(_parse_win10(v.value()))
        except Exception as e:
            log.error("Failed to parse ShimCache: %s", e)
    return result
