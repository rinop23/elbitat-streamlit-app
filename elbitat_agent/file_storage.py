from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import AdRequest, AdDraft
from .paths import get_workspace_path


def _ensure_dirs() -> None:
    base = get_workspace_path()
    for sub in ["config", "requests", "drafts", "scheduled", "posted", "logs"]:
        (base / sub).mkdir(parents=True, exist_ok=True)


def list_request_files() -> List[Path]:
    _ensure_dirs()
    base = get_workspace_path()
    req_dir = base / "requests"
    return sorted(req_dir.glob("*.json"))


def load_request(path: Path) -> AdRequest:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return AdRequest.from_dict(data)
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse {path.name}: {e}")
        raise
    except Exception as e:
        print(f"Warning: Error loading {path.name}: {e}")
        raise


def load_all_requests() -> List[AdRequest]:
    return [load_request(p) for p in list_request_files()]


def save_draft(draft: AdDraft, filename: str | None = None) -> Path:
    _ensure_dirs()
    base = get_workspace_path()
    drafts_dir = base / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        safe_title = draft.request.title.replace(" ", "_").lower()
        filename = f"{safe_title}.draft.json"

    path = drafts_dir / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(draft.to_dict(), f, indent=2, ensure_ascii=False)
    return path
