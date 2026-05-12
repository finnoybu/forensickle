"""Artifact: Process List — active processes via psutil."""
import logging

from ..core.collector import SourceCollector
from ..core.hash_utils import file_hashes
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None

NAME = "process_list"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data, no files to collect


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    if psutil is None:
        log.error("psutil not available")
        return result
    pid_names = {p.info["pid"]: p.info["name"]
                 for p in psutil.process_iter(["pid", "name"])
                 if p.info.get("name")}
    for proc in psutil.process_iter(["pid", "name", "exe", "username", "ppid",
                                      "create_time", "cmdline", "status",
                                      "num_threads", "num_handles"]):
        try:
            info = proc.info
            entry = {
                "pid": info["pid"],
                "name": info["name"],
                "path": info["exe"],
                "user": info["username"],
                "parent_pid": info["ppid"],
                "parent": pid_names.get(info["ppid"]),
                "created": int(info["create_time"] * 1000) if info["create_time"] else None,
                "command_line": " ".join(info["cmdline"]) if info["cmdline"] else None,
                "state": info["status"],
                "threads": info.get("num_threads"),
                "handles": info.get("num_handles"),
                "terminated": False,
            }
            if info["exe"]:
                try:
                    hashes = file_hashes(info["exe"])
                    if hashes:
                        entry.update({"md5": hashes["md5"], "sha1": hashes["sha1"],
                                      "sha256": hashes["sha256"]})
                except Exception:
                    pass
            try:
                io = proc.io_counters()
                entry["bytes_read"] = io.read_bytes
                entry["bytes_write"] = io.write_bytes
                entry["read_operations"] = io.read_count
                entry["write_operations"] = io.write_count
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            try:
                times = proc.cpu_times()
                entry["user_time"] = times.user
                entry["system_time"] = times.system
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            result.add_entry(entry)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result
