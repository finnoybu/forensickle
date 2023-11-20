import sys
from modules.admin2 import is_admin, run_as_admin


def main():
    """
    This function checks if the script is running with administrative privileges. If not, it attempts to
    run the script with elevated privileges. After obtaining the necessary privileges, it determines
    whether to launch the GUI or operate as a command-line utility.

    Raises:
        OSError: If there's an error during administrative privilege check or execution.
    """

    try:
        if not is_admin():
            exit_code = run_as_admin(sys.executable, sys.argv)
            sys.exit(exit_code)
    except Exception as ex:
        raise OSError(f"An exception of type {type(ex).__name__} occurred: {ex}")


if __name__ == "__main__":
    main()
    input()
