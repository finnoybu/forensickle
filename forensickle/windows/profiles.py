"""Built-in profiles and config file I/O — driven by the artifact registry."""
from __future__ import annotations

import json
import logging
import os

from forensickle.registry import get_registry, ArtifactDefinition

log = logging.getLogger(__name__)

PLATFORM = "windows"


def _registry_artifacts() -> list[ArtifactDefinition]:
    """All artifacts for this platform from the registry."""
    return get_registry().for_platform(PLATFORM)


def get_categories() -> dict[str, list[ArtifactDefinition]]:
    """Artifact categories for this platform."""
    return get_registry().by_category(PLATFORM)


def all_artifact_ids() -> list[str]:
    return [a.artifact_id for a in _registry_artifacts()]


def display_name(artifact_id: str) -> str:
    defn = get_registry().get(artifact_id)
    return defn.display_name if defn else artifact_id.replace("_", " ").title()


def artifact_capabilities(artifact_id: str) -> dict:
    """Return can_parse/can_retain for an artifact."""
    defn = get_registry().get(artifact_id)
    if not defn:
        return {"can_parse": False, "can_retain": False}
    return {"can_parse": defn.can_parse, "can_retain": defn.can_retain}


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

def _build_profile(artifact_ids: list[str], parse: bool = True, retain: bool = False) -> dict[str, dict]:
    """Build a profile config, respecting each artifact's capabilities."""
    config = {}
    for aid in artifact_ids:
        caps = artifact_capabilities(aid)
        config[aid] = {
            "parse": parse and caps["can_parse"],
            "retain": retain or (not caps["can_parse"] and caps["can_retain"]),
        }
    return config


_TRIAGE_ARTIFACTS = [
    "process_list", "network_connections",
    "run_keys", "scheduled_tasks", "services", "startup_folders",
    "hosts_file", "arp_cache", "dns_cache",
    "event_logs", "registry_system", "registry_user",
]

_STANDARD_ARTIFACTS = _TRIAGE_ARTIFACTS + [
    "chrome_history", "edge_history", "firefox_history", "ie_history",
    "userassist", "shimcache", "amcache", "bam", "prefetch",
    "psreadline", "srum", "environment_vars",
    "recycle_bin", "recent_files", "jumplist",
    "usb_device_history", "drivers",
    "defender_logs",
]

_FULL_ARTIFACTS = all_artifact_ids()


def get_profile(name: str) -> dict[str, dict]:
    """Return artifact config for a built-in profile name."""
    if name == "triage":
        return _build_profile(_TRIAGE_ARTIFACTS, parse=True, retain=False)
    elif name == "standard":
        return _build_profile(_STANDARD_ARTIFACTS, parse=True, retain=False)
    elif name == "full":
        return _build_profile(_FULL_ARTIFACTS, parse=True, retain=True)
    else:
        raise ValueError(f"Unknown profile: {name}. Available: triage, standard, full")


PROFILES = {"triage": None, "standard": None, "full": None}  # Lazy — built on demand


# ---------------------------------------------------------------------------
# Config file I/O
# ---------------------------------------------------------------------------

CONFIG_MARKER = "forensickle_config"
CONFIG_VERSION = "1.0"


def load_config(path: str) -> dict[str, dict]:
    """Load and validate a Forensickle config JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data.get(CONFIG_MARKER):
        raise ValueError(f"Not a Forensickle config file (missing '{CONFIG_MARKER}')")
    if "version" not in data:
        raise ValueError("Config file missing 'version' field")
    if "artifacts" not in data or not isinstance(data["artifacts"], dict):
        raise ValueError("Config file missing or invalid 'artifacts' field")

    config = {}
    for aid, flags in data["artifacts"].items():
        caps = artifact_capabilities(aid)
        config[aid] = {
            "parse": bool(flags.get("parse", False)) and caps["can_parse"],
            "retain": bool(flags.get("retain", False)) and caps["can_retain"],
        }
    return config


def save_config(path: str, profile_name: str, artifact_config: dict[str, dict]) -> None:
    """Save artifact config as a Forensickle config JSON file."""
    data = {
        CONFIG_MARKER: True,
        "version": CONFIG_VERSION,
        "profile_name": profile_name,
        "artifacts": artifact_config,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log.info("Saved config to %s", path)


def load_profile(name_or_path: str) -> dict[str, dict]:
    """Load a profile by built-in name or JSON file path."""
    if name_or_path in PROFILES:
        return get_profile(name_or_path)
    if os.path.isfile(name_or_path):
        return load_config(name_or_path)
    raise ValueError(f"'{name_or_path}' is not a built-in profile or valid file path")
