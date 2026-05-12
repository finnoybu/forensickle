"""Artifact: Zone.Identifier ADS — Mark of the Web on downloaded files."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "zone_identifier"
DOWNLOAD_PATTERNS = [
    r"%USERPROFILE%\Downloads\*",
    r"%USERPROFILE%\Desktop\*",
]


def collect(collector: SourceCollector) -> list[dict]:
    return []  # ADS data read live


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    for pattern in DOWNLOAD_PATTERNS:
        for expanded in expand_user_paths(pattern):
            for path in glob.glob(expanded):
                if not os.path.isfile(path):
                    continue
                ads_path = path + ":Zone.Identifier"
                try:
                    with open(ads_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    entry = {"file": path}
                    for line in content.splitlines():
                        if "=" in line:
                            k, _, v = line.partition("=")
                            entry[k.strip().lower()] = v.strip()
                    result.add_entry(entry)
                except OSError:
                    pass  # No Zone.Identifier ADS
    return result
