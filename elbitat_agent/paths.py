from __future__ import annotations

import os
import tempfile
from pathlib import Path


def get_workspace_path() -> Path:
    r"""Return the base workspace folder where JSON files will live.

    Default: ~/ElbitatAds (e.g. C:\Users\<user>\ElbitatAds on Windows)
    On cloud/restricted environments: Uses temp directory

    Can be overridden with the ELBITAT_WORKSPACE environment variable.
    """
    env = os.getenv("ELBITAT_WORKSPACE")
    if env:
        workspace = Path(env).expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace
    
    # Try home directory first
    try:
        home = Path.home()
        workspace = (home / "ElbitatAds").resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        # Test if we can write to it
        test_file = workspace / ".write_test"
        test_file.touch()
        test_file.unlink()
        return workspace
    except (PermissionError, OSError):
        # Fallback to temp directory for cloud environments
        temp_base = Path(tempfile.gettempdir())
        workspace = temp_base / "ElbitatAds"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace
