"""Artifact: WiFi History — known wireless networks from system preferences."""
import logging

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.timestamp_utils import datetime_to_epoch_ms
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "wifi_history"
WIFI_PLIST = "/Library/Preferences/SystemConfiguration/com.apple.wifi.known-networks.plist"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    entry = collector.collect_file(WIFI_PLIST)
    if entry:
        sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    for sf in sources:
        plist = read_plist(sf["path"])
        if not isinstance(plist, dict):
            continue
        for ssid, info in plist.items():
            if not isinstance(info, dict):
                continue
            entry = {"ssid": ssid}
            last_connected = info.get("LastConnected")
            if last_connected:
                entry["last_connected"] = datetime_to_epoch_ms(last_connected)
            security = info.get("SecurityType", "")
            entry["security_type"] = security
            added_by = info.get("AddedBy", "")
            if added_by:
                entry["added_by"] = added_by
            result.add_entry(entry)
    return result
