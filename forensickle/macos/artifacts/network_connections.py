"""Artifact: Network Connections — active connections via psutil."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

NAME = "network_connections"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    if not _HAS_PSUTIL:
        log.warning("psutil not available, skipping network_connections")
        return result

    for conn in psutil.net_connections(kind="inet"):
        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None
        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None
        result.add_entry({
            "fd": conn.fd,
            "family": str(conn.family),
            "type": str(conn.type),
            "local_address": laddr,
            "remote_address": raddr,
            "status": conn.status,
            "pid": conn.pid,
        })
    return result
