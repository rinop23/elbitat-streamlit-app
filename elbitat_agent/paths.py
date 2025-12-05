from __future__ import annotations

import os
from pathlib import Path


def get_workspace_path() -> Path:
    r"""Return the base workspace folder where JSON files will live.

    Default: ~/ElbitatAds (e.g. C:\Users\<user>\ElbitatAds on Windows)

    Can be overridden with the ELBITAT_WORKSPACE environment variable.
    """
    env = os.getenv("ELBITAT_WORKSPACE")
    if env:
        return Path(env).expanduser().resolve()
    # Default under user profile
    home = Path.home()
    return (home / "ElbitatAds").resolve()
