"""Media selection module for choosing appropriate images from Foto Elbitat library.

The system automatically selects 3-4 images per ad based on:
- Keywords in the ad brief (sunset, hotel, beach, romantic, etc.)
- Campaign goal and target audience
- Available images in Elbitat/ and Sunset/ folders

Selected images are copied to the workspace media folder for each campaign.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import List

from .paths import get_workspace_path


def get_media_library_path() -> Path:
    """Return the path to the Foto Elbitat media library."""
    # Navigate from workspace root to the project's Foto Elbitat folder
    # Assume this script is in elbitat_agent/ and Foto Elbitat/ is at project root
    module_dir = Path(__file__).parent
    project_root = module_dir.parent
    return project_root / "Foto Elbitat"


def list_media_files(category: str | None = None) -> List[Path]:
    """List all image files in the media library.
    
    Args:
        category: Optional subfolder name ("Elbitat", "Sunset", etc.)
                 If None, searches all subdirectories.
    
    Returns:
        List of paths to image files (jpeg/jpg only, excludes MOV files)
    """
    media_path = get_media_library_path()
    
    if not media_path.exists():
        return []
    
    image_extensions = {'.jpeg', '.jpg', '.png'}
    images: List[Path] = []
    
    if category:
        category_path = media_path / category
        if category_path.exists():
            for file in category_path.iterdir():
                if file.is_file() and file.suffix.lower() in image_extensions:
                    images.append(file)
    else:
        # Search all subdirectories
        for subdir in media_path.iterdir():
            if subdir.is_dir():
                for file in subdir.iterdir():
                    if file.is_file() and file.suffix.lower() in image_extensions:
                        images.append(file)
    
    return sorted(images)


def select_images_for_ad(
    brief: str,
    goal: str = "awareness",
    num_images: int = 4,
    prefer_category: str | None = None
) -> List[Path]:
    """Select appropriate images for an ad based on the brief and goal.
    
    This is a simple rule-based selector. In production, you might use:
    - AI vision models to analyze image content
    - Embeddings to match images to brief semantics
    - User preferences and performance history
    
    Args:
        brief: The ad brief text
        goal: Campaign goal (awareness, bookings, etc.)
        num_images: Number of images to select (3-4 recommended)
        prefer_category: Preferred category to prioritize
    
    Returns:
        List of selected image paths
    """
    brief_lower = brief.lower()
    
    # Determine which category to prioritize based on brief keywords
    if prefer_category:
        primary_category = prefer_category
    elif any(word in brief_lower for word in ['sunset', 'romantic', 'evening', 'view', 'panorama', 'vista']):
        primary_category = "Sunset"
    elif any(word in brief_lower for word in ['yoga', 'wellness', 'spa', 'relaxation', 'meditation', 'retreat', 
                                               'hotel', 'room', 'property', 'facility', 'amenity', 
                                               'pool', 'terrace', 'restaurant', 'suite']):
        primary_category = "Elbitat"
    else:
        # Mix from both categories
        primary_category = None
    
    if primary_category:
        # Get images from preferred category
        primary_images = list_media_files(primary_category)
        other_category = "Elbitat" if primary_category == "Sunset" else "Sunset"
        other_images = list_media_files(other_category)
        
        # Select mostly from primary, 1 from other for variety
        num_primary = max(num_images - 1, num_images * 3 // 4)
        num_other = num_images - num_primary
        
        selected = []
        if primary_images:
            selected.extend(random.sample(primary_images, min(num_primary, len(primary_images))))
        if other_images and num_other > 0:
            selected.extend(random.sample(other_images, min(num_other, len(other_images))))
    else:
        # Mix evenly from all categories
        all_images = list_media_files()
        if all_images:
            selected = random.sample(all_images, min(num_images, len(all_images)))
        else:
            selected = []
    
    return selected


def copy_selected_images_to_workspace(image_paths: List[Path], ad_title: str) -> List[Path]:
    """Copy selected images to the workspace media folder for the ad.
    
    Args:
        image_paths: List of source image paths
        ad_title: Title of the ad (used for subfolder naming)
    
    Returns:
        List of destination paths in the workspace
    """
    workspace = get_workspace_path()
    media_dir = workspace / "media" / ad_title.replace(" ", "_").lower()
    media_dir.mkdir(parents=True, exist_ok=True)
    
    destination_paths = []
    for img_path in image_paths:
        dest = media_dir / img_path.name
        if not dest.exists():
            import shutil
            shutil.copy2(img_path, dest)
        destination_paths.append(dest)
    
    return destination_paths
