"""Configuration for social media API credentials and workspace paths.

Set these environment variables or create a .env file:
- META_ACCESS_TOKEN: Your Meta (Facebook/Instagram) access token
- META_PAGE_ID: Your Facebook Page ID
- META_INSTAGRAM_ACCOUNT_ID: Your Instagram Business Account ID
- TIKTOK_ACCESS_TOKEN: Your TikTok API access token
- TIKTOK_OPEN_ID: Your TikTok Open ID
- ELBITAT_WORKSPACE: Custom workspace path (optional)
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SocialMediaConfig:
    """Configuration for social media API access."""
    
    # Meta (Facebook/Instagram)
    meta_access_token: str | None = None
    meta_page_id: str | None = None
    meta_instagram_account_id: str | None = None
    meta_pixel_id: str | None = None  # For Conversions API tracking
    
    # TikTok
    tiktok_access_token: str | None = None
    tiktok_open_id: str | None = None
    
    @classmethod
    def from_env(cls) -> "SocialMediaConfig":
        """Load configuration from environment variables."""
        return cls(
            meta_access_token=os.getenv("META_ACCESS_TOKEN"),
            meta_page_id=os.getenv("META_PAGE_ID"),
            meta_instagram_account_id=os.getenv("META_INSTAGRAM_ACCOUNT_ID"),
            meta_pixel_id=os.getenv("META_PIXEL_ID"),
            tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
            tiktok_open_id=os.getenv("TIKTOK_OPEN_ID"),
        )
    
    def is_meta_configured(self) -> bool:
        """Check if Meta API is configured."""
        return bool(
            self.meta_access_token 
            and self.meta_page_id 
            and self.meta_instagram_account_id
        )
    
    def is_tiktok_configured(self) -> bool:
        """Check if TikTok API is configured."""
        return bool(self.tiktok_access_token and self.tiktok_open_id)


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
