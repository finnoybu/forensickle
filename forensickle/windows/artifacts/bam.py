"""Artifact: BAM (Background Activity Moderator) — program execution with timestamps."""
import logging
import os
import struct

from ..core.collector import SourceCollector
from ..core.timestamp_utils import filetime_to_epoch_ms
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "bam"
SOURCE_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "config", "SYSTEM")
SUBKEY = r"ControlSet001\Services\bam\State\UserSettings"

try:
    from Registry import Registry
except ImportError:
    Registry = None


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
            for sid_key in key.subkeys():
                sid = sid_key.name()
                for v in sid_key.values():
                    if v.name().startswith("Version") or v.name().startswith("Sequence"):
                        continue
                    data = v.value()
                    ft = struct.unpack_from("<Q", data, 0)[0] if isinstance(data, bytes) and len(data) >= 8 else 0
                    result.add_entry({
                        "user_sid": sid,
                        "path": v.name(),
                        "value_path": f"{SUBKEY}\\{sid}",
                        "last_executed": filetime_to_epoch_ms(ft),
                        "last_modified": int(sid_key.timestamp().timestamp() * 1000) if sid_key.timestamp() else None,
                    })
        except Exception as e:
            log.error("Failed to parse BAM: %s", e)
    return result
