"""Artifact: Network Connections — active connections via psutil."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None

NAME = "network_connections"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    if psutil is None:
        log.warning("psutil not available, skipping %s", NAME)
        return result
    pid_name = {}
    for p in psutil.process_iter(["pid", "name"]):
        try:
            pid_name[p.info["pid"]] = p.info["name"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for conn in psutil.net_connections(kind="inet"):
        result.add_entry({
            "pid": conn.pid,
            "local_addr": conn.laddr.ip if conn.laddr else "",
            "local_port": conn.laddr.port if conn.laddr else None,
            "remote_addr": conn.raddr.ip if conn.raddr else "",
            "remote_port": conn.raddr.port if conn.raddr else None,
            "status": conn.status,
            "process_name": pid_name.get(conn.pid, ""),
        })
    return result
