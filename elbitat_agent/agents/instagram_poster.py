"""Automated posting agent for Instagram using Meta Graph API."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

try:
    import requests
except ImportError:
    requests = None

from ..models import AdDraft
from ..config import SocialMediaConfig


class InstagramPoster:
    """Posts content directly to Instagram using Meta Graph API."""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: SocialMediaConfig):
        if not requests:
            raise ImportError("requests library required. Run: pip install requests")
        
        if not config.is_meta_configured():
            raise ValueError("Meta API not configured. Set META_ACCESS_TOKEN, META_PAGE_ID, and META_INSTAGRAM_ACCOUNT_ID")
        
        self.access_token = config.meta_access_token
        self.page_id = config.meta_page_id
        self.instagram_account_id = config.meta_instagram_account_id
    
    def upload_image(self, image_path: Path) -> str:
        """Upload an image and return the media container ID.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Media container ID
        """
        url = f"{self.BASE_URL}/{self.instagram_account_id}/media"
        
        # For simplicity, assuming image is publicly accessible
        # In production, you'd upload to your own CDN first
        params = {
            "image_url": str(image_path),  # This needs to be a public URL
            "access_token": self.access_token,
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()["id"]
    
    def create_carousel_post(
        self, 
        image_paths: List[Path], 
        caption: str,
        hashtags: str = ""
    ) -> str:
        """Create a carousel post with multiple images.
        
        Args:
            image_paths: List of image file paths
            caption: Post caption
            hashtags: Hashtags to include
            
        Returns:
            Published post ID
        """
        # Step 1: Upload all images
        media_ids = []
        for img_path in image_paths[:10]:  # Instagram max 10 images
            media_id = self.upload_image(img_path)
            media_ids.append(media_id)
            time.sleep(1)  # Rate limiting
        
        # Step 2: Create carousel container
        url = f"{self.BASE_URL}/{self.instagram_account_id}/media"
        
        full_caption = f"{caption}\n\n{hashtags}".strip()
        
        params = {
            "caption": full_caption,
            "media_type": "CAROUSEL",
            "children": ",".join(media_ids),
            "access_token": self.access_token,
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        container_id = response.json()["id"]
        
        # Step 3: Publish the carousel
        publish_url = f"{self.BASE_URL}/{self.instagram_account_id}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        
        publish_response = requests.post(publish_url, params=publish_params)
        publish_response.raise_for_status()
        
        return publish_response.json()["id"]
    
    def post_from_draft(self, draft: AdDraft) -> Dict[str, str]:
        """Post directly from an AdDraft.
        
        Args:
            draft: The ad draft to post
            
        Returns:
            Dict with post ID and status
        """
        if "instagram" not in draft.request.platforms:
            return {"status": "skipped", "reason": "Instagram not in platforms"}
        
        instagram_content = draft.copy_by_platform.get("instagram", {})
        caption = instagram_content.get("caption", "")
        hashtags = instagram_content.get("hashtags", "")
        
        image_paths = [Path(img) for img in draft.selected_images]
        
        try:
            post_id = self.create_carousel_post(image_paths, caption, hashtags)
            return {
                "status": "success",
                "post_id": post_id,
                "platform": "instagram"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "platform": "instagram"
            }
