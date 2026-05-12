"""Artifact: Wi-Fi History — NetworkManager connection profiles."""
import glob
import logging
from configparser import ConfigParser

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "wifi_history"
NM_CONN_DIR = "/etc/NetworkManager/system-connections"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob(f"{NM_CONN_DIR}/*.nmconnection"):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            cp = ConfigParser()
            cp.read(sf["path"])
            conn_type = cp.get("connection", "type", fallback="")
            result.add_entry({
                "source_file": sf["path"],
                "ssid": cp.get("wifi", "ssid", fallback=""),
                "type": conn_type,
                "auth": cp.get("wifi-security", "key-mgmt", fallback="open"),
                "last_connected": cp.get("connection", "timestamp", fallback=""),
            })
        except (OSError, Exception) as e:
            log.debug("Failed to parse %s: %s", sf["path"], e)
    return result
