from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

from ..models import AdDraft
from ..paths import get_workspace_path


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
