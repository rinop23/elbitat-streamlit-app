"""Streamlit Web Application for Elbitat Social Media Agent.

Streamlit-based interface with authentication for:
- User login with credentials
- Chat with agent to create campaigns
- Review and approve generated drafts
- View scheduled posts
- Configure API settings
"""

from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth
from pathlib import Path
from datetime import datetime
import json
import yaml
from yaml.loader import SafeLoader

from elbitat_agent.paths import get_workspace_path
from elbitat_agent.file_storage import load_all_requests, list_request_files
from elbitat_agent.agents.orchestrator import generate_drafts_for_all_requests
from elbitat_agent.agents.auto_poster import auto_post_draft, check_api_configuration
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
    """Load authentication configuration from YAML file."""
    config_file = Path(__file__).parent / ".streamlit" / "credentials.yaml"
    
    if config_file.exists():
        with open(config_file) as file:
            return yaml.load(file, Loader=SafeLoader)
    
    # Default configuration if file doesn't exist
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
    
    # Updated for streamlit-authenticator 0.4.x - removed preauthorized parameter
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
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
        st.info("**Demo Credentials:**\n\n**Username:** admin  \n**Password:** admin123\n\n**OR**\n\n**Username:** elbitat  \n**Password:** elbitat2025")
        
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
        if st.button("💬 Create Campaign", use_container_width=True):
            st.session_state['page'] = 'chat'
            st.rerun()
    
    with col2:
        if st.button("✨ Generate Drafts", use_container_width=True):
            with st.spinner("Generating drafts..."):
                drafts = generate_drafts_for_all_requests()
                st.success(f"Generated {len(drafts)} draft(s)!")
                st.session_state['page'] = 'drafts'
                st.rerun()
    
    with col3:
        if st.button("📝 Review Drafts", use_container_width=True):
            st.session_state['page'] = 'drafts'
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


def show_chat_page():
    """Display chat interface for campaign creation."""
    st.markdown('<p class="main-header">💬 Create Campaign</p>', unsafe_allow_html=True)
    
    # Campaign form
    with st.form("campaign_form"):
        st.subheader("Campaign Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Campaign Title*", placeholder="e.g., Summer Weekend Special")
            month = st.date_input("Target Month")
            goal = st.selectbox("Campaign Goal", ["awareness", "bookings", "engagement", "leads"])
        
        with col2:
            platforms = st.multiselect(
                "Platforms*",
                ["instagram", "facebook", "tiktok"],
                default=["instagram", "facebook"]
            )
            audience = st.text_input("Target Audience", placeholder="e.g., Young couples and families")
            language = st.selectbox("Language", ["en", "fr", "de", "it"], index=0)
        
        brief = st.text_area(
            "Campaign Brief*",
            placeholder="Describe what you want this campaign to showcase...",
            height=150
        )
        
        submitted = st.form_submit_button("✨ Generate Campaign", use_container_width=True)
        
        if submitted:
            if not title or not brief or not platforms:
                st.error("Please fill in all required fields (marked with *)")
            else:
                # Create request
                workspace = get_workspace_path()
                requests_dir = workspace / "requests"
                requests_dir.mkdir(parents=True, exist_ok=True)
                
                safe_title = title.replace(" ", "_").lower()
                request_file = requests_dir / f"{safe_title}.json"
                
                request_data = {
                    "title": title,
                    "month": month.strftime("%Y-%m"),
                    "goal": goal,
                    "platforms": platforms,
                    "audience": audience,
                    "language": language,
                    "brief": brief
                }
                
                with open(request_file, 'w', encoding='utf-8') as f:
                    json.dump(request_data, f, indent=2, ensure_ascii=False)
                
                # Generate drafts
                with st.spinner("🎨 Generating campaign with AI..."):
                    try:
                        drafts = generate_drafts_for_all_requests()
                        
                        if len(drafts) == 0:
                            st.warning("⚠️ Campaign request saved, but no drafts were generated. Check that the request was saved correctly.")
                            st.write("**Saved request location:**", str(request_file))
                        else:
                            st.success(f"✅ Campaign created! Generated {len(drafts)} draft(s).")
                            st.info("Go to 'Drafts' page to review and approve your content.")
                            
                            # Automatically navigate to drafts page only if drafts were created
                            st.session_state['page'] = 'drafts'
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error generating drafts: {str(e)}")
                        st.write("**Request was saved to:**", str(request_file))
                        st.write("**Error details:**")
                        st.code(str(e))
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
                                
                                # Save updated draft
                                with open(draft_file, 'w', encoding='utf-8') as f:
                                    json.dump(draft_data, f, indent=2, ensure_ascii=False)
                                
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
                    st.write(f"**Selected: {len(st.session_state[f'temp_selected_{draft_name}'])} images**")
                    
                    # Display images with checkboxes
                    cols = st.columns(4)
                    
                    for idx, img_path in enumerate(available_images[:20]):  # Show first 20
                        img_str = str(img_path)
                        with cols[idx % 4]:
                            st.image(img_str, use_container_width=True)
                            is_selected = img_str in st.session_state[f'temp_selected_{draft_name}']
                            if st.checkbox(f"Select", key=f"sel_{draft_name}_{idx}", value=is_selected):
                                if img_str not in st.session_state[f'temp_selected_{draft_name}']:
                                    st.session_state[f'temp_selected_{draft_name}'].append(img_str)
                            else:
                                if img_str in st.session_state[f'temp_selected_{draft_name}']:
                                    st.session_state[f'temp_selected_{draft_name}'].remove(img_str)
                    
                    col_apply, col_cancel = st.columns(2)
                    with col_apply:
                        if st.button("✅ Apply Selected Images", key=f"apply_img_{draft_name}", use_container_width=True):
                            selected_new_images = st.session_state[f'temp_selected_{draft_name}']
                            if selected_new_images:
                            draft_data['selected_images'] = selected_new_images
                            
                                # Save updated draft
                                with open(draft_file, 'w', encoding='utf-8') as f:
                                    json.dump(draft_data, f, indent=2, ensure_ascii=False)
                                
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
        with st.form("change_password_form"):
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
                            
                            # Update credentials file
                            config['credentials']['usernames'][current_username]['password'] = new_hash
                            
                            # Save to file
                            config_file = Path(__file__).parent / ".streamlit" / "credentials.yaml"
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
        - `media/` - Selected images for campaigns
        - `logs/` - System logs
        """)


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
        
        # Get current page and convert to title case for radio button
        current_page = st.session_state.get('page', 'dashboard')
        page_options = ["Dashboard", "Chat", "Drafts", "Schedule", "Settings"]
        
        # Find the index of the current page
        try:
            default_index = page_options.index(current_page.title())
        except ValueError:
            default_index = 0
        
        page = st.radio(
            "Go to:",
            page_options,
            index=default_index,
            key="page_selector"
        )
        
        # Update session state page
        if page:
            st.session_state['page'] = page.lower()
        
        st.divider()
        
        st.caption("Elbitat Social Media Agent v2.0")
        st.caption("Powered by Streamlit")
    
    # Main content area
    current_page = st.session_state.get('page', 'dashboard')
    
    if current_page == 'dashboard':
        show_dashboard()
    elif current_page == 'chat':
        show_chat_page()
    elif current_page == 'drafts':
        show_drafts_page()
    elif current_page == 'schedule':
        show_schedule_page()
    elif current_page == 'settings':
        show_settings_page()


if __name__ == "__main__":
    main()
