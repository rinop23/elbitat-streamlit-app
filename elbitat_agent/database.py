"""Database module for persistent storage of drafts, requests, and scheduled posts."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st

# Try to import Supabase functions
try:
    from .supabase_db import (
        get_supabase_client,
        save_draft_to_supabase, get_all_drafts_from_supabase, delete_draft_from_supabase,
        save_request_to_supabase, get_all_requests_from_supabase, delete_request_from_supabase,
        save_scheduled_post_to_supabase, get_all_scheduled_posts_from_supabase, delete_scheduled_post_from_supabase
    )
    USE_SUPABASE = True
except ImportError:
    USE_SUPABASE = False
    print("ℹ️ Supabase not available, using SQLite")


def get_db_path() -> Path:
    """Get the database file path.
    
    On Streamlit Cloud, the database should be in the app root directory
    which persists across app restarts (but not across redeployments without mounted volumes).
    """
    # Try to use a persistent location
    if hasattr(st, 'secrets') and 'db_path' in st.secrets:
        db_path = Path(st.secrets['db_path'])
    else:
        # Use app root directory for better persistence on Streamlit Cloud
        # This will be at the same level as streamlit_app.py
        db_path = Path(__file__).parent.parent
    
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path / 'elbitat_ads.db'


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
    
    # Email contacts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            company_name TEXT,
            website TEXT,
            country TEXT,
            industry TEXT,
            status TEXT DEFAULT 'active',
            source TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Email campaigns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            template TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            sent_count INTEGER DEFAULT 0,
            opened_count INTEGER DEFAULT 0,
            clicked_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Email sends table (tracking individual sends)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            contact_id INTEGER,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP,
            opened_at TIMESTAMP,
            clicked_at TIMESTAMP,
            error_message TEXT,
            FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
            FOREIGN KEY (contact_id) REFERENCES email_contacts(id)
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
    """Save a draft to the database (Supabase or SQLite)."""
    # Try Supabase first if available and configured
    if USE_SUPABASE:
        client = get_supabase_client()
        if client:
            return save_draft_to_supabase(filename, data)
    
    # Fallback to SQLite
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
    """Get all drafts from the database (Supabase or SQLite)."""
    # Try Supabase first if available and configured
    if USE_SUPABASE:
        client = get_supabase_client()
        if client:
            return get_all_drafts_from_supabase()
    
    # Fallback to SQLite
    try:
        db_path = get_db_path()
        print(f"🗄️ Database path: {db_path}")
        print(f"🗄️ Database exists: {db_path.exists()}")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT filename, content FROM drafts ORDER BY created_at DESC')
        rows = cursor.fetchall()
        print(f"🗄️ Found {len(rows)} drafts in database")
        conn.close()
        
        drafts = []
        for filename, content_json in rows:
            data = json.loads(content_json)
            data['_filename'] = filename
            drafts.append(data)
        
        return drafts
    except Exception as e:
        print(f"❌ Error loading drafts from DB: {e}")
        import traceback
        traceback.print_exc()
        return []


def delete_draft_from_db(filename: str) -> bool:
    """Delete a draft from the database (Supabase or SQLite)."""
    # Try Supabase first if available and configured
    if USE_SUPABASE:
        client = get_supabase_client()
        if client:
            return delete_draft_from_supabase(filename)
    
    # Fallback to SQLite
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
    # Safeguard: Only allow overwrite if explicitly requested (e.g., via an 'overwrite' flag in data)
    overwrite = data.get('overwrite', False)
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # Check if post already exists
        cursor.execute('SELECT COUNT(*) FROM scheduled_posts WHERE filename = ?', (filename,))
        exists = cursor.fetchone()[0] > 0
        if exists and not overwrite:
            print(f"⛔ Scheduled post '{filename}' already exists. Not overwriting without explicit request.")
            conn.close()
            return False
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
    # Safeguard: Only allow deletion if explicitly requested (e.g., via a 'confirm_delete' flag in st.session_state)
    import streamlit as st
    confirm_delete = st.session_state.get('confirm_delete', False)
    if not confirm_delete:
        print(f"⛔ Attempted to delete scheduled post '{filename}' without explicit confirmation.")
        return False
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
    from elbitat_agent.config import get_workspace_path
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


# ===== EMAIL CONTACT OPERATIONS =====

def save_email_contact(email: str, company_name: str = None, website: str = None, 
                       country: str = None, industry: str = None, source: str = None) -> bool:
    """Save an email contact to the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO email_contacts 
            (email, company_name, website, country, industry, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email, company_name, website, country, industry, source, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving email contact: {e}")
        return False


def get_all_email_contacts(status: str = None) -> List[Dict]:
    """Get all email contacts from the database, optionally filtered by status."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT id, email, company_name, website, country, industry, status, source, notes, created_at
                FROM email_contacts 
                WHERE status = ?
                ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT id, email, company_name, website, country, industry, status, source, notes, created_at
                FROM email_contacts 
                ORDER BY created_at DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        contacts = []
        for row in rows:
            contacts.append({
                'id': row[0],
                'email': row[1],
                'company_name': row[2],
                'website': row[3],
                'country': row[4],
                'industry': row[5],
                'status': row[6],
                'source': row[7],
                'notes': row[8],
                'created_at': row[9]
            })
        
        return contacts
    except Exception as e:
        print(f"Error loading email contacts: {e}")
        return []


def update_email_contact_status(contact_id: int, status: str) -> bool:
    """Update the status of an email contact."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE email_contacts 
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (status, datetime.now(), contact_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating contact status: {e}")
        return False


def delete_email_contact(contact_id: int) -> bool:
    """Delete an email contact from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM email_contacts WHERE id = ?', (contact_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting contact: {e}")
        return False


# ===== EMAIL CAMPAIGN OPERATIONS =====

def save_email_campaign(name: str, subject: str, template: str) -> Optional[int]:
    """Save an email campaign and return its ID."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO email_campaigns (name, subject, template, created_at)
            VALUES (?, ?, ?, ?)
        ''', (name, subject, template, datetime.now()))
        
        campaign_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return campaign_id
    except Exception as e:
        print(f"Error saving campaign: {e}")
        return None


def get_all_email_campaigns() -> List[Dict]:
    """Get all email campaigns from the database."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, subject, template, status, sent_count, opened_count, clicked_count, created_at
            FROM email_campaigns 
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        campaigns = []
        for row in rows:
            campaigns.append({
                'id': row[0],
                'name': row[1],
                'subject': row[2],
                'template': row[3],
                'status': row[4],
                'sent_count': row[5],
                'opened_count': row[6],
                'clicked_count': row[7],
                'created_at': row[8]
            })
        
        return campaigns
    except Exception as e:
        print(f"Error loading campaigns: {e}")
        return []


def record_email_send(campaign_id: int, contact_id: int, status: str = 'sent') -> bool:
    """Record that an email was sent to a contact."""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO email_sends (campaign_id, contact_id, status, sent_at)
            VALUES (?, ?, ?, ?)
        ''', (campaign_id, contact_id, status, datetime.now()))
        
        # Update campaign sent count
        cursor.execute('''
            UPDATE email_campaigns 
            SET sent_count = sent_count + 1, updated_at = ?
            WHERE id = ?
        ''', (datetime.now(), campaign_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error recording email send: {e}")
        return False
