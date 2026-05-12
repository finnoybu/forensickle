"""Artifact: Windows Search Index — Windows.edb ESE database."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.ese_utils import copy_ese_db
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "windows_search_index"
SOURCE_PATH = os.path.join(
    os.environ.get("ProgramData", r"C:\ProgramData"),
    "Microsoft", "Search", "Data", "Applications", "Windows", "Windows.edb")


def collect(collector: SourceCollector) -> list[dict]:
    if os.path.isfile(SOURCE_PATH):
        return copy_ese_db(SOURCE_PATH, collector)
    return []


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
