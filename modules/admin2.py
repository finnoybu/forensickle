import os
import psutil
import subprocess

import sys

if psutil.WINDOWS:
    import ctypes
    import win32con
    import win32event
    import win32process
    from win32comext.shell import shell, shellcon


def is_admin():
    """
    Check if the current user has administrative privileges.

    Returns:
        bool: True if the user has administrative privileges, False otherwise.
    """

    if psutil.WINDOWS:
        try:
            # On Windows, check if the user has administrative privileges using the IsUserAnAdmin function
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except OSError as e:
            raise OSError(f"Error checking administrative privileges: {e}")
    else:
        # On non-Windows platforms, check if the user has root (superuser) access
        is_admin = os.getuid() == 0

    return is_admin


def run_as_admin(process_path, command_line):
    """
    Run a process with administrative privileges using UAC elevation on Windows or sudo on macOS/Linux.

    Args:
        process_path (str): The path to the executable process.
        command_line (list): List of command-line arguments.

    Returns:
        int: The exit code of the process.

    Raises:
        OSError: If there's an error while executing the process.

    Note:
        - On Windows, UAC elevation is used to run the process.
        - On macOS and Linux, sudo is used for elevated privileges.
    """

    exit_code = 0  # Default exit code

    try:
        if sys.platform.startswith('win'):
            # Check if running with admin rights
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("This script requires elevated permissions. Please run as administrator.")
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0)

            # Launch the command in a new elevated command window
            subprocess.Popen(["cmd", "/k", "start", "cmd", "/c", f'"{process_path}"'] + command_line, shell=True)
            sys.exit(0)
        elif sys.platform.startswith('darwin'):
            # On macOS, run 'sudo -k' to invalidate any previous sudo authentication
            invalidate_command = ["sudo", "-k"]
            subprocess.call(invalidate_command)

            # Create the final command by prepending 'sudo' to the process and its arguments
            final_command = ["sudo"] + [process_path] + command_line

            # Run the process with elevated privileges
            exit_code = subprocess.call(final_command)
        elif sys.platform.startswith('linux'):
            # Linux specific handling here
            pass
    except Exception as e:
        raise OSError(f"Error running as administrator: {e}")

    return exit_code