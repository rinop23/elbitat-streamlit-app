from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from .models import AdRequest, AdDraft
from .paths import get_workspace_path

# Import database functions
try:
    from .database import (
        init_database,
        save_request_to_db, get_all_requests as get_requests_from_db, delete_request_from_db,
        save_draft_to_db, get_all_drafts as get_drafts_from_db, delete_draft_from_db,
        save_scheduled_post_to_db, get_all_scheduled_posts as get_scheduled_from_db, 
        delete_scheduled_post_from_db
    )
    USE_DATABASE = True
    # Initialize database on import
    init_database()
except Exception as e:
    print(f"Database not available, using file storage: {e}")
    USE_DATABASE = False


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
        # Sanitize filename: remove/replace problematic characters
        safe_title = draft.request.title.replace(" ", "_").replace("/", "_").replace("\\", "_").lower()
        # Remove any other path separators or special chars
        safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in safe_title)
        filename = f"{safe_title}.draft.json"

    # Ensure filename doesn't create subdirectories
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Save to database if available
    draft_dict = draft.to_dict()
    if USE_DATABASE:
        save_draft_to_db(filename, draft_dict)
    
    # Also save to file system as backup
    path = drafts_dir / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(draft_dict, f, indent=2, ensure_ascii=False)
    return path


def load_all_drafts() -> List[Dict]:
    """Load all drafts from database or file system."""
    if USE_DATABASE:
        try:
            return get_drafts_from_db()
        except Exception as e:
            print(f"Error loading from database, falling back to files: {e}")
    
    # Fallback to file system
    _ensure_dirs()
    base = get_workspace_path()
    drafts_dir = base / "drafts"
    drafts = []
    
    for path in sorted(drafts_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                data['_filename'] = path.name
                drafts.append(data)
        except Exception as e:
            print(f"Error loading {path.name}: {e}")
    
    return drafts


def save_request(data: Dict, filename: str = None) -> bool:
    """Save a request to database and/or file system."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = data.get('title', 'request').replace(" ", "_").lower()
        safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in safe_title)
        filename = f"{safe_title}_{timestamp}.json"
    
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Save to database
    if USE_DATABASE:
        save_request_to_db(filename, data)
    
    # Also save to file system as backup
    _ensure_dirs()
    base = get_workspace_path()
    requests_dir = base / "requests"
    path = requests_dir / filename
    
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving request file: {e}")
        return USE_DATABASE  # Return True if saved to DB


def load_all_requests_dict() -> List[Dict]:
    """Load all requests as dictionaries from database or file system."""
    if USE_DATABASE:
        try:
            return get_requests_from_db()
        except Exception as e:
            print(f"Error loading requests from database: {e}")
    
    # Fallback to file system
    requests = []
    for path in list_request_files():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                data['_filename'] = path.name
                requests.append(data)
        except Exception as e:
            print(f"Error loading {path.name}: {e}")
    
    return requests


def save_scheduled_post(data: Dict, filename: str = None) -> bool:
    """Save a scheduled post to database and/or file system."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        service = data.get('service', 'post')
        filename = f"scheduled_{service}_{timestamp}.json"
    
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Save to database
    if USE_DATABASE:
        save_scheduled_post_to_db(filename, data)
    
    # Also save to file system as backup
    _ensure_dirs()
    base = get_workspace_path()
    scheduled_dir = base / "scheduled"
    path = scheduled_dir / filename
    
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving scheduled post file: {e}")
        return USE_DATABASE


def load_all_scheduled_posts() -> List[Dict]:
    """Load all scheduled posts from database or file system."""
    if USE_DATABASE:
        try:
            return get_scheduled_from_db()
        except Exception as e:
            print(f"Error loading from database: {e}")
    
    # Fallback to file system
    _ensure_dirs()
    base = get_workspace_path()
    scheduled_dir = base / "scheduled"
    posts = []
    
    for path in sorted(scheduled_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                data['_filename'] = path.name
                posts.append(data)
        except Exception as e:
            print(f"Error loading {path.name}: {e}")
    
    return posts


def delete_draft(filename: str) -> bool:
    """Delete a draft from database and file system."""
    success = True
    
    # Delete from database
    if USE_DATABASE:
        delete_draft_from_db(filename)
    
    # Delete from file system
    try:
        base = get_workspace_path()
        path = base / "drafts" / filename
        if path.exists():
            path.unlink()
    except Exception as e:
        print(f"Error deleting draft file: {e}")
        success = False
    
    return success


def delete_scheduled_post(filename: str) -> bool:
    """Delete a scheduled post from database and file system."""
    success = True
    
    # Delete from database
    if USE_DATABASE:
        delete_scheduled_post_from_db(filename)
    
    # Delete from file system
    try:
        base = get_workspace_path()
        path = base / "scheduled" / filename
        if path.exists():
            path.unlink()
    except Exception as e:
        print(f"Error deleting scheduled post file: {e}")
        success = False
    
    return success
