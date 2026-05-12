"""Artifact: System Registry Hives — SAM, SYSTEM, SOFTWARE, SECURITY + transaction logs."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "registry_system"
CONFIG_DIR = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                          "System32", "config")
HIVES = ["SAM", "SYSTEM", "SOFTWARE", "SECURITY"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for hive in HIVES:
        hive_path = os.path.join(CONFIG_DIR, hive)
        entry = collector.collect_file(hive_path, source_type="registry_hive")
        if entry:
            sources.append(entry)
        for logfile in glob.glob(hive_path + ".LOG*"):
            entry = collector.collect_file(logfile, source_type="registry_hive")
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
