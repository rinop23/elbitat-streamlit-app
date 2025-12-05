"""
Elbitat Social Agent - Streamlit Configuration

This file demonstrates how to load API credentials from environment variables
for secure deployment on Streamlit Cloud.
"""

import os
from elbitat_agent.config import SocialMediaConfig

def get_config() -> SocialMediaConfig:
    """
    Load configuration from environment variables (Streamlit secrets).
    
    On Streamlit Cloud, secrets are accessed via st.secrets or environment variables.
    Locally, they can be loaded from .env or set manually.
    """
    return SocialMediaConfig(
        # Meta API Credentials
        meta_access_token=os.getenv("META_ACCESS_TOKEN"),
        meta_instagram_account_id=os.getenv("META_INSTAGRAM_ACCOUNT_ID"),
        meta_pixel_id=os.getenv("META_PIXEL_ID"),
        
        # TikTok API Credentials (optional)
        tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
        tiktok_open_id=os.getenv("TIKTOK_OPEN_ID"),
    )

# Example usage in streamlit_app.py:
# from config_loader import get_config
# config = get_config()
