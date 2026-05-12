"""Artifact: SRUM — System Resource Usage Monitor (Application and Network usage)."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.ese_utils import copy_ese_db, query_ese_table
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "srum"
SOURCE_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                           "System32", "sru", "SRUDB.dat")
TABLES = {
    "{D10CA2FE-6FCF-4F6D-848E-B2E99266FA89}": "application_resource_usage",
    "{973F5D5C-1D90-4944-BE8E-24B94231A174}": "network_data_usage",
}


def collect(collector: SourceCollector) -> list[dict]:
    if os.path.isfile(SOURCE_PATH):
        return copy_ese_db(SOURCE_PATH, collector)
    return []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        for table_name, label in TABLES.items():
            rows = query_ese_table(sf["path"], table_name)
            for row in rows:
                row["_table"] = label
            result.add_entries(rows)
    return result
