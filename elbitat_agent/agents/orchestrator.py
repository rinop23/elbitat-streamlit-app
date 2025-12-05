from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from ..models import AdRequest, AdDraft
from ..file_storage import load_all_requests, save_draft
from .creative_agent import generate_simple_draft
from .posting_agent import schedule_draft_for_publication


def generate_drafts_for_all_requests() -> List[AdDraft]:
    """Load all requests from the workspace and generate simple drafts."""
    requests = load_all_requests()
    drafts: List[AdDraft] = []
    for req in requests:
        draft = generate_simple_draft(req)
        save_draft(draft)
        drafts.append(draft)
    return drafts


def schedule_all_drafts(drafts: Iterable[AdDraft], publish_at: datetime | None = None):
    """Schedule a batch of drafts for publication (file-based placeholder)."""
    for draft in drafts:
        schedule_draft_for_publication(draft, publish_at=publish_at)
