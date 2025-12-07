"""Marketing Strategist Agent - Creates comprehensive marketing plans."""

from __future__ import annotations
import os
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime, timedelta


def generate_marketing_plan(conversation_history: List[Dict[str, str]]) -> Dict:
    """Generate a comprehensive marketing plan based on conversation with user.
    
    Args:
        conversation_history: List of messages with 'role' and 'content'
        
    Returns:
        Marketing plan dictionary with strategy, timeline, and post specifications
    """
    try:
        import openai
        
        # Get API key from secrets or environment
        api_key = None
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            api_key = st.secrets['OPENAI_API_KEY']
        else:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        client = openai.OpenAI(api_key=api_key)
        
        # System prompt for marketing strategist
        system_prompt = """You are an expert marketing strategist specializing in wellness, hospitality, and holistic health campaigns.

Your role is to create comprehensive marketing plans based on conversations with clients. When creating a plan:

1. **Campaign Overview**: Define clear objectives, target audience, key messages
2. **Content Strategy**: Specify topics, themes, and content pillars
3. **Timeline**: Recommend posting frequency and duration
4. **Platform Strategy**: Recommend which platforms to use and why
5. **Service/Product Focus**: Identify which services/products to highlight in each phase
6. **Success Metrics**: Define KPIs and measurement approach

Output your marketing plan in this JSON structure:
{
  "campaign_name": "Name of the campaign",
  "overview": {
    "objective": "Primary goal",
    "duration_weeks": 8,
    "target_audience": "Description",
    "key_message": "Main message"
  },
  "content_strategy": {
    "themes": ["theme1", "theme2", "theme3"],
    "tone": "professional/casual/inspirational",
    "content_pillars": ["pillar1", "pillar2"]
  },
  "posting_schedule": {
    "frequency_per_week": 2,
    "platforms": ["Instagram", "Facebook"],
    "best_times": "Morning (9-11am)"
  },
  "posts": [
    {
      "week": 1,
      "post_number": 1,
      "focus_service": "Yoga Classes",
      "theme": "Introduction to Wellness",
      "goal": "Awareness",
      "suggested_content": "Brief description of what this post should cover",
      "platforms": ["Instagram", "Facebook"]
    }
  ]
}

Be specific, actionable, and data-driven in your recommendations."""

        # Build messages for API call
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        
        # Add final instruction to generate plan
        messages.append({
            "role": "user",
            "content": "Based on our conversation, please create a comprehensive marketing plan in the JSON format specified. Include specific posts with week numbers, themes, and services to highlight."
        })
        
        print("🎯 Generating marketing plan with GPT-4o-mini...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        plan_text = response.choices[0].message.content
        print(f"✅ Marketing plan generated: {len(plan_text)} characters")
        
        # Try to parse as JSON
        import json
        
        # Extract JSON from markdown code blocks if present
        if "```json" in plan_text:
            plan_text = plan_text.split("```json")[1].split("```")[0].strip()
        elif "```" in plan_text:
            plan_text = plan_text.split("```")[1].split("```")[0].strip()
        
        try:
            plan = json.loads(plan_text)
        except json.JSONDecodeError:
            # If not valid JSON, create structured plan from text
            plan = {
                "campaign_name": "Marketing Campaign",
                "overview": {
                    "objective": "Generated from conversation",
                    "duration_weeks": 8,
                    "target_audience": "Wellness seekers",
                    "key_message": "Holistic wellness"
                },
                "content_strategy": {
                    "themes": ["Wellness", "Self-care", "Transformation"],
                    "tone": "inspirational",
                    "content_pillars": ["Education", "Inspiration", "Community"]
                },
                "posting_schedule": {
                    "frequency_per_week": 2,
                    "platforms": ["Instagram", "Facebook"],
                    "best_times": "Morning (9-11am)"
                },
                "raw_plan": plan_text,
                "posts": []
            }
        
        return plan
        
    except Exception as e:
        print(f"❌ Error generating marketing plan: {str(e)}")
        raise


def convert_plan_to_post_requests(plan: Dict, start_date: datetime) -> List[Dict]:
    """Convert marketing plan posts into individual post request specifications.
    
    Args:
        plan: Marketing plan dictionary
        start_date: When to start the campaign
        
    Returns:
        List of post request dictionaries ready for content generation
    """
    post_requests = []
    
    overview = plan.get('overview', {})
    content_strategy = plan.get('content_strategy', {})
    posting_schedule = plan.get('posting_schedule', {})
    posts = plan.get('posts', [])
    
    frequency = posting_schedule.get('frequency_per_week', 2)
    platforms = posting_schedule.get('platforms', ['Instagram', 'Facebook'])
    
    # Calculate days between posts
    days_between_posts = 7 // frequency if frequency > 0 else 7
    
    for i, post_spec in enumerate(posts):
        # Calculate post date
        post_date = start_date + timedelta(days=i * days_between_posts)
        
        # Create post request
        request = {
            "title": f"{plan.get('campaign_name', 'Campaign')} - Post {i + 1}",
            "campaign_name": plan.get('campaign_name', 'Marketing Campaign'),
            "post_number": i + 1,
            "total_posts": len(posts),
            "scheduled_date": post_date.strftime("%Y-%m-%d"),
            "goal": post_spec.get('goal', overview.get('objective', 'Engagement')),
            "platforms": post_spec.get('platforms', platforms),
            "audience": overview.get('target_audience', 'Wellness seekers'),
            "language": "English",
            "featured_service": post_spec.get('focus_service', 'Wellness'),
            "theme": post_spec.get('theme', 'General'),
            "brief": f"""Marketing Campaign: {plan.get('campaign_name', 'Campaign')}

Week {post_spec.get('week', (i // frequency) + 1)} - Post {i + 1}/{len(posts)}

Theme: {post_spec.get('theme', 'General')}
Focus: {post_spec.get('focus_service', 'Wellness')}
Goal: {post_spec.get('goal', 'Engagement')}

Content Direction:
{post_spec.get('suggested_content', 'Create engaging content highlighting our wellness services.')}

Campaign Context:
- Objective: {overview.get('objective', 'Build awareness')}
- Target Audience: {overview.get('target_audience', 'Wellness seekers')}
- Key Message: {overview.get('key_message', 'Transform your wellness journey')}
- Tone: {content_strategy.get('tone', 'inspirational')}

Scheduled for: {post_date.strftime('%B %d, %Y')}"""
        }
        
        post_requests.append(request)
    
    return post_requests


def chat_with_marketing_agent(user_message: str, conversation_history: List[Dict[str, str]]) -> str:
    """Interactive conversation with marketing strategist to define campaign scope.
    
    Args:
        user_message: User's message
        conversation_history: Previous conversation
        
    Returns:
        Agent's response
    """
    try:
        import openai
        
        # Get API key
        api_key = None
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            api_key = st.secrets['OPENAI_API_KEY']
        else:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        client = openai.OpenAI(api_key=api_key)
        
        # System prompt for conversational strategist
        system_prompt = """You are a friendly and expert marketing strategist specializing in wellness, hospitality, and holistic health.

Your role is to have a conversation with clients to understand their marketing needs. Ask clarifying questions about:

1. **Campaign Goals**: What do they want to achieve? (awareness, bookings, engagement)
2. **Target Audience**: Who are they trying to reach?
3. **Services/Products**: What are they promoting? (yoga, massage, retreats, etc.)
4. **Timeline**: When should the campaign run? How long?
5. **Budget/Frequency**: How often can they post? (2-3 times/week, daily, etc.)
6. **Brand Voice**: Professional, casual, inspirational?
7. **Platforms**: Where should they post? (Instagram, Facebook, TikTok)

Be conversational, ask one or two questions at a time, and build understanding gradually. Show enthusiasm and expertise. When you have enough information, summarize what you've learned and ask if they're ready to see a detailed marketing plan."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}. Please try again."
