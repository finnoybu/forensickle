"""Artifact: Quarantine Events — Gatekeeper quarantine event DB."""
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.timestamp_utils import safari_coredata_to_epoch_ms
from ..core.system_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "quarantine_events"
DB_PATTERN = "~/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2"
QUERY = (
    "SELECT LSQuarantineEventIdentifier, LSQuarantineTimeStamp, "
    "LSQuarantineAgentBundleIdentifier, LSQuarantineAgentName, "
    "LSQuarantineDataURLString, LSQuarantineSenderName, "
    "LSQuarantineSenderAddress, LSQuarantineOriginURLString, "
    "LSQuarantineTypeNumber FROM LSQuarantineEvent"
)
CONVERT = {"LSQuarantineTimeStamp": safari_coredata_to_epoch_ms}
RENAME = {
    "LSQuarantineEventIdentifier": "event_id",
    "LSQuarantineTimeStamp": "timestamp",
    "LSQuarantineAgentBundleIdentifier": "agent_bundle_id",
    "LSQuarantineAgentName": "agent_name",
    "LSQuarantineDataURLString": "data_url",
    "LSQuarantineSenderName": "sender_name",
    "LSQuarantineSenderAddress": "sender_address",
    "LSQuarantineOriginURLString": "origin_url",
    "LSQuarantineTypeNumber": "type_number",
}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in expand_user_paths(DB_PATTERN):
        sources.extend(copy_sqlite_db(path, collector))
    return sources


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        if sf["path"].endswith(("-wal", "-shm")):
            continue
        rows = query_sqlite(sf["path"], QUERY)
        result.add_entries(transform_results(rows, rename=RENAME, convert=CONVERT))
    return result
