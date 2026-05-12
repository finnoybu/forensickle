"""Forensickle — entry point for GUI and CLI modes."""
import logging
import os
import sys


def main():
    from forensickle.windows.core.elevation import ensure_admin
    ensure_admin()

    # CLI mode: --profile flag triggers headless run
    if "--profile" in sys.argv or "--list" in sys.argv:
        logging.basicConfig(
            level=logging.DEBUG if "-v" in sys.argv or "--verbose" in sys.argv else logging.INFO,
            format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        )
        from forensickle.windows.orchestrator import main as cli_main
        cli_main()
        return

    # GUI mode
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    from gui.app_window import ForensickleApp
    app = ForensickleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
