"""Email discovery agent for finding business contact emails from the web."""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin, quote, unquote
import streamlit as st


# Email regex pattern
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


def search_companies(query: str, country: str = None, limit: int = 10) -> List[Dict]:
    """Search for companies using Serper.dev API.
    
    Args:
        query: Search query (e.g., "wellness agencies")
        country: Country code (e.g., "dk" for Denmark)
        limit: Maximum number of results
    
    Returns:
        List of company results with name and website
    """
    try:
        # Get API key from secrets
        if not hasattr(st, 'secrets') or 'SERPER_API_KEY' not in st.secrets:
            print("Serper API key not configured. Using fallback search.")
            return _fallback_search(query, country, limit)
        
        api_key = st.secrets['SERPER_API_KEY']
        url = "https://google.serper.dev/search"
        
        # Build search query
        search_query = query
        if country:
            search_query += f" {country}"
        
        payload = {
            "q": search_query,
            "num": limit
        }
        
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        # Parse organic results
        for result in data.get('organic', [])[:limit]:
            results.append({
                'company_name': result.get('title', ''),
                'website': result.get('link', ''),
                'description': result.get('snippet', '')
            })
        
        return results
        
    except Exception as e:
        print(f"Error searching with Serper: {e}")
        return _fallback_search(query, country, limit)


def _fallback_search(query: str, country: str = None, limit: int = 10) -> List[Dict]:
    """Fallback search using multiple methods (no API needed)."""
    try:
        # Build search query
        search_query = query
        if country:
            # Add country name and common TLD
            country_map = {
                'denmark': 'Denmark .dk',
                'sweden': 'Sweden .se',
                'norway': 'Norway .no',
                'germany': 'Germany .de',
                'uk': 'United Kingdom .uk',
                'usa': 'USA .com',
            }
            country_lower = country.lower()
            search_query += f" {country_map.get(country_lower, country)}"
        
        # Try DuckDuckGo Lite (more reliable)
        url = f"https://lite.duckduckgo.com/lite/?q={quote(search_query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        
        # Parse DDG Lite results (different structure)
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Skip internal DDG links
            if 'duckduckgo.com' in href or not href.startswith('http'):
                continue
            
            # Get the actual URL (DDG redirects)
            if '/l/?uddg=' in href or '/l/?kh=-1' in href:
                # Extract actual URL from DDG redirect
                try:
                    actual_url = href.split('uddg=')[1].split('&')[0] if 'uddg=' in href else href
                    # URL decode
                    actual_url = unquote(actual_url)
                    
                    if actual_url.startswith('http') and len(text) > 5:
                        results.append({
                            'company_name': text[:100],  # Limit length
                            'website': actual_url,
                            'description': ''
                        })
                        
                        if len(results) >= limit:
                            break
                except:
                    continue
        
        # If we didn't get enough results, add some common business directories
        if len(results) < 3 and country:
            country_lower = country.lower()
            directory_sites = []
            
            if 'denmark' in country_lower or 'dk' in country_lower:
                directory_sites = [
                    f"https://www.proff.dk/bransjes%C3%B8k/{query.replace(' ', '-')}",
                    f"https://www.krak.dk/",
                ]
            
            for site in directory_sites[:limit - len(results)]:
                results.append({
                    'company_name': f"{query.title()} Directory",
                    'website': site,
                    'description': 'Business directory'
                })
        
        return results
        
    except Exception as e:
        print(f"Error in fallback search: {e}")
        # Return at least something to work with
        return [{
            'company_name': f"{query.title()} (Manual Entry)",
            'website': f"https://www.google.com/search?q={quote(query + ' ' + (country or ''))}",
            'description': 'Could not auto-discover. Click to search manually.'
        }]


def extract_emails_from_website(website_url: str, max_pages: int = 3) -> List[str]:
    """Extract email addresses from a website.
    
    Args:
        website_url: The website URL to scrape
        max_pages: Maximum number of pages to check (contact, about, team)
    
    Returns:
        List of unique email addresses found
    """
    emails = set()
    
    try:
        # Normalize URL
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        
        parsed = urlparse(website_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Common pages that might have contact info
        pages_to_check = [
            website_url,
            urljoin(base_url, '/contact'),
            urljoin(base_url, '/about'),
            urljoin(base_url, '/team'),
            urljoin(base_url, '/kontakt'),  # Danish
            urljoin(base_url, '/om-os'),    # Danish
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        checked = 0
        for page_url in pages_to_check:
            if checked >= max_pages:
                break
            
            try:
                response = requests.get(page_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    checked += 1
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract from text content
                    text_content = soup.get_text()
                    found_emails = re.findall(EMAIL_PATTERN, text_content)
                    emails.update(found_emails)
                    
                    # Extract from mailto: links
                    mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
                    for link in mailto_links:
                        email = link['href'].replace('mailto:', '').split('?')[0]
                        if re.match(EMAIL_PATTERN, email):
                            emails.add(email)
                    
            except Exception as e:
                print(f"Error checking {page_url}: {e}")
                continue
        
        # Filter out common false positives
        filtered_emails = []
        ignore_patterns = ['example.com', 'test.com', 'domain.com', 'email.com', 
                          'yoursite.com', 'website.com', 'placeholder.com']
        
        for email in emails:
            email_lower = email.lower()
            if not any(pattern in email_lower for pattern in ignore_patterns):
                filtered_emails.append(email)
        
        return list(set(filtered_emails))
        
    except Exception as e:
        print(f"Error extracting emails from {website_url}: {e}")
        return []


def validate_email(email: str) -> bool:
    """Basic email validation using regex.
    
    For production, consider using email-validator library with DNS checks.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def discover_contacts(search_query: str, country: str = None, 
                     max_companies: int = 10) -> List[Dict]:
    """Discover email contacts for companies matching the search query.
    
    Args:
        search_query: What to search for (e.g., "wellness agencies")
        country: Country to search in (e.g., "Denmark")
        max_companies: Maximum number of companies to process
    
    Returns:
        List of discovered contacts with email, company, website
    """
    discovered_contacts = []
    
    # Step 1: Search for companies
    print(f"Searching for: {search_query} in {country or 'all countries'}...")
    companies = search_companies(search_query, country, max_companies)
    
    print(f"Found {len(companies)} companies to check")
    
    # Step 2: Extract emails from each company website
    for i, company in enumerate(companies, 1):
        website = company.get('website', '')
        company_name = company.get('company_name', '')
        
        if not website:
            continue
        
        print(f"[{i}/{len(companies)}] Checking {company_name}...")
        
        emails = extract_emails_from_website(website, max_pages=3)
        
        for email in emails:
            if validate_email(email):
                discovered_contacts.append({
                    'email': email,
                    'company_name': company_name,
                    'website': website,
                    'country': country,
                    'source': f'web_search: {search_query}'
                })
                print(f"  ✓ Found: {email}")
    
    print(f"\nDiscovery complete! Found {len(discovered_contacts)} email contacts.")
    return discovered_contacts


def bulk_save_contacts(contacts: List[Dict]) -> Dict[str, int]:
    """Save multiple discovered contacts to the database.
    
    Returns:
        Dictionary with 'saved', 'skipped', and 'errors' counts
    """
    from .database import save_email_contact
    
    stats = {'saved': 0, 'skipped': 0, 'errors': 0}
    
    for contact in contacts:
        try:
            email = contact.get('email')
            
            # Skip if no email
            if not email:
                print(f"Skipping contact with no email: {contact.get('company_name')}")
                stats['skipped'] += 1
                continue
            
            print(f"Attempting to save: {email} - {contact.get('company_name')}")
            
            success = save_email_contact(
                email=email,
                company_name=contact.get('company_name'),
                website=contact.get('website'),
                country=contact.get('country'),
                industry=contact.get('industry'),
                source=contact.get('source')
            )
            
            if success:
                stats['saved'] += 1
                print(f"  ✓ Saved successfully")
            else:
                stats['skipped'] += 1
                print(f"  ⊘ Skipped (duplicate or failed)")
                
        except Exception as e:
            print(f"Error saving {contact.get('email')}: {e}")
            import traceback
            traceback.print_exc()
            stats['errors'] += 1
    
    print(f"\nBulk save complete: {stats}")
    return stats
