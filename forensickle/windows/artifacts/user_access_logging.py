"""Artifact: User Access Logging — ESE databases in LogFiles\\Sum."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.ese_utils import copy_ese_db, query_ese_table
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "user_access_logging"
SOURCE_DIR = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                          "System32", "LogFiles", "Sum")


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob(os.path.join(SOURCE_DIR, "*.mdb")):
        if os.path.isfile(path):
            sources.extend(copy_ese_db(path, collector))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        for table in ("CLIENTS", "DNS", "ROLE_ACCESS"):
            try:
                rows = query_ese_table(sf["path"], table)
                for row in rows:
                    row["_table"] = table
                    row["_source"] = sf["path"]
                result.add_entries(rows)
            except Exception as e:
                log.debug("Failed to query %s in %s: %s", table, sf["path"], e)
    return result
