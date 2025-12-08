"""Streamlit Web Application for Elbitat Social Media Agent.

Streamlit-based interface with authentication for:
- User login with credentials
- Chat with agent to create campaigns and marketing strategies
- Review and approve generated drafts
- View scheduled posts
- Configure API settings
"""

from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth
from pathlib import Path
from datetime import datetime, timedelta
import json
import yaml
from yaml.loader import SafeLoader
import copy

from elbitat_agent.paths import get_workspace_path
from elbitat_agent.file_storage import (
    load_all_requests, list_request_files,
    load_all_drafts, save_request, save_scheduled_post, delete_draft, delete_scheduled_post,
    load_all_scheduled_posts, load_all_requests_dict, save_draft_dict
)
from elbitat_agent.agents.orchestrator import generate_drafts_for_all_requests
from elbitat_agent.agents.auto_poster import auto_post_draft, check_api_configuration
from elbitat_agent.agents.email_finder import discover_contacts, bulk_save_contacts
from elbitat_agent.agents.email_campaigns import (
    send_campaign, send_test_email, get_default_templates, personalize_email
)
from elbitat_agent.database import (
    get_all_email_contacts, update_email_contact_status, delete_email_contact,
    save_email_campaign, get_all_email_campaigns
)
from elbitat_agent.models import AdRequest, AdDraft


# Page configuration
st.set_page_config(
    page_title="Elbitat Social Agent",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .draft-card {
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: white;
    }
    .success-msg {
        color: #28a745;
        font-weight: bold;
    }
    .error-msg {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Authentication Configuration
def load_auth_config():
    """Load authentication configuration from Streamlit secrets or YAML file."""
    # Try loading from Streamlit secrets first (for cloud deployment)
    if hasattr(st, 'secrets') and 'credentials' in st.secrets:
        return {
            'credentials': dict(st.secrets['credentials']),
            'cookie': {
                'expiry_days': 30,
                'key': 'elbitat_social_agent_cookie',
                'name': 'elbitat_auth_cookie'
            }
        }
    
    # Try loading from YAML file (for local development)
    config_file = Path(__file__).parent / ".streamlit" / "credentials.yaml"
    if config_file.exists():
        with open(config_file) as file:
            return yaml.load(file, Loader=SafeLoader)
    
    # Default configuration if neither exists
    return {
        'credentials': {
            'usernames': {
                'admin': {
                    'name': 'Administrator',
                    'password': '$2b$12$6cu1qsgrlyLIUoN6adH2nezrZbgfNp0.39dIFYSZZRwrl0ynWXZtq'  # 'admin123'
                },
                'elbitat': {
                    'name': 'Elbitat Team',
                    'password': '$2b$12$x047S/8YsNREG2neeDws3.Db3WmN.RTUDYV9lyzgde3inZ6V43PTC'  # 'elbitat2025'
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'elbitat_social_agent_cookie',
            'name': 'elbitat_auth_cookie'
        }
    }


def initialize_auth():
    """Initialize authentication system."""
    config = load_auth_config()
    
    # Convert to plain dict to avoid modifying read-only st.secrets
    # streamlit-authenticator tries to track failed login attempts by modifying the credentials dict
    if hasattr(config, 'to_dict'):
        config_dict = config.to_dict()
    else:
        # Manual conversion for nested secrets
        config_dict = {
            'credentials': {
                'usernames': {}
            },
            'cookie': {
                'name': str(config['cookie']['name']),
                'key': str(config['cookie']['key']),
                'expiry_days': int(config['cookie']['expiry_days'])
            }
        }
        # Copy usernames
        for username, user_data in config['credentials']['usernames'].items():
            config_dict['credentials']['usernames'][str(username)] = {
                'name': str(user_data['name']),
                'password': str(user_data['password'])
            }
    
    # Updated for streamlit-authenticator 0.4.x - removed preauthorized parameter
    authenticator = stauth.Authenticate(
        config_dict['credentials'],
        config_dict['cookie']['name'],
        config_dict['cookie']['key'],
        config_dict['cookie']['expiry_days']
    )
    
    return authenticator


# Initialize session state
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None


def show_login_page():
    """Display login page."""
    st.markdown('<p class="main-header">🔐 Elbitat Social Agent Login</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        authenticator = initialize_auth()
        
        # Updated for streamlit-authenticator 0.4.x - login() now modifies session_state directly
        authenticator.login(location='main')
        
        # Get values from session_state (set by authenticator)
        authentication_status = st.session_state.get('authentication_status')
        name = st.session_state.get('name')
        username = st.session_state.get('username')
        
        if authentication_status == False:
            st.error('Username/password is incorrect')
        elif authentication_status == None:
            st.warning('Please enter your username and password')
        
        if authentication_status:
            st.rerun()


def show_dashboard():
    """Display main dashboard."""
    st.markdown(f'<p class="main-header">📊 Dashboard</p>', unsafe_allow_html=True)
    
    # Get statistics
    api_status = check_api_configuration()
    workspace = get_workspace_path()
    
    drafts_count = len(list((workspace / "drafts").glob("*.json"))) if (workspace / "drafts").exists() else 0
    scheduled_count = len(list((workspace / "scheduled").glob("*.json"))) if (workspace / "scheduled").exists() else 0
    posted_count = len(list((workspace / "posted").glob("*.json"))) if (workspace / "posted").exists() else 0
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Drafts", drafts_count, "Ready for review")
    
    with col2:
        st.metric("📅 Scheduled", scheduled_count, "Approved posts")
    
    with col3:
        st.metric("✅ Posted", posted_count, "Published content")
    
    with col4:
        api_ok = api_status['meta_instagram_facebook'] or api_status['tiktok']
        st.metric("🔌 API Status", "Connected" if api_ok else "Not configured")
    
    st.divider()
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Create Campaign", use_container_width=True, key="quick_chat"):
            st.session_state.page = 'chat'
            st.rerun()
    
    with col2:
        if st.button("✨ Generate Drafts", use_container_width=True, key="quick_generate"):
            with st.spinner("Generating drafts..."):
                try:
                    drafts = generate_drafts_for_all_requests()
                    st.success(f"Generated {len(drafts)} draft(s)!")
                    st.session_state.page = 'drafts'
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating drafts: {str(e)}")
    
    with col3:
        if st.button("📝 Review Drafts", use_container_width=True, key="quick_drafts"):
            st.session_state.page = 'drafts'
            st.rerun()
    
    # Recent activity
    st.divider()
    st.subheader("📈 Recent Activity")
    
    if posted_count > 0:
        posted_dir = workspace / "posted"
        recent_posts = sorted(posted_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        
        for post_file in recent_posts:
            with open(post_file, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
                draft = post_data.get('draft', {})
                results = post_data.get('results', {})
                
                with st.expander(f"📱 {draft.get('request', {}).get('title', 'Untitled')}"):
                    st.write(f"**Posted:** {datetime.fromtimestamp(post_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
                    
                    for platform, result in results.items():
                        status = result.get('status', 'unknown')
                        if status == 'success':
                            st.success(f"✓ {platform.upper()}: Posted")
                        elif status == 'error':
                            st.error(f"✗ {platform.upper()}: {result.get('error', 'Error')}")
    else:
        st.info("No posts published yet. Create your first campaign!")


def show_marketing_strategy_page():
    """Display marketing strategist chat interface."""
    try:
        st.markdown('<p class="main-header">🎯 Marketing Strategy Assistant</p>', unsafe_allow_html=True)
        
        st.write("""
        Chat with our AI marketing strategist to create a comprehensive marketing plan. 
        Once your plan is ready, we'll automatically generate all the posts for you!
        """)
        
        # Initialize conversation history
        if 'marketing_conversation' not in st.session_state:
            st.session_state.marketing_conversation = []
        
        if 'marketing_plan' not in st.session_state:
            st.session_state.marketing_plan = None
        
        # Display conversation history
        st.subheader("💬 Conversation")
    
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.marketing_conversation:
                if msg['role'] == 'user':
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**Strategist:** {msg['content']}")
    
        # User input
        with st.form("marketing_chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Your message:",
                placeholder="Tell me about your marketing goals...",
                height=100,
                key="marketing_input"
            )
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                send_button = st.form_submit_button("💬 Send Message", use_container_width=True)
            
            with col2:
                generate_plan_button = st.form_submit_button("📋 Generate Marketing Plan", use_container_width=True)
            
            with col3:
                if st.form_submit_button("🔄 New Chat"):
                    st.session_state.marketing_conversation = []
                    st.session_state.marketing_plan = None
                    st.rerun()
    
        # Handle send message
        if send_button and user_input:
            from elbitat_agent.agents.marketing_strategist import chat_with_marketing_agent
            
            # Add user message
            st.session_state.marketing_conversation.append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response
            with st.spinner("🤔 Thinking..."):
                try:
                    response = chat_with_marketing_agent(
                        user_input,
                        st.session_state.marketing_conversation[:-1]  # Exclude the message we just added
                    )
                    
                    st.session_state.marketing_conversation.append({
                        "role": "assistant",
                        "content": response
                    })
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
        # Handle generate plan
        if generate_plan_button:
            if len(st.session_state.marketing_conversation) < 2:
                st.warning("Please have a conversation with the strategist first to define your campaign needs.")
            else:
                from elbitat_agent.agents.marketing_strategist import generate_marketing_plan
                
                with st.spinner("📊 Creating your comprehensive marketing plan..."):
                    try:
                        plan = generate_marketing_plan(st.session_state.marketing_conversation)
                        st.session_state.marketing_plan = plan
                        st.success("✅ Marketing plan generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating plan: {str(e)}")
    
        # Display marketing plan if generated
        if st.session_state.marketing_plan:
            st.divider()
            st.subheader("📋 Your Marketing Plan")
            
            plan = st.session_state.marketing_plan
            
            # Overview
            with st.expander("📊 Campaign Overview", expanded=True):
                overview = plan.get('overview', {})
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Campaign:** {plan.get('campaign_name', 'N/A')}")
                    st.write(f"**Objective:** {overview.get('objective', 'N/A')}")
                    st.write(f"**Target Audience:** {overview.get('target_audience', 'N/A')}")
                
                with col2:
                    st.write(f"**Duration:** {overview.get('duration_weeks', 'N/A')} weeks")
                    st.write(f"**Key Message:** {overview.get('key_message', 'N/A')}")
            
            # Content Strategy
            with st.expander("✍️ Content Strategy"):
                content = plan.get('content_strategy', {})
                st.write(f"**Tone:** {content.get('tone', 'N/A')}")
                st.write(f"**Themes:** {', '.join(content.get('themes', []))}")
                st.write(f"**Content Pillars:** {', '.join(content.get('content_pillars', []))}")
            
            # Posting Schedule
            with st.expander("📅 Posting Schedule"):
                schedule = plan.get('posting_schedule', {})
                st.write(f"**Frequency:** {schedule.get('frequency_per_week', 'N/A')} posts per week")
                st.write(f"**Platforms:** {', '.join(schedule.get('platforms', []))}")
                st.write(f"**Best Times:** {schedule.get('best_times', 'N/A')}")
            
            # Posts breakdown
            posts = plan.get('posts', [])
            if posts:
                with st.expander(f"📝 Planned Posts ({len(posts)} posts)"):
                    for i, post in enumerate(posts):
                        st.markdown(f"""
                        **Post {i+1}** - Week {post.get('week', 'N/A')}
                        - **Focus:** {post.get('focus_service', 'N/A')}
                        - **Theme:** {post.get('theme', 'N/A')}
                        - **Goal:** {post.get('goal', 'N/A')}
                        - **Content:** {post.get('suggested_content', 'N/A')}
                        """)
                        st.divider()
            
            # Raw plan if available
            if 'raw_plan' in plan:
                with st.expander("📄 Full Plan Details"):
                    st.text(plan['raw_plan'])
            
            # Action buttons
            st.divider()
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("✨ Generate All Posts Now", use_container_width=True, type="primary"):
                    from elbitat_agent.agents.marketing_strategist import convert_plan_to_post_requests
                    from elbitat_agent.file_storage import save_request
                    
                    with st.spinner("Creating post requests from marketing plan..."):
                        try:
                            # Get start date
                            start_date = datetime.now()
                            
                            # Convert plan to post requests
                            post_requests = convert_plan_to_post_requests(plan, start_date)
                            
                            # Save each request
                            workspace = get_workspace_path()
                            requests_dir = workspace / "requests"
                            requests_dir.mkdir(parents=True, exist_ok=True)
                            
                            for i, request_data in enumerate(post_requests):
                                filename = f"marketing_{plan.get('campaign_name', 'campaign').replace(' ', '_').lower()}_post{i+1:02d}.json"
                                request_file = requests_dir / filename
                                
                                with open(request_file, 'w', encoding='utf-8') as f:
                                    json.dump(request_data, f, indent=2, ensure_ascii=False)
                            
                            st.success(f"✅ Created {len(post_requests)} post requests!")
                            st.info("💡 Go to Dashboard and click 'Generate Drafts' to create the content.")
                            
                        except Exception as e:
                            st.error(f"Error creating posts: {str(e)}")
            
            with col2:
                if st.button("📝 Edit Plan", use_container_width=True):
                    st.info("Continue the conversation above to refine your plan, then regenerate.")
            
            with col3:
                if st.button("🗑️ Clear"):
                    st.session_state.marketing_plan = None
                    st.session_state.marketing_conversation = []
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error loading Marketing Strategy page: {str(e)}")
        st.info("Please try refreshing the page or contact support if the issue persists.")
        import traceback
        st.code(traceback.format_exc())


def show_chat_page():
    """Display chat interface for campaign creation."""
    st.markdown('<p class="main-header">💬 Create Campaign</p>', unsafe_allow_html=True)
    
    # Campaign type selector
    campaign_type = st.radio(
        "Campaign Type",
        ["Single Post", "Multi-Post Series"],
        horizontal=True,
        help="Single: One post. Multi-Post: Multiple posts over time"
    )
    
    # Campaign form
    with st.form("campaign_form"):
        st.subheader("Campaign Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Campaign Title*", placeholder="e.g., Holistic Wellness Launch")
            goal = st.selectbox("Campaign Goal", ["awareness", "bookings", "engagement", "leads"])
            audience = st.text_input("Target Audience", placeholder="e.g., Wellness seekers, yoga enthusiasts")
        
        with col2:
            platforms = st.multiselect(
                "Platforms*",
                ["instagram", "facebook", "tiktok"],
                default=["instagram", "facebook"]
            )
            language = st.selectbox("Language", ["en", "fr", "de", "it", "es"], index=0)
        
        # Multi-post series options
        if campaign_type == "Multi-Post Series":
            st.divider()
            st.subheader("📅 Campaign Schedule")
            
            col_date1, col_date2, col_freq = st.columns(3)
            with col_date1:
                start_date = st.date_input("Start Date*", datetime.now().date())
            with col_date2:
                end_date = st.date_input("End Date*", datetime.now().date() + timedelta(days=90))
            with col_freq:
                # Calculate weeks between dates
                if end_date > start_date:
                    weeks_diff = (end_date - start_date).days // 7
                    posts_per_week = st.selectbox(
                        "Posts per Week*",
                        [1, 2, 3, 4],
                        index=0,
                        help=f"Campaign runs {weeks_diff} weeks"
                    )
                    total_posts = weeks_diff * posts_per_week
                    st.info(f"📊 Total: ~{total_posts} posts")
                else:
                    posts_per_week = 1
            
            st.divider()
            st.subheader("🎯 Services/Products to Feature")
            
            services = st.text_area(
                "List Services (one per line)*",
                placeholder="Yoga Program\nHypopressive Gymnastics\nTraditional Thai Massage\nSound Healing\nPilates Sessions",
                height=120,
                help="Each service will be featured in rotation across posts"
            )
        else:
            start_date = datetime.now().date()
            end_date = start_date
            posts_per_week = 1
            services = ""
        
        brief = st.text_area(
            "Campaign Brief*",
            placeholder="Example: Launch holistic wellness program at Elbitat. Mediterranean version of Kamalaya Koh Samui. Feature yoga, Thai massage, sound harmonization, pilates. Target wellness seekers.",
            height=150
        )
        
        submitted = st.form_submit_button("✨ Generate Campaign", use_container_width=True)
        
        if submitted:
            if not title or not brief or not platforms:
                st.error("Please fill in all required fields (marked with *)")
            elif campaign_type == "Multi-Post Series" and (not services or end_date <= start_date):
                st.error("For multi-post campaigns, please provide services and valid date range")
            else:
                workspace = get_workspace_path()
                requests_dir = workspace / "requests"
                requests_dir.mkdir(parents=True, exist_ok=True)
                
                safe_title = title.replace(" ", "_").lower()
                
                # Parse services list
                service_list = [s.strip() for s in services.split('\n') if s.strip()] if services else []
                
                if campaign_type == "Multi-Post Series":
                    # Generate multiple requests - one for each post
                    weeks_count = (end_date - start_date).days // 7
                    total_posts = weeks_count * posts_per_week
                    
                    with st.spinner(f"Creating {total_posts} campaign posts..."):
                        for post_num in range(total_posts):
                            # Calculate post date
                            days_offset = (post_num * 7) // posts_per_week
                            post_date = start_date + timedelta(days=days_offset)
                            
                            # Rotate through services
                            featured_service = service_list[post_num % len(service_list)] if service_list else "wellness"
                            
                            # Create unique request for this post
                            request_file = requests_dir / f"{safe_title}_post{post_num+1:02d}.json"
                            
                            request_data = {
                                "title": f"{title} - Post {post_num+1}/{total_posts}",
                                "campaign_series": title,
                                "post_number": post_num + 1,
                                "total_posts": total_posts,
                                "scheduled_date": post_date.strftime("%Y-%m-%d"),
                                "goal": goal,
                                "platforms": platforms,
                                "audience": audience,
                                "language": language,
                                "featured_service": featured_service,
                                "all_services": service_list,
                                "brief": f"{brief}\n\nPost {post_num+1}/{total_posts} - Focus: {featured_service}\nScheduled for: {post_date.strftime('%B %d, %Y')}"
                            }
                            
                            with open(request_file, 'w', encoding='utf-8') as f:
                                json.dump(request_data, f, indent=2, ensure_ascii=False)
                        
                        st.success(f"✅ Created {total_posts} posts spanning {weeks_count} weeks!")
                        st.info(f"📅 {start_date.strftime('%b %d')} → {end_date.strftime('%b %d, %Y')} | {posts_per_week} post(s)/week")
                        st.balloons()
                else:
                    # Single post campaign
                    request_file = requests_dir / f"{safe_title}.json"
                    
                    request_data = {
                        "title": title,
                        "month": start_date.strftime("%Y-%m"),
                        "goal": goal,
                        "platforms": platforms,
                        "audience": audience,
                        "language": language,
                        "brief": brief
                    }
                    
                    with open(request_file, 'w', encoding='utf-8') as f:
                        json.dump(request_data, f, indent=2, ensure_ascii=False)
                    
                    st.success(f"✅ Campaign request created!")
                    st.balloons()
                
                # Generate drafts for all saved requests
                with st.spinner("🎨 Generating content with AI..."):
                    try:
                        drafts = generate_drafts_for_all_requests()
                        
                        if len(drafts) == 0:
                            st.warning("⚠️ Campaign request(s) saved, but no drafts were generated yet.")
                        else:
                            st.success(f"✅ Generated {len(drafts)} draft(s)!")
                            st.info("Go to 'Drafts' page to review and approve your content.")
                            
                            # Automatically navigate to drafts page
                            st.session_state['page'] = 'drafts'
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error generating drafts: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())


def show_drafts_page():
    """Display drafts review and approval page."""
    st.markdown('<p class="main-header">📝 Review & Approve Drafts</p>', unsafe_allow_html=True)
    
    workspace = get_workspace_path()
    drafts_dir = workspace / "drafts"
    
    if not drafts_dir.exists():
        st.info("No drafts available. Create a campaign first!")
        return
    
    draft_files = sorted(drafts_dir.glob("*.json"))
    
    if not draft_files:
        st.info("No drafts available. Create a campaign first!")
        if st.button("💬 Create Campaign"):
            st.session_state['page'] = 'chat'
            st.rerun()
        return
    
    # Display drafts in grid
    cols = st.columns(3)
    
    for idx, draft_file in enumerate(draft_files):
        with cols[idx % 3]:
            with open(draft_file, 'r', encoding='utf-8') as f:
                draft_data = json.load(f)
            
            request = draft_data['request']
            
            with st.container():
                st.markdown(f"### {request['title']}")
                st.write(f"**Month:** {request.get('month', 'N/A')}")
                st.write(f"**Goal:** {request['goal']}")
                st.write(f"**Platforms:** {', '.join(request['platforms'])}")
                
                # Brief preview
                brief = request.get('brief', '')
                if len(brief) > 100:
                    st.write(f"{brief[:100]}...")
                else:
                    st.write(brief)
                
                # Review button
                if st.button(f"👁️ Review", key=f"review_{draft_file.stem}"):
                    st.session_state['selected_draft'] = draft_file.stem
                    st.session_state['show_draft_detail'] = True
                    st.rerun()
    
    # Show draft detail modal
    if st.session_state.get('show_draft_detail'):
        show_draft_detail_modal()


def show_draft_detail_modal():
    """Display detailed draft view in modal-like container."""
    draft_name = st.session_state.get('selected_draft')
    workspace = get_workspace_path()
    draft_file = workspace / "drafts" / f"{draft_name}.json"
    
    if not draft_file.exists():
        st.error("Draft not found")
        return
    
    with open(draft_file, 'r', encoding='utf-8') as f:
        draft_data = json.load(f)
    
    request = draft_data['request']
    copy_by_platform = draft_data['copy_by_platform']
    selected_images = draft_data.get('selected_images', [])
    
    # Header with close button
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"## 📄 {request['title']}")
    with col2:
        if st.button("❌ Close"):
            st.session_state['show_draft_detail'] = False
            st.rerun()
    
    st.divider()
    
    # Two column layout
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("Campaign Info")
        st.write(f"**Month:** {request.get('month', 'N/A')}")
        st.write(f"**Goal:** {request['goal']}")
        st.write(f"**Platforms:** {', '.join(request['platforms'])}")
        st.write(f"**Audience:** {request.get('audience', 'General')}")
        
        st.subheader("Brief")
        st.write(request.get('brief', ''))
        
        st.subheader(f"Selected Images ({len(selected_images)})")
        if selected_images:
            # Display images in a grid
            img_cols = st.columns(2)
            for idx, img_path in enumerate(selected_images):
                with img_cols[idx % 2]:
                    if Path(img_path).exists():
                        st.image(str(img_path), use_container_width=True)
        else:
            st.info("No images selected")
    
    with col_right:
        # Edit mode toggle
        edit_mode = st.checkbox("✏️ Edit Mode", key=f"edit_mode_{draft_name}")
        
        if edit_mode:
            st.info("💬 **AI Assistant:** Tell me what you'd like to change about the content or images!")
            
            # AI conversation for edits
            user_feedback = st.text_area(
                "What would you like to change?",
                placeholder="e.g., 'Make the Facebook post more engaging' or 'Change images to sunset views'",
                height=100,
                key=f"feedback_{draft_name}"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 Regenerate Content", key=f"regen_{draft_name}", use_container_width=True):
                    if user_feedback:
                        with st.spinner("🎨 Regenerating content with AI..."):
                            # Import here to avoid circular import
                            from elbitat_agent.agents.creative_agent import generate_ai_content
                            from elbitat_agent.models import AdRequest
                            
                            # Create updated request with feedback
                            updated_request = AdRequest.from_dict(request)
                            updated_request.brief = f"{request['brief']}\n\nADDITIONAL INSTRUCTIONS: {user_feedback}"
                            
                            try:
                                new_copy = generate_ai_content(updated_request)
                                draft_data['copy_by_platform'] = new_copy
                                
                                # Save updated draft to database
                                save_draft_dict(draft_data, draft_file.name)
                                
                                st.success("✅ Content regenerated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error regenerating content: {str(e)}")
                    else:
                        st.warning("Please provide feedback on what to change")
            
            with col_b:
                if st.button("🖼️ Change Images", key=f"img_{draft_name}", use_container_width=True):
                    st.session_state[f'show_image_selector_{draft_name}'] = True
                    st.rerun()
            
            # Image selector modal
            if st.session_state.get(f'show_image_selector_{draft_name}'):
                st.divider()
                st.subheader("📁 Select New Images")
                
                from elbitat_agent.media_selector import list_media_files
                
                # Initialize selected images in session state
                if f'temp_selected_{draft_name}' not in st.session_state:
                    st.session_state[f'temp_selected_{draft_name}'] = []
                
                # Category selector
                category = st.selectbox(
                    "Category",
                    ["All", "Elbitat", "Sunset"],
                    key=f"cat_select_{draft_name}"
                )
                
                available_images = list_media_files(None if category == "All" else category)
                
                if available_images:
                    st.write(f"**Available: {len(available_images)} images**")
                    st.write(f"**Currently selected: {len(st.session_state[f'temp_selected_{draft_name}'])} images**")
                    
                    # Display images with click buttons in a grid
                    cols = st.columns(4)
                    
                    for idx, img_path in enumerate(available_images[:20]):  # Show first 20
                        img_str = str(img_path)
                        with cols[idx % 4]:
                            st.image(img_str, use_container_width=True)
                            # Check if this image is currently selected
                            is_selected = img_str in st.session_state[f'temp_selected_{draft_name}']
                            
                            # Toggle button
                            if is_selected:
                                if st.button("✅ Selected", key=f"sel_{draft_name}_{category}_{idx}", use_container_width=True):
                                    st.session_state[f'temp_selected_{draft_name}'].remove(img_str)
                                    st.rerun()
                            else:
                                if st.button("➕ Select", key=f"sel_{draft_name}_{category}_{idx}", use_container_width=True):
                                    st.session_state[f'temp_selected_{draft_name}'].append(img_str)
                                    st.rerun()
                    
                    st.divider()
                    col_apply, col_cancel = st.columns(2)
                    with col_apply:
                        if st.button("✅ Apply Selected Images", key=f"apply_img_{draft_name}", use_container_width=True):
                            selected_new_images = st.session_state[f'temp_selected_{draft_name}']
                            if selected_new_images:
                                draft_data['selected_images'] = selected_new_images
                                
                                # Save updated draft to database
                                save_draft_dict(draft_data, draft_file.name)
                                
                                st.success(f"✅ Updated with {len(selected_new_images)} images!")
                                st.session_state[f'show_image_selector_{draft_name}'] = False
                                st.session_state[f'temp_selected_{draft_name}'] = []  # Clear temp selection
                                st.rerun()
                            else:
                                st.warning("Please select at least one image")
                    
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_img_{draft_name}", use_container_width=True):
                            st.session_state[f'show_image_selector_{draft_name}'] = False
                            st.session_state[f'temp_selected_{draft_name}'] = []
                            st.rerun()
                else:
                    st.warning("No images available in this category")
        
        # Platform-specific content (always visible)
        st.divider()
        if 'instagram' in copy_by_platform:
            st.subheader("📷 Instagram")
            st.text_area(
                "Caption",
                copy_by_platform['instagram']['caption'],
                height=150,
                key="ig_caption",
                disabled=not edit_mode
            )
            st.text_input(
                "Hashtags",
                copy_by_platform['instagram']['hashtags'],
                key="ig_hashtags",
                disabled=not edit_mode
            )
        
        if 'facebook' in copy_by_platform:
            st.subheader("📘 Facebook")
            st.text_area(
                "Message",
                copy_by_platform['facebook']['message'],
                height=150,
                key="fb_message",
                disabled=not edit_mode
            )
        
        if 'tiktok' in copy_by_platform:
            st.subheader("🎵 TikTok")
            st.text_input(
                "Caption",
                copy_by_platform['tiktok']['caption'],
                key="tt_caption",
                disabled=not edit_mode
            )
            st.text_area(
                "Script",
                copy_by_platform['tiktok'].get('script', ''),
                height=100,
                key="tt_script",
                disabled=not edit_mode
            )
    
    # Action buttons
    st.divider()
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        if st.button("🗑️ Delete", use_container_width=True):
            draft_file.unlink()
            st.success("Draft deleted!")
            st.session_state['show_draft_detail'] = False
            st.rerun()
    
    with col2:
        if st.button("✅ Approve for Later", use_container_width=True):
            # Move to scheduled
            scheduled_dir = workspace / "scheduled"
            scheduled_dir.mkdir(parents=True, exist_ok=True)
            
            scheduled_file = scheduled_dir / f"{draft_name}.scheduled.json"
            with open(scheduled_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'draft': draft_data,
                    'approved_at': datetime.now().isoformat(),
                    'approved': True
                }, f, indent=2, ensure_ascii=False)
            
            st.success("Approved for later posting!")
            st.session_state['show_draft_detail'] = False
            st.rerun()
    
    with col3:
        if st.button("🚀 Post Now", use_container_width=True):
            # Convert to AdDraft and post
            draft = AdDraft(
                request=AdRequest.from_dict(request),
                copy_by_platform=copy_by_platform,
                selected_images=selected_images
            )
            
            with st.spinner("Posting to social media..."):
                results = auto_post_draft(draft)
            
            # Show results
            for platform, result in results.items():
                status = result.get('status', 'unknown')
                if status == 'success':
                    st.success(f"✓ {platform.upper()}: Posted successfully!")
                elif status == 'not_configured':
                    st.warning(f"⚠ {platform.upper()}: {result.get('reason', 'Not configured')}")
                elif status == 'error':
                    st.error(f"✗ {platform.upper()}: {result.get('error', 'Error')}")
            
            st.session_state['show_draft_detail'] = False


def show_schedule_page():
    """Display scheduled posts page."""
    st.markdown('<p class="main-header">📅 Scheduled Posts</p>', unsafe_allow_html=True)
    
    workspace = get_workspace_path()
    scheduled_dir = workspace / "scheduled"
    
    if not scheduled_dir.exists() or not list(scheduled_dir.glob("*.json")):
        st.info("No scheduled posts yet. Approve drafts to schedule them.")
        if st.button("📝 Review Drafts"):
            st.session_state['page'] = 'drafts'
            st.rerun()
        return
    
    scheduled_files = sorted(scheduled_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    st.write(f"**{len(scheduled_files)} post(s) scheduled for weekly publishing**")
    
    for sched_file in scheduled_files:
        with open(sched_file, 'r', encoding='utf-8') as f:
            sched_data = json.load(f)
        
        draft = sched_data.get('draft', {})
        request = draft.get('request', {})
        approved_at = sched_data.get('approved_at', '')
        
        with st.expander(f"📱 {request.get('title', 'Untitled')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Approved:** {approved_at[:10] if approved_at else 'N/A'}")
                st.write(f"**Platforms:** {', '.join(request.get('platforms', []))}")
                st.write(f"**Brief:** {request.get('brief', '')[:100]}...")
            
            with col2:
                if st.button("🚀 Post Now", key=f"post_{sched_file.stem}"):
                    # Post immediately
                    ad_draft = AdDraft(
                        request=AdRequest.from_dict(request),
                        copy_by_platform=draft.get('copy_by_platform', {}),
                        selected_images=draft.get('selected_images', [])
                    )
                    
                    with st.spinner("Posting..."):
                        results = auto_post_draft(ad_draft)
                    
                    st.success("Posted!")
                    sched_file.unlink()
                    st.rerun()


def show_settings_page():
    """Display settings and API configuration page."""
    st.markdown('<p class="main-header">⚙️ Settings & API Configuration</p>', unsafe_allow_html=True)
    
    # API Status
    st.subheader("🔌 API Configuration Status")
    
    api_status = check_api_configuration()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if api_status['meta_instagram_facebook']:
            st.success("✓ Meta (Instagram/Facebook)")
        else:
            st.error("✗ Meta Not Configured")
    
    with col2:
        if api_status['tiktok']:
            st.success("✓ TikTok")
        else:
            st.error("✗ TikTok Not Configured")
    
    with col3:
        if api_status['has_requests_library']:
            st.success("✓ Requests Library")
        else:
            st.error("✗ Requests Library")
    
    st.divider()
    
    # Image Library Management
    st.subheader("📸 Image Library Management")
    
    # Get media library path
    from elbitat_agent.media_selector import get_media_library_path, list_media_files
    media_library = get_media_library_path()
    
    # Display current library status
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Image Library Location:** `{media_library}`")
        
        # Count images by category
        if media_library.exists():
            elbitat_images = list_media_files("Elbitat")
            sunset_images = list_media_files("Sunset")
            total_images = len(elbitat_images) + len(sunset_images)
            
            st.metric("Total Images", total_images)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("🏨 Elbitat Hotel", len(elbitat_images))
            with col_b:
                st.metric("🌅 Sunset Views", len(sunset_images))
        else:
            st.warning("Image library not found. Please upload images below.")
    
    with col2:
        if st.button("🔄 Refresh Library", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Upload interface
    st.subheader("📤 Upload Images")
    
    # Select category
    category = st.selectbox(
        "Select Image Category",
        ["Elbitat", "Sunset", "Create New Category"],
        help="Choose where to save the uploaded images"
    )
    
    if category == "Create New Category":
        new_category = st.text_input("New Category Name", placeholder="e.g., Beach, Pool, Restaurant")
        if new_category:
            category = new_category
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Images",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        help="Select multiple images to upload"
    )
    
    if uploaded_files:
        st.write(f"**Selected {len(uploaded_files)} image(s) for upload**")
        
        # Preview first 3 images
        preview_cols = st.columns(min(3, len(uploaded_files)))
        for idx, uploaded_file in enumerate(uploaded_files[:3]):
            with preview_cols[idx]:
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
        
        if len(uploaded_files) > 3:
            st.info(f"+ {len(uploaded_files) - 3} more image(s)")
        
        # Upload button
        if st.button("✅ Upload Images", type="primary", use_container_width=True):
            # Create category folder
            category_path = media_library / category
            category_path.mkdir(parents=True, exist_ok=True)
            
            # Save uploaded files
            success_count = 0
            for uploaded_file in uploaded_files:
                try:
                    file_path = category_path / uploaded_file.name
                    with open(file_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    success_count += 1
                except Exception as e:
                    st.error(f"Error uploading {uploaded_file.name}: {str(e)}")
            
            if success_count > 0:
                st.success(f"✅ Successfully uploaded {success_count} image(s) to '{category}' category!")
                st.balloons()
                st.rerun()
    
    st.divider()
    
    # Bulk folder upload instructions
    with st.expander("📁 Bulk Upload via Folder (Advanced)"):
        st.markdown("""
        **To upload an entire folder structure:**
        
        1. Place your image folders in the project directory:
        ```
        elbitat-social-agent/
        └── Foto Elbitat/
            ├── Elbitat/
            │   ├── image1.jpg
            │   └── image2.jpg
            └── Sunset/
                ├── image1.jpg
                └── image2.jpg
        ```
        
        2. The agent will automatically detect and use images from these folders
        
        3. Alternatively, copy your folders directly to:
        ```
        """ + str(media_library) + """
        ```
        
        4. Click "Refresh Library" button above to update
        """)
    
    st.divider()
    
    # User Account Management
    st.subheader("👤 User Account Settings")
    
    # Get current user
    current_username = st.session_state.get('username')
    current_name = st.session_state.get('name')
    
    st.write(f"**Logged in as:** {current_name} (`{current_username}`)")
    
    # Change password section
    with st.expander("🔒 Change Password"):
        # Check if using cloud secrets
        using_cloud_secrets = hasattr(st, 'secrets') and 'credentials' in dir(st.secrets)
        
        if using_cloud_secrets:
            st.info("📌 **Password Management on Streamlit Cloud**")
            st.write("""
            To change your password when deployed on Streamlit Cloud:
            
            1. Generate a new password hash using bcrypt
            2. Go to your app's dashboard → **Manage app** → **Secrets**
            3. Update the password hash for your username
            4. Save changes - the app will restart automatically
            
            **Or** use the form below to generate a new hash:
            """)
            
            with st.form("generate_hash_form"):
                new_pwd_for_hash = st.text_input("New Password", type="password", key="pwd_for_hash")
                if st.form_submit_button("🔑 Generate Hash"):
                    if new_pwd_for_hash:
                        import bcrypt
                        new_hash = bcrypt.hashpw(new_pwd_for_hash.encode(), bcrypt.gensalt()).decode()
                        st.code(new_hash, language="text")
                        st.success("✅ Copy this hash and paste it into your Streamlit Cloud secrets!")
                    else:
                        st.error("Please enter a password")
            
            st.divider()
        
        with st.form("change_password_form"):
            if using_cloud_secrets:
                st.caption("⚠️ Note: Password changes below won't persist on Streamlit Cloud. Use hash generator above instead.")
            else:
                st.write("**Change Your Password**")
            
            current_password = st.text_input(
                "Current Password",
                type="password",
                key="current_pwd"
            )
            
            new_password = st.text_input(
                "New Password",
                type="password",
                help="Minimum 8 characters recommended",
                key="new_pwd"
            )
            
            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                key="confirm_pwd"
            )
            
            submit_pwd = st.form_submit_button("✅ Change Password", use_container_width=True)
            
            if submit_pwd:
                if not current_password or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                elif len(new_password) < 6:
                    st.error("New password must be at least 6 characters")
                else:
                    # Verify current password and update
                    import bcrypt
                    
                    # Load current credentials
                    config = load_auth_config()
                    user_data = config['credentials']['usernames'].get(current_username)
                    
                    if user_data:
                        # Verify current password
                        stored_hash = user_data['password']
                        if bcrypt.checkpw(current_password.encode(), stored_hash.encode()):
                            # Generate new password hash
                            new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                            
                            # Try to save to YAML file (works locally)
                            config_file = Path(__file__).parent / ".streamlit" / "credentials.yaml"
                            
                            try:
                                # Create a mutable copy if config is from st.secrets
                                if hasattr(config, '__class__') and 'Secrets' in config.__class__.__name__:
                                    # Config is from st.secrets - create mutable dict
                                    config_dict = {
                                        'credentials': {
                                            'usernames': {}
                                        },
                                        'cookie': dict(config['cookie'])
                                    }
                                    for username, udata in config['credentials']['usernames'].items():
                                        config_dict['credentials']['usernames'][str(username)] = dict(udata)
                                    config = config_dict
                                
                                # Update credentials
                                config['credentials']['usernames'][current_username]['password'] = new_hash
                                
                                # Attempt to save to file
                                config_file.parent.mkdir(parents=True, exist_ok=True)
                                with open(config_file, 'w') as f:
                                    yaml.dump(config, f, default_flow_style=False)
                                
                                st.success("✅ Password changed successfully! Please log in again with your new password.")
                                
                                # Clear session and force re-login
                                st.session_state['authentication_status'] = None
                                st.session_state['name'] = None
                                st.session_state['username'] = None
                                
                                st.info("Redirecting to login page...")
                                import time
                                time.sleep(2)
                                st.rerun()
                            except (PermissionError, OSError, TypeError) as e:
                                # Cloud environment - can't save to file
                                st.warning("⚠️ Cannot save password on cloud deployment")
                                st.info("📋 **Your new password hash:**")
                                st.code(new_hash, language="text")
                                st.write("""
                                To apply this password change:
                                1. Copy the hash above
                                2. Go to Streamlit Cloud dashboard → Manage app → Secrets
                                3. Update the password for `""" + current_username + """`:
                                ```toml
                                [credentials.usernames.""" + current_username + """]
                                password = \"""" + new_hash + """\"
                                ```
                                4. Save changes
                                """)
                        else:
                            st.error("❌ Current password is incorrect")
                    else:
                        st.error("❌ User not found")
    
    st.divider()
    
    # Configuration Instructions
    st.subheader("📝 API Setup Instructions")
    
    tab1, tab2, tab3 = st.tabs(["Meta (Instagram/Facebook)", "TikTok", "Workspace"])
    
    with tab1:
        st.markdown("""
        **Required Environment Variables:**
        ```
        META_ACCESS_TOKEN=your_token
        META_PAGE_ID=your_page_id
        META_INSTAGRAM_ACCOUNT_ID=your_ig_account_id
        ```
        
        **Setup Steps:**
        1. Create Facebook App at developers.facebook.com
        2. Add Instagram and Pages products
        3. Generate Page Access Token
        4. Get Page ID and Instagram Account ID
        5. Set environment variables
        
        See `API_SETUP.md` for detailed instructions.
        """)
    
    with tab2:
        st.markdown("""
        **Required Environment Variables:**
        ```
        TIKTOK_ACCESS_TOKEN=your_token
        TIKTOK_OPEN_ID=your_open_id
        ```
        
        **Setup Steps:**
        1. Apply for TikTok Developer Account
        2. Create app with video permissions
        3. Get Client Key and Secret
        4. Implement OAuth 2.0 flow
        5. Set environment variables
        
        See `API_SETUP.md` for detailed instructions.
        """)
    
    with tab3:
        workspace = get_workspace_path()
        st.write(f"**Workspace Location:** `{workspace}`")
        
        st.markdown("""
        **Directory Structure:**
        - `requests/` - Campaign request JSON files
        - `drafts/` - Generated draft content
        - `scheduled/` - Approved posts for publishing
        - `posted/` - Published post results
        """)


def show_email_campaigns_page():
    """Display email marketing campaigns page with contact discovery and bulk sending."""
    st.markdown('<p class="main-header">✉️ Email Campaigns</p>', unsafe_allow_html=True)
    
    st.markdown("""
    Discover business contacts from the web and send personalized email campaigns.
    """)
    
    # Create tabs for different email campaign functions
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Find Contacts", "📋 Contact List", "✉️ Create Campaign", "🚀 Send Campaign"])
    
    with tab1:
        st.subheader("Discover Business Contacts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            search_query = st.text_input(
                "Search Query",
                placeholder="e.g., wellness agencies, marketing firms, restaurants",
                help="Describe the type of businesses you want to find"
            )
        
        with col2:
            country = st.text_input(
                "Country",
                value="Denmark",
                help="Country to focus the search on"
            )
        
        max_companies = st.slider("Maximum Companies to Find", 5, 50, 10)
        
        if st.button("🔍 Start Discovery", type="primary", use_container_width=True):
            if not search_query:
                st.error("Please enter a search query")
            else:
                with st.spinner(f"Searching for {search_query} in {country}..."):
                    try:
                        # Discover contacts
                        contacts = discover_contacts(search_query, country, max_companies)
                        
                        if contacts:
                            st.success(f"✅ Found {len(contacts)} contacts!")
                            
                            # Display results in a table
                            st.subheader("Discovered Contacts")
                            
                            for i, contact in enumerate(contacts, 1):
                                with st.expander(f"{i}. {contact.get('company_name', 'Unknown')} - {contact.get('email', 'No email')}"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write(f"**Email:** {contact.get('email', 'N/A')}")
                                        st.write(f"**Company:** {contact.get('company_name', 'N/A')}")
                                        st.write(f"**Website:** {contact.get('website', 'N/A')}")
                                    
                                    with col2:
                                        st.write(f"**Country:** {contact.get('country', 'N/A')}")
                                        st.write(f"**Industry:** {contact.get('industry', 'N/A')}")
                                        st.write(f"**Source:** {contact.get('source', 'N/A')}")
                            
                            # Save to database
                            if st.button("💾 Save All Contacts to Database", use_container_width=True):
                                with st.spinner("Saving contacts..."):
                                    # Ensure database is initialized
                                    from elbitat_agent.database import init_database
                                    init_database()
                                    
                                    stats = bulk_save_contacts(contacts)
                                    st.success(f"Saved {stats['saved']} contacts! (Skipped {stats['skipped']} duplicates)")
                                    st.rerun()
                        else:
                            st.warning("No contacts found. Try a different search query.")
                    
                    except Exception as e:
                        st.error(f"Error during discovery: {str(e)}")
                        st.info("Try a different search query or check your API configuration.")
    
    with tab2:
        st.subheader("Manage Contacts")
        
        # Filter options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "new", "active", "contacted", "bounced", "unsubscribed"],
                index=0
            )
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Get contacts from database
        try:
            # Ensure database is initialized
            from elbitat_agent.database import init_database
            init_database()
            
            filter_val = None if status_filter == "All" else status_filter
            contacts = get_all_email_contacts(status=filter_val)
            
            if contacts:
                st.info(f"📊 Total contacts: {len(contacts)}")
                
                # Display contacts in a table
                for contact in contacts:
                    with st.expander(f"{contact['company_name']} - {contact['email']}"):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.write(f"**Email:** {contact['email']}")
                            st.write(f"**Company:** {contact['company_name']}")
                            st.write(f"**Website:** {contact.get('website', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Country:** {contact.get('country', 'N/A')}")
                            st.write(f"**Status:** {contact['status']}")
                            st.write(f"**Source:** {contact.get('source', 'N/A')}")
                        
                        with col3:
                            # Update status
                            status_options = ["new", "active", "contacted", "bounced", "unsubscribed"]
                            current_status = contact.get('status', 'new')
                            try:
                                status_index = status_options.index(current_status)
                            except ValueError:
                                status_index = 0
                            
                            new_status = st.selectbox(
                                "Status",
                                status_options,
                                index=status_index,
                                key=f"status_{contact['id']}"
                            )
                            
                            if st.button("Update", key=f"update_{contact['id']}"):
                                if update_email_contact_status(contact['id'], new_status):
                                    st.success("Status updated!")
                                    st.rerun()
                            
                            if st.button("🗑️ Delete", key=f"delete_{contact['id']}"):
                                if delete_email_contact(contact['id']):
                                    st.success("Contact deleted!")
                                    st.rerun()
                
                # Export to CSV
                if st.button("📥 Export to CSV", use_container_width=True):
                    import io
                    output = io.StringIO()
                    output.write("Email,Company,Website,Country,Industry,Status,Source\n")
                    for contact in contacts:
                        output.write(f"{contact['email']},{contact['company_name']},{contact.get('website', '')},{contact.get('country', '')},{contact.get('industry', '')},{contact['status']},{contact.get('source', '')}\n")
                    
                    st.download_button(
                        label="Download CSV",
                        data=output.getvalue(),
                        file_name=f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning(f"No contacts found with status filter: '{status_filter}'")
                st.info("""
                **Troubleshooting:**
                - Try selecting "All" status filter to see all contacts
                - Newly saved contacts have 'new' or 'active' status by default
                - Use the 'Find Contacts' tab to discover new leads
                - Check if contacts were successfully saved (you should see a success message)
                """)
        
        except Exception as e:
            st.error(f"Error loading contacts: {str(e)}")
    
    with tab3:
        st.subheader("Create Email Campaign")
        
        # Campaign name
        campaign_name = st.text_input(
            "Campaign Name",
            placeholder="e.g., Q1 Partnership Outreach",
            help="Give your campaign a memorable name"
        )
        
        # Subject line
        subject = st.text_input(
            "Email Subject",
            placeholder="e.g., Partnership Opportunity with Your Company",
            help="The subject line for your email"
        )
        
        # Template selection
        st.markdown("**Email Template**")
        
        templates = get_default_templates()
        template_names = list(templates.keys())
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            selected_template = st.selectbox(
                "Choose Template",
                ["Custom"] + template_names,
                help="Select a pre-built template or create your own"
            )
        
        with col2:
            if selected_template != "Custom":
                template_content = templates[selected_template]
                st.info(f"Using {selected_template} template")
            else:
                template_content = ""
        
        # Email content editor
        email_content = st.text_area(
            "Email Content",
            value=template_content,
            height=300,
            help="Use {{company_name}}, {{first_name}}, {{email}}, {{website}}, {{country}} for personalization"
        )
        
        # Preview
        if email_content:
            st.markdown("**Preview (with sample data)**")
            sample_contact = {
                'company_name': 'Acme Corp',
                'first_name': 'John',
                'email': 'john@acme.com',
                'website': 'https://acme.com',
                'country': 'Denmark'
            }
            preview = personalize_email(email_content, sample_contact)
            st.markdown(f"```\n{preview}\n```")
        
        # Save campaign
        if st.button("💾 Save Campaign", type="primary", use_container_width=True):
            if not campaign_name:
                st.error("Please enter a campaign name")
            elif not subject:
                st.error("Please enter an email subject")
            elif not email_content:
                st.error("Please enter email content")
            else:
                try:
                    campaign_id = save_email_campaign(campaign_name, subject, email_content)
                    if campaign_id:
                        st.success(f"✅ Campaign '{campaign_name}' saved! Go to 'Send Campaign' tab to send it.")
                    else:
                        st.error("Failed to save campaign")
                except Exception as e:
                    st.error(f"Error saving campaign: {str(e)}")
    
    with tab4:
        st.subheader("Send Email Campaign")
        
        # Get saved campaigns
        try:
            campaigns = get_all_email_campaigns()
            
            if campaigns:
                # Campaign selection
                campaign_names = [f"{c['name']} (ID: {c['id']})" for c in campaigns]
                selected_campaign_str = st.selectbox(
                    "Select Campaign",
                    campaign_names,
                    help="Choose a saved campaign to send"
                )
                
                # Extract campaign ID
                campaign_id = int(selected_campaign_str.split("ID: ")[1].rstrip(")"))
                campaign = next(c for c in campaigns if c['id'] == campaign_id)
                
                # Display campaign details
                st.markdown(f"**Campaign:** {campaign['name']}")
                st.markdown(f"**Subject:** {campaign['subject']}")
                
                with st.expander("View Email Template"):
                    st.text(campaign['template'])
                
                # Get active contacts
                contacts = get_all_email_contacts(status='active')
                
                if contacts:
                    st.info(f"Found {len(contacts)} active contacts")
                    
                    # Contact selection
                    all_contacts = st.checkbox("Send to all active contacts", value=True)
                    
                    if not all_contacts:
                        selected_emails = st.multiselect(
                            "Select Recipients",
                            [f"{c['company_name']} ({c['email']})" for c in contacts]
                        )
                        contact_ids = [
                            contacts[i]['id'] 
                            for i, c in enumerate(contacts) 
                            if f"{c['company_name']} ({c['email']})" in selected_emails
                        ]
                    else:
                        contact_ids = [c['id'] for c in contacts]
                    
                    st.markdown(f"**Recipients:** {len(contact_ids)} contacts")
                    
                    # Email sending disabled
                    st.markdown("---")
                    st.info("📧 **Email Sending Feature**")
                    st.warning("""
                    Email sending is currently disabled. The system can discover and save contacts, 
                    but sending functionality requires email service configuration (SendGrid, Gmail SMTP, etc.).
                    
                    **What you can do now:**
                    - ✅ Search and discover business contacts
                    - ✅ Save contacts to database
                    - ✅ Create and save email campaigns
                    - ✅ Export contact lists to CSV
                    
                    **To enable email sending:**
                    Configure an email service provider in the Settings or contact support.
                    """)
                else:
                    st.warning("No active contacts found. Add contacts in the 'Find Contacts' or 'Contact List' tabs.")
            else:
                st.info("No campaigns found. Create a campaign in the 'Create Campaign' tab first.")
        
        except Exception as e:
            st.error(f"Error loading campaigns: {str(e)}")


def main():
    """Main application entry point."""
    
    # Check authentication
    if st.session_state.get('authentication_status') != True:
        show_login_page()
        return
    
    # Authenticated - show main app
    authenticator = initialize_auth()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### 👤 Welcome, {st.session_state['name']}!")
        
        # Updated for streamlit-authenticator 0.4.x
        authenticator.logout(location='sidebar')
        
        st.divider()
        
        st.subheader("Navigation")
        
        # Initialize page in session state if not present
        if 'page' not in st.session_state:
            st.session_state.page = 'dashboard'
        
        # Get current page and convert to title case for radio button
        current_page = st.session_state.page
        page_options = ["Dashboard", "Marketing Strategy", "Chat", "Drafts", "Schedule", "Email Campaigns", "Settings"]
        
        # Find the index of the current page
        try:
            default_index = page_options.index(current_page.title())
        except (ValueError, AttributeError):
            default_index = 0
        
        # Remove key to allow session state to control the selection
        page = st.radio(
            "Go to:",
            page_options,
            index=default_index
        )
        
        # Update session state page using dot notation
        if page:
            st.session_state.page = page.lower()
        
        st.divider()
        
        st.caption("Elbitat Social Media Agent v2.0")
        st.caption("Powered by Streamlit")
    
    # Main content area
    current_page = st.session_state.page if 'page' in st.session_state else 'dashboard'
    
    if current_page == 'dashboard':
        show_dashboard()
    elif current_page == 'marketing strategy':
        show_marketing_strategy_page()
    elif current_page == 'chat':
        show_chat_page()
    elif current_page == 'drafts':
        show_drafts_page()
    elif current_page == 'schedule':
        show_schedule_page()
    elif current_page == 'email campaigns':
        show_email_campaigns_page()
    elif current_page == 'settings':
        show_settings_page()


if __name__ == "__main__":
    main()
