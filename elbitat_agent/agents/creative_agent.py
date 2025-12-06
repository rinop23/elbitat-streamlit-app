from __future__ import annotations

import os
from typing import Dict

from ..models import AdRequest, AdDraft
from ..media_selector import select_images_for_ad, copy_selected_images_to_workspace


def generate_ai_content(request: AdRequest) -> Dict[str, Dict[str, str]]:
    """Generate creative content using OpenAI."""
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        client = OpenAI(api_key=api_key)
        
        # Build prompt based on platforms
        platforms_str = ", ".join(request.platforms)
        
        prompt = f"""You are a professional social media content creator for Elbitat, a luxury hotel on Elba Island, Italy.

Create engaging social media content for the following campaign:

**Campaign Title:** {request.title}
**Goal:** {request.goal}
**Target Audience:** {request.audience or 'Travelers seeking authentic Italian experiences'}
**Platforms:** {platforms_str}
**Language:** {request.language}
**Brief:** {request.brief}

Generate platform-specific content with the following format:

For Instagram:
- Caption: Engaging caption (2-3 sentences, include emojis, conversational tone)
- Hashtags: 8-12 relevant hashtags (including #Elbitat #ElbaIsland)

For Facebook:
- Message: Detailed post (3-4 sentences, more informative)

For TikTok:
- Caption: Short catchy caption
- Script: Brief video script outline (3-4 scenes)

Make the content compelling, authentic, and aligned with the campaign goal of "{request.goal}"."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative social media content writer for a luxury Italian hotel. Write engaging, authentic content that drives bookings and engagement."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        ai_content = response.choices[0].message.content
        
        # Parse the AI response into structured format
        copy: Dict[str, Dict[str, str]] = {}
        
        if "instagram" in request.platforms:
            copy["instagram"] = parse_instagram_content(ai_content, request)
        
        if "facebook" in request.platforms:
            copy["facebook"] = parse_facebook_content(ai_content, request)
        
        if "tiktok" in request.platforms:
            copy["tiktok"] = parse_tiktok_content(ai_content, request)
        
        return copy
        
    except ImportError:
        print("OpenAI library not installed. Using placeholder content.")
        return generate_placeholder_content(request)
    except Exception as e:
        print(f"Error generating AI content: {e}. Using placeholder content.")
        return generate_placeholder_content(request)


def parse_instagram_content(ai_content: str, request: AdRequest) -> Dict[str, str]:
    """Parse Instagram content from AI response."""
    lines = ai_content.split('\n')
    caption = ""
    hashtags = "#Elbitat #ElbaIsland"
    
    for i, line in enumerate(lines):
        if 'caption:' in line.lower() or ('instagram' in line.lower() and i < len(lines) - 1):
            # Get next few lines as caption
            caption_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith('#') and 'hashtag' not in lines[j].lower():
                    caption_lines.append(lines[j].strip())
                elif lines[j].strip().startswith('#'):
                    break
            caption = ' '.join(caption_lines)
            break
    
    # Extract hashtags
    for line in lines:
        if line.strip().startswith('#'):
            hashtags = line.strip()
            break
        elif 'hashtag' in line.lower() and '#' in line:
            hashtags = line.split(':', 1)[1].strip() if ':' in line else line.strip()
            break
    
    if not caption:
        caption = f"✨ {request.title} ✨\n\n{request.brief[:100]}..."
    
    return {"caption": caption, "hashtags": hashtags}


def parse_facebook_content(ai_content: str, request: AdRequest) -> Dict[str, str]:
    """Parse Facebook content from AI response."""
    lines = ai_content.split('\n')
    message = ""
    
    for i, line in enumerate(lines):
        if 'facebook' in line.lower() and 'message' in line.lower():
            # Get next few lines as message
            message_lines = []
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].strip() and 'tiktok' not in lines[j].lower() and not lines[j].strip().startswith('#'):
                    message_lines.append(lines[j].strip())
            message = ' '.join(message_lines)
            break
    
    if not message:
        message = f"{request.title}\n\n{request.brief}\n\nBook your stay at Elbitat Hotel on Elba Island."
    
    return {"message": message}


def parse_tiktok_content(ai_content: str, request: AdRequest) -> Dict[str, str]:
    """Parse TikTok content from AI response."""
    lines = ai_content.split('\n')
    caption = ""
    script = ""
    
    for i, line in enumerate(lines):
        if 'tiktok' in line.lower():
            # Get caption and script
            for j in range(i + 1, min(i + 8, len(lines))):
                if 'caption' in lines[j].lower():
                    caption = lines[j].split(':', 1)[1].strip() if ':' in lines[j] else ""
                elif 'script' in lines[j].lower():
                    script_lines = []
                    for k in range(j + 1, min(j + 5, len(lines))):
                        if lines[k].strip():
                            script_lines.append(lines[k].strip())
                    script = '\n'.join(script_lines)
                    break
            break
    
    if not caption:
        caption = f"{request.title} 🏖️"
    if not script:
        script = f"Scene 1: Stunning view of Elbitat\nScene 2: {request.brief[:50]}\nScene 3: Call to action - book now!"
    
    return {"caption": caption, "script": script}


def generate_placeholder_content(request: AdRequest) -> Dict[str, Dict[str, str]]:
    """Generate simple placeholder content when OpenAI is not available."""
    copy: Dict[str, Dict[str, str]] = {}

    if "instagram" in request.platforms:
        copy["instagram"] = {
            "caption": f"[PLACEHOLDER IG] {request.title} — goal: {request.goal}\n\n{request.brief}",
            "hashtags": "#Elbitat #ElbaIsland #ItalianGetaway",
        }

    if "facebook" in request.platforms:
        copy["facebook"] = {
            "message": f"[PLACEHOLDER FB] {request.title} — goal: {request.goal}\n\n{request.brief}",
        }

    if "tiktok" in request.platforms:
        copy["tiktok"] = {
            "caption": f"[PLACEHOLDER TikTok] {request.title}",
            "script": "Intro shot, show Elbitat, then overlay text with the key message.",
        }
    
    return copy


def generate_simple_draft(request: AdRequest) -> AdDraft:
    """Generate draft with AI-powered content or placeholder if OpenAI not available."""
    
    # Try to generate AI content, fall back to placeholder
    copy = generate_ai_content(request)

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
