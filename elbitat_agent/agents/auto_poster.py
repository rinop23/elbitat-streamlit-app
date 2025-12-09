"""Automated posting orchestrator - publishes to all platforms."""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict
import json

from ..models import AdDraft
from ..config import SocialMediaConfig, get_workspace_path

try:
    from .instagram_poster import InstagramPoster
    from .facebook_poster import FacebookPoster
    from .tiktok_poster import TikTokPoster
except ImportError:
    InstagramPoster = None
    FacebookPoster = None
    TikTokPoster = None


def auto_post_draft(draft: AdDraft, platforms: List[str] | None = None) -> Dict[str, Dict]:
    """Automatically post a draft to specified platforms.
    
    Args:
        draft: The ad draft to post
        platforms: List of platforms to post to (default: all in draft)
        
    Returns:
        Dict of results for each platform
    """
    config = SocialMediaConfig.from_env()
    results = {}
    
    target_platforms = platforms or draft.request.platforms
    
    # Instagram
    if "instagram" in target_platforms:
        if config.is_meta_configured() and InstagramPoster:
            try:
                poster = InstagramPoster(config)
                results["instagram"] = poster.post_from_draft(draft)
            except Exception as e:
                results["instagram"] = {
                    "status": "error",
                    "error": str(e),
                    "platform": "instagram"
                }
        else:
            results["instagram"] = {
                "status": "not_configured",
                "reason": "Meta API credentials not set",
                "platform": "instagram"
            }
    
    # Facebook
    if "facebook" in target_platforms:
        if config.is_meta_configured() and FacebookPoster:
            try:
                poster = FacebookPoster(config)
                results["facebook"] = poster.post_from_draft(draft)
            except Exception as e:
                results["facebook"] = {
                    "status": "error",
                    "error": str(e),
                    "platform": "facebook"
                }
        else:
            results["facebook"] = {
                "status": "not_configured",
                "reason": "Meta API credentials not set",
                "platform": "facebook"
            }
    
    # TikTok
    if "tiktok" in target_platforms:
        if config.is_tiktok_configured() and TikTokPoster:
            try:
                poster = TikTokPoster(config)
                results["tiktok"] = poster.post_from_draft(draft)
            except Exception as e:
                results["tiktok"] = {
                    "status": "error",
                    "error": str(e),
                    "platform": "tiktok"
                }
        else:
            results["tiktok"] = {
                "status": "not_configured",
                "reason": "TikTok API credentials not set",
                "platform": "tiktok"
            }
    
    # Save results to workspace
    _save_posting_results(draft, results)
    
    return results


def _save_posting_results(draft: AdDraft, results: Dict[str, Dict]) -> None:
    """Save posting results to the posted folder."""
    base = get_workspace_path()
    posted_dir = base / "posted"
    posted_dir.mkdir(parents=True, exist_ok=True)
    
    safe_title = draft.request.title.replace(" ", "_").lower()
    filename = f"{safe_title}.posted.json"
    path = posted_dir / filename
    
    payload = {
        "draft": draft.to_dict(),
        "results": results,
    }
    
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def check_api_configuration() -> Dict[str, bool]:
    """Check which APIs are properly configured.
    
    Returns:
        Dict with configuration status for each platform
    """
    config = SocialMediaConfig.from_env()
    
    return {
        "meta_instagram_facebook": config.is_meta_configured(),
        "tiktok": config.is_tiktok_configured(),
        "has_requests_library": InstagramPoster is not None,
    }
