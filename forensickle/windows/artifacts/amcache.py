"""Artifact: AmCache — program execution/existence evidence from Amcache.hve.

Supports both Win8 (Root\\File, Root\\Programs) and Win10+ (Root\\InventoryApplicationFile,
Root\\InventoryApplication) formats. Also parses Shortcuts, DriverBinaries, DeviceContainers,
DevicePnps, and DriverPackages when present.

SHA-1 hashes are first 30MB of file only. Key last write time on Win10+ reflects
Compatibility Appraiser scan, NOT execution time.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.timestamp_utils import filetime_to_epoch_ms, epoch_ms_now

log = logging.getLogger(__name__)

NAME = "amcache"
SOURCE_PATH = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"),
    "appcompat", "Programs", "Amcache.hve",
)
# Also collect transaction logs for dirty hive recovery
LOG_PATTERNS = [SOURCE_PATH + ".LOG1", SOURCE_PATH + ".LOG2"]

try:
    from Registry import Registry
except ImportError:
    Registry = None

try:
    from regipy.recovery import apply_transaction_logs
except ImportError:
    apply_transaction_logs = None


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in [SOURCE_PATH] + LOG_PATTERNS:
        entry = collector.collect_file(path, source_type="registry_hive")
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)

    if not Registry:
        log.error("python-registry not available — cannot parse AmCache")
        return result

    hive_source = next((s for s in sources if s["path"].endswith(".hve")), None)
    if not hive_source:
        return result

    copied_path = collector.collected_path(hive_source)
    if not copied_path:
        log.error("Collected AmCache hive not found in sources")
        return result

    # Replay transaction logs if available
    parse_path = _replay_logs(copied_path, sources, collector)

    try:
        reg = Registry.Registry(parse_path)
    except Exception as e:
        log.error("Failed to open AmCache hive: %s", e)
        return result

    # Detect format
    fmt = _detect_format(reg)
    log.info("AmCache format: %s", fmt)

    if fmt == "win10":
        _parse_win10_files(reg, result)
        _parse_win10_programs(reg, result)
    elif fmt == "win8":
        _parse_win8_files(reg, result)

    # Common subkeys across formats
    _parse_shortcuts(reg, result)
    _parse_driver_binaries(reg, result)
    _parse_device_containers(reg, result)
    _parse_device_pnps(reg, result)
    _parse_driver_packages(reg, result)

    # Tag file entries as associated/unassociated
    _tag_association(result)

    return result


# ---------------------------------------------------------------------------
# Transaction log replay
# ---------------------------------------------------------------------------

def _replay_logs(hive_path: str, sources: list[dict], collector) -> str:
    """Apply transaction logs to the hive for a clean parse. Returns path to use."""
    if not apply_transaction_logs:
        log.debug("regipy not available — skipping log replay")
        return hive_path

    # Find LOG1 and LOG2 in collected sources
    log1_source = next((s for s in sources if s["path"].endswith(".LOG1")), None)
    log2_source = next((s for s in sources if s["path"].endswith(".LOG2")), None)

    log1_path = collector.collected_path(log1_source) if log1_source else None
    log2_path = collector.collected_path(log2_source) if log2_source else None

    if not log1_path and not log2_path:
        log.debug("No transaction logs found — parsing hive as-is")
        return hive_path

    # Apply logs to a new restored hive
    restored_path = hive_path + ".clean"
    try:
        apply_transaction_logs(
            hive_path,
            primary_log_path=log1_path or log2_path,
            secondary_log_path=log2_path if log1_path else None,
            restored_hive_path=restored_path,
        )
        if os.path.isfile(restored_path) and os.path.getsize(restored_path) > 0:
            log.info("Transaction logs replayed → %s (%d bytes)",
                     restored_path, os.path.getsize(restored_path))
            return restored_path
    except Exception as e:
        log.warning("Log replay failed: %s — parsing hive without replay", e)

    return hive_path


# ---------------------------------------------------------------------------
# Associated / Unassociated tagging
# ---------------------------------------------------------------------------

def _tag_association(result: ResultBuilder):
    """Tag file entries as 'associated' or 'unassociated' based on program entries."""
    # Collect all known program IDs
    program_ids = set()
    for entry in result.entries:
        if entry.get("_type") == "program_entry":
            pid = entry.get("program_id", "") or entry.get("programid", "")
            if pid:
                program_ids.add(pid.lower())

    # Tag each file entry
    for entry in result.entries:
        if entry.get("_type") != "file_entry":
            continue
        pid = entry.get("programid", "") or entry.get("program_id", "")
        if pid and pid.lower() in program_ids:
            entry["associated"] = True
        else:
            entry["associated"] = False


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def _detect_format(reg) -> str:
    try:
        reg.open("Root\\InventoryApplicationFile")
        return "win10"
    except Exception:
        pass
    try:
        reg.open("Root\\File")
        return "win8"
    except Exception:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# Win10+ parsing
# ---------------------------------------------------------------------------

_WIN10_FILE_VALUES = [
    "ProgramId", "LongPathHash", "Name", "LowerCaseLongPath", "FileId",
    "ProductName", "Publisher", "Language", "Version", "Size", "BinaryType",
    "IsPeFile", "IsOsComponent", "LinkDate", "BinFileVersion", "ProductVersion",
    "BinProductVersion", "Usn",
]


def _parse_win10_files(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryApplicationFile")
    except Exception:
        return

    for subkey in key.subkeys():
        entry = {
            "_type": "file_entry",
            "_format": "win10",
            "key_name": subkey.name(),
            "key_last_modified": _key_ts(subkey),
        }
        vals = {v.name(): v.value() for v in subkey.values()}

        for field in _WIN10_FILE_VALUES:
            entry[field.lower()] = vals.get(field)

        # SHA-1: strip leading "0000" prefix
        file_id = entry.get("fileid") or ""
        if isinstance(file_id, str) and len(file_id) > 4:
            entry["sha1"] = file_id[4:]
        else:
            entry["sha1"] = file_id

        # Path
        entry["path"] = entry.pop("lowercaselongpath", "")
        entry["file_name"] = entry.pop("name", "")
        entry["file_id"] = entry.pop("longpathhash", "")

        # Boolean conversions
        for bf in ("isoscomponent", "ispefile"):
            v = entry.get(bf)
            if v is not None:
                entry[bf] = bool(int(v)) if str(v).isdigit() else bool(v)

        # LinkDate: parse "MM/DD/YYYY HH:MM:SS" string
        ld = entry.get("linkdate")
        if isinstance(ld, str) and ld.strip():
            try:
                dt = datetime.strptime(ld.strip(), "%m/%d/%Y %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
                entry["link_date_ms"] = int(dt.timestamp() * 1000)
            except ValueError:
                entry["link_date_ms"] = None
        else:
            entry["link_date_ms"] = None

        # Clean up None fields
        entry = {k: v for k, v in entry.items() if v is not None and v != ""}
        result.add_entry(entry)


def _parse_win10_programs(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryApplication")
    except Exception:
        return

    for subkey in key.subkeys():
        entry = {
            "_type": "program_entry",
            "_format": "win10",
            "program_id": subkey.name(),
            "key_last_modified": _key_ts(subkey),
        }
        for v in subkey.values():
            entry[v.name().lower()] = v.value()
        entry = {k: v for k, v in entry.items() if v is not None and v != ""}
        result.add_entry(entry)


# ---------------------------------------------------------------------------
# Win8 parsing
# ---------------------------------------------------------------------------

_WIN8_VALUE_MAP = {
    "0": "product_name", "1": "company_name", "2": "file_version_number",
    "3": "language_code", "5": "file_version", "6": "size",
    "c": "file_description", "f": "link_date_unix",
    "11": "file_last_modified_ft", "12": "file_created_ft",
    "15": "path", "17": "install_date_ft",
    "100": "program_id", "101": "sha1_raw",
    "8": "pe_header_hash_raw", "9": "pe_header_checksum",
}


def _parse_win8_files(reg, result: ResultBuilder):
    try:
        file_key = reg.open("Root\\File")
    except Exception:
        return

    for vol_key in file_key.subkeys():
        for subkey in vol_key.subkeys():
            entry = {
                "_type": "file_entry",
                "_format": "win8",
                "volume_guid": vol_key.name(),
                "file_id": subkey.name(),
                "key_last_modified": _key_ts(subkey),
            }
            vals = {str(v.name()): v.value() for v in subkey.values()}

            for val_id, field_name in _WIN8_VALUE_MAP.items():
                if val_id in vals:
                    entry[field_name] = vals[val_id]

            # SHA-1: strip "0000" prefix
            raw_sha1 = entry.pop("sha1_raw", "")
            if isinstance(raw_sha1, str) and len(raw_sha1) > 4:
                entry["sha1"] = raw_sha1[4:]

            # PE header hash: strip prefix (fix Cortex bug: [4:0] → [4:])
            raw_pehash = entry.pop("pe_header_hash_raw", "")
            if isinstance(raw_pehash, str) and len(raw_pehash) > 4:
                entry["pe_header_hash"] = raw_pehash[4:]

            # Timestamp conversions
            ld = entry.pop("link_date_unix", None)
            if ld and isinstance(ld, (int, float)) and ld > 0:
                entry["link_date_ms"] = int(ld) * 1000

            for ft_field, ms_field in [
                ("file_last_modified_ft", "file_last_modified_ms"),
                ("file_created_ft", "file_created_ms"),
                ("install_date_ft", "install_date_ms"),
            ]:
                ft_val = entry.pop(ft_field, None)
                if ft_val:
                    entry[ms_field] = filetime_to_epoch_ms(int(ft_val))

            entry = {k: v for k, v in entry.items() if v is not None and v != ""}
            result.add_entry(entry)


# ---------------------------------------------------------------------------
# Additional subkeys (both formats)
# ---------------------------------------------------------------------------

def _parse_shortcuts(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryApplicationShortcut")
    except Exception:
        return
    for subkey in key.subkeys():
        entry = {"_type": "shortcut", "key_name": subkey.name(), "key_last_modified": _key_ts(subkey)}
        for v in subkey.values():
            entry[v.name().lower()] = v.value()
        result.add_entry(entry)


def _parse_driver_binaries(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryDriverBinary")
    except Exception:
        return
    for subkey in key.subkeys():
        entry = {"_type": "driver_binary", "key_name": subkey.name(), "key_last_modified": _key_ts(subkey)}
        for v in subkey.values():
            entry[v.name().lower()] = v.value()
        result.add_entry(entry)


def _parse_device_containers(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryDeviceContainer")
    except Exception:
        return
    for subkey in key.subkeys():
        entry = {"_type": "device_container", "key_name": subkey.name(), "key_last_modified": _key_ts(subkey)}
        for v in subkey.values():
            entry[v.name().lower()] = v.value()
        result.add_entry(entry)


def _parse_device_pnps(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryDevicePnp")
    except Exception:
        return
    for subkey in key.subkeys():
        entry = {"_type": "device_pnp", "key_name": subkey.name(), "key_last_modified": _key_ts(subkey)}
        for v in subkey.values():
            entry[v.name().lower()] = v.value()
        result.add_entry(entry)


def _parse_driver_packages(reg, result: ResultBuilder):
    try:
        key = reg.open("Root\\InventoryDriverPackage")
    except Exception:
        return
    for subkey in key.subkeys():
        entry = {"_type": "driver_package", "key_name": subkey.name(), "key_last_modified": _key_ts(subkey)}
        for v in subkey.values():
            entry[v.name().lower()] = v.value()
        result.add_entry(entry)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _key_ts(subkey) -> int | None:
    """Get registry key last write time as epoch ms."""
    try:
        ts = subkey.timestamp()
        if ts:
            return int(ts.replace(tzinfo=timezone.utc).timestamp() * 1000)
    except Exception:
        pass
    return None
