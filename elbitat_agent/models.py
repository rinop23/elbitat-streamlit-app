from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class AdRequest:
    """Represents a high-level request for an ad or campaign."""

    title: str
    month: Optional[str] = None           # e.g. "2025-07"
    goal: str = "awareness"               # awareness | bookings | leads | engagement
    platforms: List[str] = field(default_factory=lambda: ["instagram", "facebook"])
    audience: Optional[str] = None
    language: str = "en"
    brief: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> "AdRequest":
        return cls(
            title=data.get("title", "Untitled"),
            month=data.get("month"),
            goal=data.get("goal", "awareness"),
            platforms=data.get("platforms", ["instagram", "facebook"]),
            audience=data.get("audience"),
            language=data.get("language", "en"),
            brief=data.get("brief", ""),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AdDraft:
    """Represents a concrete draft generated from a request.

    copy_by_platform:
        {
          "instagram": {"caption": "...", "hashtags": "..."},
          "facebook": {"message": "..."},
          "tiktok": {"caption": "...", "script": "..."}
        }
    
    selected_images: List of image file paths (relative or absolute)
    """

    request: AdRequest
    copy_by_platform: Dict[str, Dict[str, str]] = field(default_factory=dict)
    selected_images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "request": self.request.to_dict(),
            "copy_by_platform": self.copy_by_platform,
            "selected_images": self.selected_images,
        }
