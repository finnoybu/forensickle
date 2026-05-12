"""Artifact: Process List — active processes via psutil."""
import logging

from ..core.collector import SourceCollector
from ..core.hash_utils import file_hashes
from ..core.timestamp_utils import stat_time_to_epoch_ms
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

NAME = "process_list"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    if not _HAS_PSUTIL:
        log.warning("psutil not available, skipping process_list")
        return result

    for proc in psutil.process_iter(
        ["pid", "name", "exe", "username", "ppid", "create_time", "cmdline"]
    ):
        try:
            info = proc.info
            exe_path = info.get("exe") or ""
            hashes = file_hashes(exe_path) if exe_path else None
            result.add_entry({
                "pid": info.get("pid"),
                "name": info.get("name"),
                "path": exe_path,
                "user": info.get("username"),
                "parent_pid": info.get("ppid"),
                "sha256": hashes["sha256"] if hashes else None,
                "create_time": stat_time_to_epoch_ms(info["create_time"])
                if info.get("create_time") else None,
                "cmdline": info.get("cmdline"),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return result
