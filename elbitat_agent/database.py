"""Database module for persistent storage of drafts, requests, and scheduled posts."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st


def get_db_path() -> Path:
    """Get the database file path.
    
    On Streamlit Cloud, uses a persistent volume if available,
    otherwise falls back to app directory (which persists across sessions but not redeployments).
    For true persistence across redeployments, mount a volume or use external DB.
    """
    # Try to use a persistent location
    if hasattr(st, 'secrets') and 'db_path' in st.secrets:
        db_path = Path(st.secrets['db_path'])
    else:
        # Use app directory - will persist during session
        db_path = Path(__file__).parent.parent / 'data'
    
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path / 'elbitat.db'


def init_database():
    """Initialize the database with required tables."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Drafts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            service TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Scheduled posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            service TEXT,
            scheduled_time TIMESTAMP,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


# ===== REQUEST OPERATIONS =====

def save_request_to_db(filename: str, data: Dict) -> bool:
    """Save a request to the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        content_json = json.dumps(data, ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO requests (filename, content, updated_at)
            VALUES (?, ?, ?)
        ''', (filename, content_json, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving request to DB: {e}")
        return False


def get_all_requests() -> List[Dict]:
    """Get all requests from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT filename, content FROM requests ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        requests = []
        for filename, content_json in rows:
            data = json.loads(content_json)
            data['_filename'] = filename
            requests.append(data)
        
        return requests
    except Exception as e:
        print(f"Error loading requests from DB: {e}")
        return []


def delete_request_from_db(filename: str) -> bool:
    """Delete a request from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM requests WHERE filename = ?', (filename,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting request from DB: {e}")
        return False


# ===== DRAFT OPERATIONS =====

def save_draft_to_db(filename: str, data: Dict) -> bool:
    """Save a draft to the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        content_json = json.dumps(data, ensure_ascii=False)
        service = data.get('service', '')
        image_path = data.get('image_path', '')
        
        cursor.execute('''
            INSERT OR REPLACE INTO drafts (filename, content, service, image_path, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, content_json, service, image_path, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving draft to DB: {e}")
        return False


def get_all_drafts() -> List[Dict]:
    """Get all drafts from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT filename, content FROM drafts ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        drafts = []
        for filename, content_json in rows:
            data = json.loads(content_json)
            data['_filename'] = filename
            drafts.append(data)
        
        return drafts
    except Exception as e:
        print(f"Error loading drafts from DB: {e}")
        return []


def delete_draft_from_db(filename: str) -> bool:
    """Delete a draft from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM drafts WHERE filename = ?', (filename,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting draft from DB: {e}")
        return False


# ===== SCHEDULED POST OPERATIONS =====

def save_scheduled_post_to_db(filename: str, data: Dict) -> bool:
    """Save a scheduled post to the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        content_json = json.dumps(data, ensure_ascii=False)
        service = data.get('service', '')
        scheduled_time = data.get('scheduled_time', '')
        status = data.get('status', 'pending')
        
        cursor.execute('''
            INSERT OR REPLACE INTO scheduled_posts 
            (filename, content, service, scheduled_time, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (filename, content_json, service, scheduled_time, status, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving scheduled post to DB: {e}")
        return False


def get_all_scheduled_posts() -> List[Dict]:
    """Get all scheduled posts from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT filename, content FROM scheduled_posts ORDER BY scheduled_time ASC')
        rows = cursor.fetchall()
        conn.close()
        
        posts = []
        for filename, content_json in rows:
            data = json.loads(content_json)
            data['_filename'] = filename
            posts.append(data)
        
        return posts
    except Exception as e:
        print(f"Error loading scheduled posts from DB: {e}")
        return []


def delete_scheduled_post_from_db(filename: str) -> bool:
    """Delete a scheduled post from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM scheduled_posts WHERE filename = ?', (filename,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting scheduled post from DB: {e}")
        return False


def update_scheduled_post_status(filename: str, status: str) -> bool:
    """Update the status of a scheduled post."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE scheduled_posts 
            SET status = ?, updated_at = ?
            WHERE filename = ?
        ''', (status, datetime.now(), filename))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating scheduled post status: {e}")
        return False


# ===== MIGRATION UTILITIES =====

def migrate_files_to_db():
    """Migrate existing files from file system to database (one-time operation)."""
    from elbitat_agent.paths import get_workspace_path
    from elbitat_agent.file_storage import load_all_requests, load_all_drafts, load_all_scheduled_posts
    
    workspace = get_workspace_path()
    migrated_count = {'requests': 0, 'drafts': 0, 'scheduled': 0}
    
    # Migrate requests
    try:
        requests = load_all_requests()
        for req in requests:
            filename = req.get('_filename', f"request_{datetime.now().timestamp()}.json")
            if save_request_to_db(filename, req):
                migrated_count['requests'] += 1
    except Exception as e:
        print(f"Error migrating requests: {e}")
    
    # Migrate drafts
    try:
        drafts = load_all_drafts()
        for draft in drafts:
            filename = draft.get('_filename', f"draft_{datetime.now().timestamp()}.json")
            if save_draft_to_db(filename, draft):
                migrated_count['drafts'] += 1
    except Exception as e:
        print(f"Error migrating drafts: {e}")
    
    # Migrate scheduled posts
    try:
        posts = load_all_scheduled_posts()
        for post in posts:
            filename = post.get('_filename', f"scheduled_{datetime.now().timestamp()}.json")
            if save_scheduled_post_to_db(filename, post):
                migrated_count['scheduled'] += 1
    except Exception as e:
        print(f"Error migrating scheduled posts: {e}")
    
    return migrated_count
