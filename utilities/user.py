import os
import ctypes


def is_admin():
    """
    Check if the current user has administrative privileges.

    This function checks whether the current user has administrative privileges on
    the system. It uses platform-specific methods to determine the user's
    administrative status.

    Returns:
        bool: True if the user has administrative privileges, False otherwise.

    Examples:
        1. On a Unix-based system with superuser privileges (UID is 0):
           ```python
           >>> is_admin()
           True
           ```

        2. On a Unix-based system without superuser privileges (UID is not 0):
           ```python
           >>> is_admin()
           False
           ```

        3. On a Windows system with administrative privileges:
           ```python
           >>> is_admin()
           True
           ```

        4. On a Windows system without administrative privileges:
           ```python
           >>> is_admin()
           False
           ```

    PEP 8 Compliance:
        - Function name is in lowercase with words separated by underscores.
        - Proper use of whitespace and indentation as per PEP 8 guidelines.

    See Also:
        - `os.getuid()`: Function for retrieving the user's UID on Unix-based systems.
        - `ctypes.windll.shell32.IsUserAnAdmin()`: Windows-specific function for checking administrative status.

    """
    try:
        # On Unix-based systems, use os.getuid() to check if the user's UID is 0,
        # which typically indicates root or superuser privileges.
        is_admin = os.getuid() == 0
    except AttributeError:
        # On Windows, use ctypes.windll.shell32.IsUserAnAdmin() function to check
        # if the user is an administrator.
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    return is_admin
