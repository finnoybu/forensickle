"""Administrator privilege check and UAC self-elevation."""
from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger(__name__)


def is_admin() -> bool:
    """Return True if the current process is running as Administrator."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        return False


def relaunch_as_admin() -> bool:
    """Re-launch the current process with UAC elevation.

    Returns True if the elevated process was started (caller should exit).
    Returns False if the user declined the UAC prompt or the call failed.
    """
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params_argv = sys.argv[1:]
    else:
        executable = sys.executable
        params_argv = sys.argv

    params = " ".join(f'"{a}"' if " " in a else a for a in params_argv)

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 1
        )
        return ret > 32
    except (AttributeError, OSError) as exc:
        log.error("UAC self-elevate failed: %s", exc)
        return False


def ensure_admin() -> None:
    """Verify the current process is elevated; self-elevate or exit.

    If already admin, returns silently. Otherwise attempts UAC self-elevation
    and exits this (non-elevated) process. If self-elevation fails or is
    declined, prints an error to stderr and exits with status 1.
    """
    if is_admin():
        return

    if relaunch_as_admin():
        sys.exit(0)

    print(
        "ERROR: Forensickle requires Administrator privileges.\n"
        "Please right-click and 'Run as administrator', or launch from an elevated terminal.",
        file=sys.stderr,
    )
    sys.exit(1)
