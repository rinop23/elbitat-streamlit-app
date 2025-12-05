"""Automated posting agent for TikTok using TikTok for Business API."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

try:
    import requests
except ImportError:
    requests = None

from ..models import AdDraft
from ..config import SocialMediaConfig


class TikTokPoster:
    """Posts content directly to TikTok using TikTok for Business API."""
    
    BASE_URL = "https://open-api.tiktok.com"
    
    def __init__(self, config: SocialMediaConfig):
        if not requests:
            raise ImportError("requests library required. Run: pip install requests")
        
        if not config.is_tiktok_configured():
            raise ValueError("TikTok API not configured. Set TIKTOK_ACCESS_TOKEN and TIKTOK_OPEN_ID")
        
        self.access_token = config.tiktok_access_token
        self.open_id = config.tiktok_open_id
    
    def create_video_from_images(self, image_paths: list[Path]) -> Path:
        """Create a video from images (simplified placeholder).
        
        In production, you would:
        1. Use ffmpeg or moviepy to create a video from images
        2. Add transitions, effects, music
        3. Export to MP4
        
        Args:
            image_paths: List of image files
            
        Returns:
            Path to created video file
        """
        # Placeholder - in real implementation, create actual video
        # For now, return first image path as we'd need video creation library
        return image_paths[0]
    
    def upload_video(self, video_path: Path, caption: str, script: str = "") -> str:
        """Upload video to TikTok.
        
        Args:
            video_path: Path to video file
            caption: Video caption
            script: Optional video script/description
            
        Returns:
            Posted video ID
        """
        # Step 1: Initialize upload
        init_url = f"{self.BASE_URL}/share/video/upload/"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        init_data = {
            "open_id": self.open_id,
        }
        
        if requests:
            init_response = requests.post(init_url, headers=headers, json=init_data)
            init_response.raise_for_status()
            upload_url = init_response.json()["data"]["upload_url"]
            
            # Step 2: Upload video file
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                upload_response = requests.post(upload_url, files=files)
                upload_response.raise_for_status()
            
            # Step 3: Publish video
            publish_url = f"{self.BASE_URL}/share/video/publish/"
            
            full_caption = f"{caption}\n\n{script}".strip() if script else caption
            
            publish_data = {
                "open_id": self.open_id,
                "caption": full_caption,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            }
            
            publish_response = requests.post(publish_url, headers=headers, json=publish_data)
            publish_response.raise_for_status()
            
            return publish_response.json()["data"]["share_id"]
        
        return ""
    
    def post_from_draft(self, draft: AdDraft) -> Dict[str, str]:
        """Post directly from an AdDraft.
        
        Args:
            draft: The ad draft to post
            
        Returns:
            Dict with post ID and status
        """
        if "tiktok" not in draft.request.platforms:
            return {"status": "skipped", "reason": "TikTok not in platforms"}
        
        tiktok_content = draft.copy_by_platform.get("tiktok", {})
        caption = tiktok_content.get("caption", "")
        script = tiktok_content.get("script", "")
        
        image_paths = [Path(img) for img in draft.selected_images]
        
        try:
            # Convert images to video
            video_path = self.create_video_from_images(image_paths)
            
            # Upload to TikTok
            post_id = self.upload_video(video_path, caption, script)
            
            return {
                "status": "success",
                "post_id": post_id,
                "platform": "tiktok"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "platform": "tiktok"
            }
