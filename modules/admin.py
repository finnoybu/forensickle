import os
import psutil
import subprocess

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
        if psutil.WINDOWS:
            # On Windows, build a space-separated string of command-line arguments
            string_command_line = " ".join(command_line)

            # Execute the process with UAC elevation
            process_info = shell.ShellExecuteEx(
                nShow=win32con.SW_SHOWNORMAL,
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",  # causes UAC elevation prompt
                lpFile=process_path,
                lpParameters=string_command_line,
            )

            process_handle = process_info["hProcess"]
            _ = win32event.WaitForSingleObject(process_handle, win32event.INFINITE)

            exit_code = win32process.GetExitCodeProcess(process_handle)
        elif psutil.MACOS:
            # On macOS, run 'sudo -k' to invalidate any previous sudo authentication
            invalidate_command = ["sudo", "-k"]
            subprocess.call(invalidate_command)

            # Create the final command by prepending 'sudo' to the process and its arguments
            final_command = ["sudo"] + [process_path] + command_line

            # Run the process with elevated privileges
            exit_code = subprocess.call(final_command)
    except Exception as e:
        raise OSError(f"Error running as administrator: {e}")

    return exit_code
