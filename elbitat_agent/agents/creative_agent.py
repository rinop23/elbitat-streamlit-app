from __future__ import annotations

import os
from typing import Dict

from ..models import AdRequest, AdDraft
from ..media_selector import select_images_for_ad, copy_selected_images_to_workspace


def generate_ai_content(request: AdRequest) -> Dict[str, Dict[str, str]]:
    """Generate creative content using OpenAI."""
    try:
        from openai import OpenAI
        
        # Try to get API key from Streamlit secrets first, then environment
        api_key = None
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
                api_key = st.secrets["OPENAI_API_KEY"]
        except:
            pass
        
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in secrets or environment variables")
        
        print(f"✅ Using OpenAI API (key starts with: {api_key[:15]}...)")
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
        print(f"📝 AI Generated Content:\n{ai_content[:200]}...\n")
        
        # Parse the AI response into structured format
        copy: Dict[str, Dict[str, str]] = {}
        
        if "instagram" in request.platforms:
            copy["instagram"] = parse_instagram_content(ai_content, request)
            print(f"✅ Instagram parsed: {copy['instagram']['caption'][:50]}...")
        
        if "facebook" in request.platforms:
            copy["facebook"] = parse_facebook_content(ai_content, request)
            print(f"✅ Facebook parsed: {copy['facebook']['message'][:50]}...")
        
        if "tiktok" in request.platforms:
            copy["tiktok"] = parse_tiktok_content(ai_content, request)
            print(f"✅ TikTok parsed: {copy['tiktok']['caption'][:30]}...")
        
        return copy
        
    except ImportError as e:
        print(f"⚠️ OpenAI library not installed: {e}. Using placeholder content.")
        return generate_placeholder_content(request)
    except ValueError as e:
        print(f"⚠️ OpenAI API key issue: {e}. Using placeholder content.")
        return generate_placeholder_content(request)
    except Exception as e:
        print(f"⚠️ Error generating AI content: {e}. Using placeholder content.")
        import traceback
        traceback.print_exc()
        return generate_placeholder_content(request)


def parse_instagram_content(ai_content: str, request: AdRequest) -> Dict[str, str]:
    """Parse Instagram content from AI response."""
    lines = ai_content.split('\n')
    caption = ""
    hashtags = ""
    
    # Find Instagram section (flexible matching)
    ig_start = -1
    for i, line in enumerate(lines):
        if 'instagram' in line.lower() and (line.startswith('##') or line.startswith('**') or ':' in line):
            ig_start = i
            break
    
    if ig_start >= 0:
        # Extract caption and hashtags
        in_caption = False
        in_hashtags = False
        
        for j in range(ig_start + 1, len(lines)):
            line = lines[j].strip()
            
            # Stop at divider or next platform
            if line.startswith('---') or (line.startswith('###') and any(p in line.lower() for p in ['facebook', 'tiktok'])):
                break
            
            # Check for caption marker
            if '**caption' in line.lower() and ':' in line:
                in_caption = True
                in_hashtags = False
                # Check if caption is on the same line
                text = line.split(':', 1)[1].strip()
                if text and not text.startswith('**'):
                    caption = text
                    in_caption = False
                continue
            
            # Check for hashtags marker
            if '**hashtag' in line.lower() and ':' in line:
                in_caption = False
                in_hashtags = True
                # Check if hashtags are on the same line
                text = line.split(':', 1)[1].strip()
                if text and text.startswith('#'):
                    hashtags = text
                    in_hashtags = False
                continue
            
            # Collect caption from next line(s) if not yet captured
            if in_caption and line and not caption:
                if not line.startswith('**') and not line.startswith('#'):
                    caption = line
                    in_caption = False
            
            # Collect hashtags from next line if not yet captured
            if in_hashtags and line:
                if line.startswith('#'):
                    hashtags = line
                    break
    
    # If hashtags weren't found separately, try to extract from caption
    if not hashtags and caption and '#' in caption:
        # Split caption and hashtags
        parts = caption.split('#', 1)
        if len(parts) == 2:
            caption = parts[0].strip()
            hashtags = '#' + parts[1]
    
    # Fallbacks
    if not caption or len(caption) < 20:
        caption = f"✨ {request.title} ✨\n\n{request.brief[:150] if len(request.brief) > 150 else request.brief}"
    
    if not hashtags:
        hashtags = "#Elbitat #ElbaIsland #ItalyTravel #WellnessRetreat"
    else:
        # Clean up hashtags
        hashtags = hashtags.replace('*', '').replace('###', '').strip()
    
    return {"caption": caption, "hashtags": hashtags}


def parse_facebook_content(ai_content: str, request: AdRequest) -> Dict[str, str]:
    """Parse Facebook content from AI response."""
    lines = ai_content.split('\n')
    message = ""
    
    # Find Facebook section
    fb_start = -1
    for i, line in enumerate(lines):
        if 'facebook' in line.lower():
            fb_start = i
            break
    
    if fb_start >= 0:
        # Extract message
        in_message = False
        
        for j in range(fb_start + 1, len(lines)):
            line = lines[j].strip()
            
            # Stop at divider or next platform
            if line.startswith('---') or (line.startswith('###') and 'tiktok' in line.lower()):
                break
            
            # Check for message marker
            if '**message' in line.lower() and ':' in line:
                in_message = True
                # Check if message is on the same line
                text = line.split(':', 1)[1].strip()
                if text and not text.startswith('**'):
                    message = text
                    break
                continue
            
            # Collect message from next line if not yet captured
            if in_message and line and not message:
                if not line.startswith('**') and not line.startswith('###') and not line.startswith('#'):
                    message = line
                    break
    
    # Fallback
    if not message or len(message) < 20:
        message = f"{request.title}\n\n{request.brief}\n\nDiscover the perfect blend of luxury and wellness at Elbitat Hotel on Elba Island. Book your transformative retreat today!"
    
    return {"message": message}


def parse_tiktok_content(ai_content: str, request: AdRequest) -> Dict[str, str]:
    """Parse TikTok content from AI response."""
    lines = ai_content.split('\n')
    caption = ""
    script = ""
    
    # Find TikTok section (flexible matching)
    tt_start = -1
    for i, line in enumerate(lines):
        if 'tiktok' in line.lower() and (line.startswith('##') or line.startswith('**') or ':' in line):
            tt_start = i
            break
    
    if tt_start >= 0:
        script_lines = []
        in_caption = False
        in_script = False
        
        for j in range(tt_start + 1, len(lines)):
            line = lines[j].strip()
            
            # Stop at divider
            if line.startswith('---'):
                break
            
            # Skip empty lines unless collecting script
            if not line and not in_script:
                continue
            
            # Check for caption marker
            if '**caption' in line.lower() and ':' in line:
                in_caption = True
                in_script = False
                # Check if caption is on same line
                text = line.split(':', 1)[1].strip().replace('**', '').strip()
                if text:  # Only if there's actual content, not just markdown
                    caption = text
                    in_caption = False
                continue
            
            # Collect caption from next line if not yet captured
            if in_caption and line and not caption:
                caption = line.replace('**', '').strip()
                in_caption = False
                continue
            
            # Check for script marker
            if ('**script' in line.lower() or 'script outline' in line.lower()) and ':' in line:
                in_caption = False
                in_script = True
                # Check if script text on same line
                text = line.split(':', 1)[1].strip()
                if text:
                    script_lines.append(text)
                continue
            
            # Collect script lines
            if in_script and line:
                # Skip ### headers but keep content
                if not line.startswith('###'):
                    script_lines.append(line)
        
        if script_lines:
            script = '\n'.join(script_lines)
    
    # Fallbacks
    if not caption or len(caption) < 10:
        caption = f"{request.title} 🏖️✨ #Elbitat #ElbaIsland"
    
    if not script or len(script) < 20:
        script = f"Scene 1: Stunning aerial view of Elbitat Hotel on Elba Island\nScene 2: {request.brief[:80]}\nScene 3: Close-up of luxury amenities\nScene 4: Call to action - Book your stay today!"
    
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
