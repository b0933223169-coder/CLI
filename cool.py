"""Portable launcher for running cool directly from this folder."""
from __future__ import annotations

import importlib.machinery
import sys
import types
from pathlib import Path


if __package__:
    from .cli import main
else:
    package_dir = Path(__file__).resolve().parent
    package = types.ModuleType("cool_app")
    package.__path__ = [str(package_dir)]
    package.__package__ = "cool_app"
    package.__spec__ = importlib.machinery.ModuleSpec(
        "cool_app",
        loader=None,
        is_package=True,
    )
    package.__spec__.submodule_search_locations = [str(package_dir)]
    sys.modules.setdefault("cool_app", package)
    from cool_app.cli import main


if __name__ == "__main__":
    main()
