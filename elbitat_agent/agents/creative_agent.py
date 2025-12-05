from __future__ import annotations

from typing import Dict

from ..models import AdRequest, AdDraft
from ..media_selector import select_images_for_ad, copy_selected_images_to_workspace


def generate_simple_draft(request: AdRequest) -> AdDraft:
    """Very simple placeholder creative agent.

    In the real system this is where you'd call OpenAI / ChatGPT to generate
    proper multi-language, multi-platform copy based on the request.

    For now we just create some basic text so the file pipeline works.
    """
    copy: Dict[str, Dict[str, str]] = {}

    if "instagram" in request.platforms:
        copy["instagram"] = {
            "caption": f"[DRAFT IG] {request.title} — goal: {request.goal}\n\n{request.brief}",
            "hashtags": "#Elbitat #ElbaIsland #Draft",
        }

    if "facebook" in request.platforms:
        copy["facebook"] = {
            "message": f"[DRAFT FB] {request.title} — goal: {request.goal}\n\n{request.brief}",
        }

    if "tiktok" in request.platforms:
        copy["tiktok"] = {
            "caption": f"[DRAFT TikTok] {request.title}",
            "script": "Intro shot, show Elbitat, then overlay text with the key message.",
        }

    # Select appropriate images (3-4 images per ad)
    num_images = 4 if "instagram" in request.platforms or "facebook" in request.platforms else 3
    selected_images = select_images_for_ad(
        brief=request.brief,
        goal=request.goal,
        num_images=num_images
    )
    
    # Copy images to workspace and get their paths
    if selected_images:
        workspace_images = copy_selected_images_to_workspace(selected_images, request.title)
        image_paths = [str(img) for img in workspace_images]
    else:
        image_paths = []

    return AdDraft(
        request=request, 
        copy_by_platform=copy,
        selected_images=image_paths
    )
