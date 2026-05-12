"""Artifact: Environment Variables — system and user env vars from registry."""
import logging

from ..core.collector import SourceCollector
from ..core.registry_utils import read_registry_key
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:
    winreg = None

NAME = "environment_vars"
SYSTEM_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
USER_KEY = r"Environment"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live registry data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    if winreg is None:
        log.error("winreg not available")
        return result
    # System variables
    sys_vars = read_registry_key(winreg.HKEY_LOCAL_MACHINE, SYSTEM_KEY)
    for name, value in sys_vars.items():
        result.add_entry({"scope": "system", "name": name, "value": value})
    # Current user variables
    user_vars = read_registry_key(winreg.HKEY_CURRENT_USER, USER_KEY)
    for name, value in user_vars.items():
        result.add_entry({"scope": "user", "name": name, "value": value})
    return result
