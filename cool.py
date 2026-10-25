"""Run the original Cool English command-line application."""
from __future__ import annotations

import importlib.machinery
import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def _load_legacy_cli():
    if __package__:
        from .accounts import AccountManager
        from .cli import main
        from .repl import repl
    else:
        package = types.ModuleType("cool_app")
        package.__path__ = [str(PROJECT_DIR)]
        package.__package__ = "cool_app"
        package.__spec__ = importlib.machinery.ModuleSpec(
            "cool_app",
            loader=None,
            is_package=True,
        )
        package.__spec__.submodule_search_locations = [str(PROJECT_DIR)]
        sys.modules.setdefault("cool_app", package)

        from cool_app.accounts import AccountManager
        from cool_app.cli import main
        from cool_app.repl import repl
    return AccountManager, main, repl


def _run_legacy_cli() -> int:
    _, main, _ = _load_legacy_cli()
    cli_args = [arg for arg in sys.argv[1:] if arg not in ("--cli", "--gui-repl")]
    sys.argv = [sys.argv[0], *cli_args]
    main()
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_legacy_cli())
