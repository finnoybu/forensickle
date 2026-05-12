"""Artifact: ShellBags — folder access history from USRCLASS.DAT."""
import logging
import os

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "shellbags"
SOURCE_PATHS = [r"%LOCALAPPDATA%\Microsoft\Windows\UsrClass.dat"]
BAGMRU_KEY = r"Local Settings\Software\Microsoft\Windows\Shell\BagMRU"
BAGS_KEY = r"Local Settings\Software\Microsoft\Windows\Shell\Bags"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for expanded in expand_user_paths(pattern):
            entry = collector.collect_file(expanded, source_type="registry_hive")
            if entry:
                sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    # ShellBag binary parsing requires complex shell item interpretation
    log.warning("ShellBags binary parsing not yet implemented; collected %d source files", len(sources))
    return result
