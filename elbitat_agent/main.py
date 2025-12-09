from __future__ import annotations

import argparse
from datetime import datetime
from typing import List
import json

from .file_storage import list_request_files, load_all_requests
from .agents.orchestrator import generate_drafts_for_all_requests
from .config import get_workspace_path


def cmd_list_requests() -> None:
    files = list_request_files()
    if not files:
        print("No requests found. Add JSON files into your workspace 'requests' folder.")
        return

    print("Requests in workspace:")
    for p in files:
        print(f"- {p.name}")


def cmd_generate_drafts() -> None:
    drafts = generate_drafts_for_all_requests()
    print(f"Generated {len(drafts)} draft(s). Check the 'drafts' folder in your workspace.")


def cmd_schedule_draft() -> None:
    """Prepare a draft for scheduled publication."""
    from .agents.orchestrator import schedule_all_drafts

    # For now, just schedule all drafts to demonstrate the workflow
    drafts = generate_drafts_for_all_requests()
    publish_time = datetime.now()  # In production, parse from args

    schedule_all_drafts(drafts, publish_at=publish_time)

    print(f"Scheduled {len(drafts)} draft(s) for publication.")
    print("Check the 'scheduled' folder in your workspace.")


def cmd_show_draft() -> None:
    """Show a formatted preview of a draft for review before posting."""
    base = get_workspace_path()
    drafts_dir = base / "drafts"
    
    if not drafts_dir.exists():
        print("No drafts folder found.")
        return
    
    drafts = sorted(drafts_dir.glob("*.json"))
    if not drafts:
        print("No drafts found.")
        return
    
    print("Available drafts:")
    for i, draft in enumerate(drafts, 1):
        print(f"{i}. {draft.stem}")


def cmd_check_api() -> None:
    """Check if API credentials are configured for automated posting."""
    from .agents.auto_poster import check_api_configuration
    
    print("\n=== API Configuration Status ===\n")
    
    status = check_api_configuration()
    
    print(f"Meta (Instagram/Facebook): {'✓ Configured' if status['meta_instagram_facebook'] else '✗ Not configured'}")
    print(f"TikTok:                    {'✓ Configured' if status['tiktok'] else '✗ Not configured'}")
    print(f"Requests library:          {'✓ Installed' if status['has_requests_library'] else '✗ Not installed'}")
    
    if not status['has_requests_library']:
        print("\nTo enable automated posting, run:")
        print("  pip install requests")
    
    if not status['meta_instagram_facebook']:
        print("\nTo configure Meta (Instagram/Facebook), set:")
        print("  META_ACCESS_TOKEN=your_token")
        print("  META_PAGE_ID=your_page_id")
        print("  META_INSTAGRAM_ACCOUNT_ID=your_ig_account_id")
    
    if not status['tiktok']:
        print("\nTo configure TikTok, set:")
        print("  TIKTOK_ACCESS_TOKEN=your_token")
        print("  TIKTOK_OPEN_ID=your_open_id")


def cmd_auto_post(draft_name: str, platforms: List[str] | None = None) -> None:
    """Automatically post a draft to social media platforms."""
    from .agents.auto_poster import auto_post_draft
    from .models import AdDraft
    
    base = get_workspace_path()
    draft_file = base / "drafts" / f"{draft_name}.draft.json"
    
    if not draft_file.exists():
        # Try without .draft suffix
        draft_file = base / "drafts" / f"{draft_name}.json"
    
    if not draft_file.exists():
        print(f"Error: Draft not found: {draft_name}")
        print("\nAvailable drafts:")
        cmd_show_draft()
        return
    
    # Load draft
    with draft_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    from .models import AdRequest
    draft = AdDraft(
        request=AdRequest.from_dict(data["request"]),
        copy_by_platform=data["copy_by_platform"],
        selected_images=data.get("selected_images", [])
    )
    
    print(f"\n🚀 Auto-posting: {draft.request.title}")
    print(f"Platforms: {', '.join(platforms or draft.request.platforms)}\n")
    
    results = auto_post_draft(draft, platforms)
    
    # Display results
    print("\n=== Posting Results ===\n")
    for platform, result in results.items():
        status = result.get("status", "unknown")
        if status == "success":
            print(f"✓ {platform.upper()}: Posted successfully (ID: {result.get('post_id', 'N/A')})")
        elif status == "not_configured":
            print(f"⚠ {platform.upper()}: {result.get('reason', 'Not configured')}")
        elif status == "error":
            print(f"✗ {platform.upper()}: Error - {result.get('error', 'Unknown error')}")
        elif status == "skipped":
            print(f"- {platform.upper()}: {result.get('reason', 'Skipped')}")
    
    print(f"\nResults saved to: {base / 'posted' / f'{draft_name}.posted.json'}")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Elbitat social media agent with automated posting")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-requests", help="List all ad request JSON files in the workspace")
    sub.add_parser("generate-drafts", help="Generate drafts with intelligent image selection")
    sub.add_parser("schedule-drafts", help="Schedule drafts for publication (placeholder)")
    sub.add_parser("show-drafts", help="List all generated drafts")
    sub.add_parser("check-api", help="Check API configuration status for automated posting")
    
    post_parser = sub.add_parser("auto-post", help="Automatically post a draft to social media")
    post_parser.add_argument("draft_name", help="Name of the draft to post (without .json extension)")
    post_parser.add_argument("--platforms", nargs="+", help="Specific platforms to post to (instagram, facebook, tiktok)")

    args = parser.parse_args(argv)

    if args.command == "list-requests":
        cmd_list_requests()
    elif args.command == "generate-drafts":
        cmd_generate_drafts()
    elif args.command == "schedule-drafts":
        cmd_schedule_draft()
    elif args.command == "show-drafts":
        cmd_show_draft()
    elif args.command == "check-api":
        cmd_check_api()
    elif args.command == "auto-post":
        cmd_auto_post(args.draft_name, args.platforms)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
