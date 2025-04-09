"""
Google Calendar integration for Nexus AI
"""
import os
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import pytz
from pathlib import Path

import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleCalendar:
    """Interface for Google Calendar API."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the Google Calendar client."""
        self.data_dir = data_dir or os.environ.get("DATA_DIR", ".")
        self.credentials_path = Path(self.data_dir) / "google_credentials.json"
        self.token_path = Path(self.data_dir) / "google_token.json"
        self.service = None
        self.credentials = None
        self.scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
    
    def _load_credentials(self):
        """Load or refresh Google API credentials."""
        # Check if token exists
        if self.token_path.exists():
            with open(self.token_path, "r") as token_file:
                token_data = json.load(token_file)
                self.credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(
                    token_data, self.scopes
                )
        
        # If credentials don't exist or are invalid, return False
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self._save_token()
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    return False
            else:
                return False
        
        # Build the service
        try:
            self.service = build("calendar", "v3", credentials=self.credentials)
            return True
        except Exception as e:
            logger.error(f"Error building calendar service: {e}")
            return False
    
    def _save_token(self):
        """Save the current token for future use."""
        if not self.credentials:
            return
        
        token_data = {
            "token": self.credentials.token,
            "refresh_token": self.credentials.refresh_token,
            "token_uri": self.credentials.token_uri,
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "scopes": self.credentials.scopes
        }
        
        with open(self.token_path, "w") as token_file:
            json.dump(token_data, token_file)
    
    async def authorize_with_code(self, auth_code: str) -> bool:
        """Authorize with Google using the provided code."""
        try:
            if not self.credentials_path.exists():
                logger.error("Google client configuration file not found")
                return False
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path,
                scopes=self.scopes
            )
            
            flow.fetch_token(code=auth_code)
            self.credentials = flow.credentials
            self._save_token()
            
            return self._load_credentials()
        except Exception as e:
            logger.error(f"Error authorizing with code: {e}")
            return False
    
    async def get_today_events(self) -> List[Dict[str, str]]:
        """Get events for today from Google Calendar."""
        if not self._load_credentials():
            return []
        
        try:
            # Get timezone from system
            local_tz = datetime.now().astimezone().tzinfo
            
            # Calculate today's timeframe
            now = datetime.now(local_tz)
            start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=local_tz)
            end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=local_tz)
            
            # Convert to ISO format
            start_time_iso = start_of_day.isoformat()
            end_time_iso = end_of_day.isoformat()
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=start_time_iso,
                timeMax=end_time_iso,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            # Process events
            events = events_result.get("items", [])
            
            return [self._format_event(event) for event in events]
        
        except Exception as e:
            logger.error(f"Error getting today's events: {e}")
            return []
    
    async def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next X days."""
        if not self._load_credentials():
            return []
        
        try:
            # Get timezone from system
            local_tz = datetime.now().astimezone().tzinfo
            
            # Calculate timeframe
            now = datetime.now(local_tz)
            end_date = now + timedelta(days=days)
            
            # Convert to ISO format
            start_time_iso = now.isoformat()
            end_time_iso = end_date.isoformat()
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=start_time_iso,
                timeMax=end_time_iso,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            # Process events
            events = events_result.get("items", [])
            
            return [self._format_event(event) for event in events]
        
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []
    
    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Google Calendar event into a simplified structure."""
        # Get start and end times (handling all-day events)
        start = event.get("start", {})
        end = event.get("end", {})
        
        # Format the event
        formatted_event = {
            "id": event.get("id", ""),
            "summary": event.get("summary", "Untitled Event"),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "all_day": "date" in start and "dateTime" not in start
        }
        
        # Handle datetime format based on all-day or timed event
        if formatted_event["all_day"]:
            formatted_event["start_date"] = start.get("date", "")
            formatted_event["end_date"] = end.get("date", "")
        else:
            start_dt = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
            
            formatted_event["start_datetime"] = start_dt.isoformat()
            formatted_event["end_datetime"] = end_dt.isoformat()
            formatted_event["start_time"] = start_dt.strftime("%H:%M")
            formatted_event["end_time"] = end_dt.strftime("%H:%M")
        
        return formatted_event
