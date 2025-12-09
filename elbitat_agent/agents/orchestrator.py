from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List
import json

from ..models import AdRequest, AdDraft
from ..file_storage import load_all_requests, save_draft
from ..config import get_workspace_path
from .creative_agent import generate_simple_draft


def generate_drafts_for_all_requests() -> List[AdDraft]:
    """Load all requests from the workspace and generate simple drafts."""
    requests = load_all_requests()
    drafts: List[AdDraft] = []
    for req in requests:
        draft = generate_simple_draft(req)
        save_draft(draft)
        drafts.append(draft)
    return drafts


def schedule_draft_for_publication(
    draft: AdDraft, publish_at: datetime | None = None
) -> Path:
    """Placeholder 'posting agent'.

    In the real system this would:
      - transform the draft into platform-specific API payloads
      - call Meta/TikTok APIs to schedule or publish

    For now we just save a JSON file into `scheduled/` so we can build and test
    the file-based pipeline.
    """
    base = get_workspace_path()
    scheduled_dir = base / "scheduled"
    scheduled_dir.mkdir(parents=True, exist_ok=True)

    safe_title = draft.request.title.replace(" ", "_").lower()
    filename = f"{safe_title}.scheduled.json"
    path = scheduled_dir / filename

    payload = {
        "draft": draft.to_dict(),
        "publish_at": publish_at.isoformat() if publish_at else None,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return path


def schedule_all_drafts(drafts: Iterable[AdDraft], publish_at: datetime | None = None):
    """Schedule a batch of drafts for publication (file-based placeholder)."""
    for draft in drafts:
        schedule_draft_for_publication(draft, publish_at=publish_at)
