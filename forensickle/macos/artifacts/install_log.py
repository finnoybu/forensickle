"""Artifact: Install Log — system install log and package install history."""
import logging

from ..core.collector import SourceCollector
from ..core.plist_utils import read_plist
from ..core.timestamp_utils import datetime_to_epoch_ms
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "install_log"
INSTALL_LOG = "/var/log/install.log"
INSTALL_HISTORY = "/Library/Receipts/InstallHistory.plist"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in [INSTALL_LOG, INSTALL_HISTORY]:
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    # Parse install.log lines
    for sf in sources:
        if sf["path"] == INSTALL_LOG:
            try:
                with open(sf["path"], "r", encoding="utf-8", errors="replace") as f:
                    for line_no, line in enumerate(f, 1):
                        stripped = line.rstrip("\n")
                        if not stripped:
                            continue
                        result.add_entry({
                            "source": "install.log",
                            "line_number": line_no,
                            "raw": stripped,
                        })
            except OSError as e:
                log.error("Cannot read %s: %s", sf["path"], e)

        # Parse InstallHistory.plist
        elif sf["path"] == INSTALL_HISTORY:
            plist = read_plist(sf["path"])
            if not isinstance(plist, list):
                continue
            for item in plist:
                if not isinstance(item, dict):
                    continue
                entry = {
                    "source": "InstallHistory.plist",
                    "package_name": item.get("displayName", ""),
                    "package_version": item.get("displayVersion", ""),
                    "package_id": item.get("packageIdentifiers", []),
                    "process_name": item.get("processName", ""),
                }
                dt = item.get("date")
                if dt:
                    entry["install_date"] = datetime_to_epoch_ms(dt)
                result.add_entry(entry)
    return result
