"""Artifact: MRU Lists — OpenSavePidlMRU, LastVisitedPidlMRU, CIDSizeMRU."""
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "mru_lists"
NTUSER_PATHS = [r"%USERPROFILE%\NTUSER.DAT"]
SUBKEYS = [
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU",
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\LastVisitedPidlMRU",
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\CIDSizeMRU",
]

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
        except Exception as e:
            log.error("Failed to open hive %s: %s", sf["path"], e)
            continue

        for subkey in SUBKEYS:
            mru_name = subkey.rsplit("\\", 1)[-1]
            try:
                key = reg.open(subkey)
                key_modified = int(key.timestamp().timestamp() * 1000) if key.timestamp() else None

                for v in key.values():
                    if v.name() == "MRUListEx":
                        continue
                    result.add_entry({
                        "mru_type": mru_name,
                        "entry": v.name(),
                        "value": v.value() if not isinstance(v.value(), bytes) else v.value().hex(),
                        "last_modified": key_modified,
                        "value_path": subkey,
                        "user": user,
                        "user_sid": user_sid,
                    })
                for sk in key.subkeys():
                    sk_modified = int(sk.timestamp().timestamp() * 1000) if sk.timestamp() else None
                    for v in sk.values():
                        if v.name() == "MRUListEx":
                            continue
                        result.add_entry({
                            "mru_type": f"{mru_name}\\{sk.name()}",
                            "entry": v.name(),
                            "value": v.value() if not isinstance(v.value(), bytes) else v.value().hex(),
                            "last_modified": sk_modified,
                            "value_path": f"{subkey}\\{sk.name()}",
                            "user": user,
                            "user_sid": user_sid,
                        })
            except Exception as e:
                log.debug("MRU key not found: %s: %s", subkey, e)

    return result


def _extract_user(path: str) -> tuple[str, str]:
    m = re.search(r"[/\\]Users[/\\]([^/\\]+)[/\\]", path, re.IGNORECASE)
    return ("", m.group(1) if m else "")
