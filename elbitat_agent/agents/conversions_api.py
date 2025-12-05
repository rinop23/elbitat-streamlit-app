"""Meta Conversions API integration for lead tracking and event reporting.

This module allows you to send lead events and conversions to Meta (Facebook/Instagram)
for better campaign tracking and optimization.

Use cases:
- Track bookings from social media campaigns
- Report conversion events (purchases, sign-ups)
- Send CRM data to Meta for optimization
- Measure campaign ROI
"""

from __future__ import annotations

import time
import hashlib
from typing import Dict, List, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

from ..config import SocialMediaConfig


class MetaConversionsAPI:
    """Send conversion events to Meta Conversions API.
    
    This is used for tracking leads, purchases, and other conversion events
    that result from your social media campaigns.
    """
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, config: SocialMediaConfig):
        if not requests:
            raise ImportError("requests library required. Run: pip install requests")
        
        if not config.meta_access_token:
            raise ValueError("Meta Access Token not configured")
        
        self.access_token = config.meta_access_token
        self.pixel_id = config.meta_pixel_id  # Will need to add this to config
    
    @staticmethod
    def hash_user_data(value: str) -> str:
        """Hash user data (email, phone) for privacy.
        
        Meta requires hashed PII data for GDPR/CCPA compliance.
        """
        return hashlib.sha256(value.lower().strip().encode()).hexdigest()
    
    def send_lead_event(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        lead_id: Optional[str] = None,
        lead_source: str = "social_media_campaign",
        custom_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Send a lead event to Meta Conversions API.
        
        Args:
            email: Customer email (will be hashed automatically)
            phone: Customer phone (will be hashed automatically)
            lead_id: Your internal lead ID
            lead_source: Where the lead came from
            custom_data: Additional custom data to send
            
        Returns:
            Response from Meta API
        """
        # Build user data
        user_data = {}
        
        if email:
            user_data['em'] = [self.hash_user_data(email)]
        
        if phone:
            # Remove all non-numeric characters
            phone_clean = ''.join(filter(str.isdigit, phone))
            user_data['ph'] = [self.hash_user_data(phone_clean)]
        
        if lead_id:
            user_data['lead_id'] = lead_id
        
        # Build event data
        event_data = {
            "action_source": "website",  # or "system_generated" for CRM
            "event_name": "Lead",
            "event_time": int(time.time()),
            "user_data": user_data
        }
        
        # Add custom data if provided
        if custom_data:
            event_data["custom_data"] = {
                "event_source": lead_source,
                **custom_data
            }
        
        # Send to Meta
        return self._send_event(event_data)
    
    def send_booking_event(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        booking_value: float = 0.0,
        currency: str = "EUR",
        booking_id: Optional[str] = None,
        check_in_date: Optional[str] = None,
        check_out_date: Optional[str] = None
    ) -> Dict[str, str]:
        """Send a booking/purchase event to Meta.
        
        Args:
            email: Customer email
            phone: Customer phone
            booking_value: Total booking value
            currency: Currency code (EUR, USD, etc.)
            booking_id: Your internal booking ID
            check_in_date: Check-in date (YYYY-MM-DD)
            check_out_date: Check-out date (YYYY-MM-DD)
            
        Returns:
            Response from Meta API
        """
        # Build user data
        user_data = {}
        
        if email:
            user_data['em'] = [self.hash_user_data(email)]
        
        if phone:
            phone_clean = ''.join(filter(str.isdigit, phone))
            user_data['ph'] = [self.hash_user_data(phone_clean)]
        
        # Build event data
        event_data = {
            "action_source": "website",
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "user_data": user_data,
            "custom_data": {
                "value": booking_value,
                "currency": currency,
                "content_type": "hotel_booking"
            }
        }
        
        # Add booking details
        if booking_id:
            event_data["custom_data"]["booking_id"] = booking_id
        
        if check_in_date:
            event_data["custom_data"]["checkin_date"] = check_in_date
        
        if check_out_date:
            event_data["custom_data"]["checkout_date"] = check_out_date
        
        return self._send_event(event_data)
    
    def send_custom_event(
        self,
        event_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        custom_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Send a custom event to Meta.
        
        Args:
            event_name: Name of the event (e.g., "ViewContent", "AddToCart")
            email: Customer email
            phone: Customer phone
            custom_data: Any custom data to send
            
        Returns:
            Response from Meta API
        """
        # Build user data
        user_data = {}
        
        if email:
            user_data['em'] = [self.hash_user_data(email)]
        
        if phone:
            phone_clean = ''.join(filter(str.isdigit, phone))
            user_data['ph'] = [self.hash_user_data(phone_clean)]
        
        # Build event data
        event_data = {
            "action_source": "website",
            "event_name": event_name,
            "event_time": int(time.time()),
            "user_data": user_data
        }
        
        if custom_data:
            event_data["custom_data"] = custom_data
        
        return self._send_event(event_data)
    
    def _send_event(self, event_data: Dict) -> Dict[str, str]:
        """Internal method to send event to Meta Conversions API.
        
        Args:
            event_data: Complete event data payload
            
        Returns:
            Response from Meta API
        """
        if not self.pixel_id:
            return {
                "status": "error",
                "error": "Meta Pixel ID not configured"
            }
        
        url = f"{self.BASE_URL}/{self.pixel_id}/events"
        
        payload = {
            "data": [event_data],
            "access_token": self.access_token
        }
        
        try:
            if requests:
                response = requests.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                return {
                    "status": "success",
                    "events_received": result.get("events_received", 0),
                    "messages": result.get("messages", [])
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
        
        return {"status": "error", "error": "requests library not available"}


def track_campaign_lead(
    email: str,
    phone: Optional[str] = None,
    campaign_name: Optional[str] = None,
    source_platform: Optional[str] = None
) -> Dict[str, str]:
    """Helper function to track leads from social media campaigns.
    
    Use this when someone books or inquires via your social media posts.
    
    Args:
        email: Customer email
        phone: Customer phone (optional)
        campaign_name: Which campaign generated this lead
        source_platform: instagram, facebook, or tiktok
        
    Returns:
        Tracking result
        
    Example:
        >>> track_campaign_lead(
        ...     email="customer@example.com",
        ...     phone="+1234567890",
        ...     campaign_name="first_june_weekend_getaway",
        ...     source_platform="instagram"
        ... )
    """
    config = SocialMediaConfig.from_env()
    
    if not config.meta_access_token:
        return {
            "status": "not_configured",
            "message": "Meta API not configured"
        }
    
    try:
        api = MetaConversionsAPI(config)
        
        custom_data = {}
        if campaign_name:
            custom_data["campaign_name"] = campaign_name
        if source_platform:
            custom_data["source_platform"] = source_platform
        
        custom_data["event_source"] = "elbitat_social_agent"
        
        result = api.send_lead_event(
            email=email,
            phone=phone,
            lead_source="social_media_campaign",
            custom_data=custom_data
        )
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
