"""Artifact: Process List — active processes via psutil."""
import logging

from ..core.collector import SourceCollector
from ..core.hash_utils import file_hashes
from ..core.output import ResultBuilder
from ..core.timestamp_utils import normalize_timestamp_ms

log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None

NAME = "process_list"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    if psutil is None:
        log.warning("psutil not available, skipping %s", NAME)
        return result
    for proc in psutil.process_iter(["pid", "name", "exe", "username", "ppid",
                                      "create_time", "cmdline"]):
        try:
            info = proc.info
            cpu = proc.cpu_times()
            io = proc.io_counters() if hasattr(proc, "io_counters") else None
            sha = ""
            if info["exe"]:
                h = file_hashes(info["exe"])
                sha = h["sha256"] if h else ""
            result.add_entry({
                "pid": info["pid"],
                "name": info["name"],
                "path": info["exe"] or "",
                "user": info["username"] or "",
                "parent_pid": info["ppid"],
                "sha256": sha,
                "create_time": normalize_timestamp_ms(int(info["create_time"] * 1000))
                    if info["create_time"] else None,
                "cmdline": " ".join(info["cmdline"] or []),
                "cpu_user": cpu.user,
                "cpu_system": cpu.system,
                "threads": proc.num_threads(),
                "read_bytes": io.read_bytes if io else None,
                "write_bytes": io.write_bytes if io else None,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return result
