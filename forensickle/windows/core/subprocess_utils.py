"""Subprocess helper — suppresses console windows on Windows."""
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def run_silent(cmd, **kwargs):
    """Run a subprocess with no visible console window. Same API as subprocess.run."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)
