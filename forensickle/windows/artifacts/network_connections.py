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

_PROTO_MAP = {
    ("AF_INET", "SOCK_STREAM"): "tcp",
    ("AF_INET", "SOCK_DGRAM"): "udp",
    ("AF_INET6", "SOCK_STREAM"): "tcp6",
    ("AF_INET6", "SOCK_DGRAM"): "udp6",
}


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    if psutil is None:
        log.error("psutil not available")
        return result
    proc_info = {}
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            info = proc.info
            proc_info[info["pid"]] = {
                "name": info["name"],
                "path": info["exe"],
                "cmdline": " ".join(info["cmdline"]) if info["cmdline"] else None,
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for conn in psutil.net_connections(kind="inet"):
        fam = conn.family.name if hasattr(conn.family, "name") else str(conn.family)
        typ = conn.type.name if hasattr(conn.type, "name") else str(conn.type)
        pi = proc_info.get(conn.pid, {})
        entry = {
            "pid": conn.pid,
            "process_name": pi.get("name"),
            "process_path": pi.get("path"),
            "command_line": pi.get("cmdline"),
            "protocol": _PROTO_MAP.get((fam, typ), f"{fam}/{typ}"),
            "local_address": conn.laddr.ip if conn.laddr else None,
            "local_port": conn.laddr.port if conn.laddr else None,
            "remote_address": conn.raddr.ip if conn.raddr else None,
            "remote_port": conn.raddr.port if conn.raddr else None,
            "state": conn.status,
        }
        result.add_entry(entry)
    return result
