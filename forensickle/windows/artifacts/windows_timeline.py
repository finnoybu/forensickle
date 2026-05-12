"""Artifact: Windows Timeline — ActivitiesCache.db (user activity history)."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.sqlite_utils import copy_sqlite_db, query_sqlite, transform_results
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "windows_timeline"
SOURCE_PATHS = [r"%LOCALAPPDATA%\ConnectedDevicesPlatform\*\ActivitiesCache.db"]
QUERY = (
    "SELECT Id, AppId, AppActivityId, ActivityType, LastModifiedTime, "
    "ExpirationTime, CreatedInCloud, StartTime, EndTime, LastModifiedOnClient, "
    "GroupAppActivityId, EnterpriseId, IsLocalOnly, Etag, PackageIdHash, "
    "PlatformDeviceId, Priority, Tag, [Group], UserActionState, ActivityStatus, "
    "ParentActivityId, Payload "
    "FROM Activity"
)

# Normalize PascalCase SQLite columns to snake_case matching Cortex
RENAME = {
    "Id": "id",
    "AppId": "app_id",
    "AppActivityId": "app_activity_id",
    "ActivityType": "activity_type",
    "LastModifiedTime": "last_modified",
    "ExpirationTime": "expiration_time",
    "CreatedInCloud": "created_in_cloud",
    "StartTime": "start_time",
    "EndTime": "end_time",
    "LastModifiedOnClient": "last_modified_on_client",
    "GroupAppActivityId": "group_app_activity_id",
    "EnterpriseId": "enterprise_id",
    "IsLocalOnly": "is_local_only",
    "Etag": "etag",
    "PackageIdHash": "package_id_hash",
    "PlatformDeviceId": "platform_device_id",
    "Priority": "priority",
    "Tag": "tag",
    "Group": "group",
    "UserActionState": "user_action_state",
    "ActivityStatus": "activity_status",
    "ParentActivityId": "parent_activity_id",
    "Payload": "payload",
}


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for expanded in expand_user_paths(pattern):
            for path in glob.glob(expanded):
                sources.extend(copy_sqlite_db(path, collector))
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        if sf["path"].endswith(("-wal", "-shm")):
            continue
        rows = query_sqlite(sf["path"], QUERY)
        result.add_entries(transform_results(rows, rename=RENAME))
    return result
