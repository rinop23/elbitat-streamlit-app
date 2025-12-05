"""Automated posting agent for Facebook using Meta Graph API."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

try:
    import requests
except ImportError:
    requests = None

from ..models import AdDraft
from ..config import SocialMediaConfig


class FacebookPoster:
    """Posts content directly to Facebook using Meta Graph API."""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: SocialMediaConfig):
        if not requests:
            raise ImportError("requests library required. Run: pip install requests")
        
        if not config.is_meta_configured():
            raise ValueError("Meta API not configured. Set META_ACCESS_TOKEN and META_PAGE_ID")
        
        self.access_token = config.meta_access_token
        self.page_id = config.meta_page_id
    
    def upload_images_and_post(
        self, 
        image_paths: List[Path], 
        message: str
    ) -> str:
        """Upload images and create a Facebook post.
        
        Args:
            image_paths: List of image file paths
            message: Post message/caption
            
        Returns:
            Published post ID
        """
        url = f"{self.BASE_URL}/{self.page_id}/photos"
        
        # Upload images
        attached_media = []
        for img_path in image_paths:
            with open(img_path, 'rb') as img_file:
                files = {'source': img_file}
                params = {
                    'access_token': self.access_token,
                    'published': 'false',  # Upload but don't publish yet
                }
                
                if requests:
                    response = requests.post(url, params=params, files=files)
                    response.raise_for_status()
                    photo_id = response.json()['id']
                    attached_media.append({'media_fbid': photo_id})
        
        # Create post with all images
        feed_url = f"{self.BASE_URL}/{self.page_id}/feed"
        post_params = {
            'message': message,
            'attached_media': attached_media,
            'access_token': self.access_token,
        }
        
        if requests:
            post_response = requests.post(feed_url, json=post_params)
            post_response.raise_for_status()
            return post_response.json()['id']
        
        return ""
    
    def post_from_draft(self, draft: AdDraft) -> Dict[str, str]:
        """Post directly from an AdDraft.
        
        Args:
            draft: The ad draft to post
            
        Returns:
            Dict with post ID and status
        """
        if "facebook" not in draft.request.platforms:
            return {"status": "skipped", "reason": "Facebook not in platforms"}
        
        facebook_content = draft.copy_by_platform.get("facebook", {})
        message = facebook_content.get("message", "")
        
        image_paths = [Path(img) for img in draft.selected_images]
        
        try:
            post_id = self.upload_images_and_post(image_paths, message)
            return {
                "status": "success",
                "post_id": post_id,
                "platform": "facebook"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "platform": "facebook"
            }
