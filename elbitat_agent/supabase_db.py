"""Supabase cloud database adapter for persistent storage."""

import json
from typing import Dict, List, Optional
from datetime import datetime
import streamlit as st


def get_supabase_client():
    """Initialize and return Supabase client."""
    try:
        from supabase import create_client, Client
        
        # Get credentials from Streamlit secrets
        url = st.secrets.get("supabase_url")
        key = st.secrets.get("supabase_key")
        
        if not url or not key:
            print("⚠️ Supabase credentials not found in secrets")
            return None
        
        client: Client = create_client(url, key)
        print("✅ Connected to Supabase")
        return client
    except ImportError:
        print("⚠️ Supabase package not installed")
        return None
    except Exception as e:
        print(f"⚠️ Error connecting to Supabase: {e}")
        return None


def init_supabase_tables():
    """
    Initialize Supabase tables if they don't exist.
    
    Note: Tables should be created via Supabase dashboard or SQL editor:
    
    -- Drafts table
    CREATE TABLE IF NOT EXISTS drafts (
        id BIGSERIAL PRIMARY KEY,
        filename TEXT UNIQUE NOT NULL,
        content JSONB NOT NULL,
        service TEXT,
        image_path TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- Requests table
    CREATE TABLE IF NOT EXISTS requests (
        id BIGSERIAL PRIMARY KEY,
        filename TEXT UNIQUE NOT NULL,
        content JSONB NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- Scheduled posts table
    CREATE TABLE IF NOT EXISTS scheduled_posts (
        id BIGSERIAL PRIMARY KEY,
        filename TEXT UNIQUE NOT NULL,
        content JSONB NOT NULL,
        scheduled_time TIMESTAMPTZ,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    print("ℹ️ Please create tables via Supabase SQL editor (see docstring)")


# ===== DRAFT OPERATIONS =====

def save_draft_to_supabase(filename: str, data: Dict) -> bool:
    """Save a draft to Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        service = data.get('service', '')
        image_path = data.get('image_path', '')
        
        # Upsert (insert or update if exists)
        result = client.table('drafts').upsert({
            'filename': filename,
            'content': data,
            'service': service,
            'image_path': image_path,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='filename').execute()
        
        print(f"✅ Saved draft to Supabase: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving draft to Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_all_drafts_from_supabase() -> List[Dict]:
    """Get all drafts from Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return []
        
        result = client.table('drafts').select('filename, content').order('created_at', desc=True).execute()
        
        drafts = []
        for row in result.data:
            data = row['content']
            data['_filename'] = row['filename']
            drafts.append(data)
        
        print(f"✅ Loaded {len(drafts)} drafts from Supabase")
        return drafts
    except Exception as e:
        print(f"❌ Error loading drafts from Supabase: {e}")
        import traceback
        traceback.print_exc()
        return []


def delete_draft_from_supabase(filename: str) -> bool:
    """Delete a draft from Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        client.table('drafts').delete().eq('filename', filename).execute()
        print(f"✅ Deleted draft from Supabase: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error deleting draft from Supabase: {e}")
        return False


# ===== REQUEST OPERATIONS =====

def save_request_to_supabase(filename: str, data: Dict) -> bool:
    """Save a request to Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        result = client.table('requests').upsert({
            'filename': filename,
            'content': data,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='filename').execute()
        
        print(f"✅ Saved request to Supabase: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving request to Supabase: {e}")
        return False


def get_all_requests_from_supabase() -> List[Dict]:
    """Get all requests from Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return []
        
        result = client.table('requests').select('filename, content').order('created_at', desc=True).execute()
        
        requests = []
        for row in result.data:
            data = row['content']
            data['_filename'] = row['filename']
            requests.append(data)
        
        print(f"✅ Loaded {len(requests)} requests from Supabase")
        return requests
    except Exception as e:
        print(f"❌ Error loading requests from Supabase: {e}")
        return []


def delete_request_from_supabase(filename: str) -> bool:
    """Delete a request from Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        client.table('requests').delete().eq('filename', filename).execute()
        print(f"✅ Deleted request from Supabase: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error deleting request from Supabase: {e}")
        return False


# ===== SCHEDULED POST OPERATIONS =====

def save_scheduled_post_to_supabase(filename: str, data: Dict) -> bool:
    """Save a scheduled post to Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        scheduled_time = data.get('scheduled_time')
        status = data.get('status', 'pending')
        
        result = client.table('scheduled_posts').upsert({
            'filename': filename,
            'content': data,
            'scheduled_time': scheduled_time,
            'status': status,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='filename').execute()
        
        print(f"✅ Saved scheduled post to Supabase: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving scheduled post to Supabase: {e}")
        return False


def get_all_scheduled_posts_from_supabase() -> List[Dict]:
    """Get all scheduled posts from Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return []
        
        result = client.table('scheduled_posts').select('filename, content').order('scheduled_time', desc=False).execute()
        
        posts = []
        for row in result.data:
            data = row['content']
            data['_filename'] = row['filename']
            posts.append(data)
        
        print(f"✅ Loaded {len(posts)} scheduled posts from Supabase")
        return posts
    except Exception as e:
        print(f"❌ Error loading scheduled posts from Supabase: {e}")
        return []


def delete_scheduled_post_from_supabase(filename: str) -> bool:
    """Delete a scheduled post from Supabase."""
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        client.table('scheduled_posts').delete().eq('filename', filename).execute()
        print(f"✅ Deleted scheduled post from Supabase: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error deleting scheduled post from Supabase: {e}")
        return False
