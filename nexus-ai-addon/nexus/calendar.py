import os
import logging
import json
import datetime
import asyncio
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nexus.calendar")

class GoogleCalendar:
    """Interface for Google Calendar API."""
    
    def __init__(self):
        """Initialize the Google Calendar client."""
        # Check if Google Calendar is enabled
        self.enabled = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
        if not self.enabled:
            logger.info("Google Calendar integration is disabled")
            return
        
        # Get credentials from environment
        self.credentials_json = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "")
        if not self.credentials_json:
            logger.warning("Google Calendar credentials not provided")
            self.enabled = False
            return
        
        # Setup Google Calendar API
        self.credentials = None
        self.calendar_service = None
        self.token_path = "/data/nexus/google_token.json"
        
        # Try to load saved token
        self._load_credentials()
    
    def _load_credentials(self):
        """Load or refresh Google API credentials."""
        # Define the scopes for calendar access
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        
        # Check if we have a saved token
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'r') as token_file:
                    token_data = json.load(token_file)
                    self.credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception as e:
                logger.error(f"Failed to load saved token: {e}")
                self.credentials = None
        
        # If no valid credentials, try to initialize from provided credentials
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self._save_token()
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    self.credentials = None
            else:
                try:
                    # Parse the credentials JSON
                    creds_data = json.loads(self.credentials_json)
                    
                    # Create a flow for user authorization
                    flow = InstalledAppFlow.from_client_config(
                        creds_data, 
                        SCOPES,
                        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
                    )
                    
                    # This will require user interaction - we can't fully automate this
                    # For Home Assistant add-on, this would need to be handled via ingress UI
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    logger.info(f"Please visit this URL to authorize: {auth_url}")
                    logger.info("After authorization, paste the code in the add-on UI")
                    
                    # For now, we'll log that this needs to be done
                    logger.warning("Google Calendar authorization required - use the add-on UI")
                    self.credentials = None
                except Exception as e:
                    logger.error(f"Failed to initialize OAuth flow: {e}")
                    self.credentials = None
        
        # Initialize the calendar service if we have valid credentials
        if self.credentials and self.credentials.valid:
            try:
                self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
                logger.info("Google Calendar API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to build calendar service: {e}")
                self.calendar_service = None
        else:
            logger.warning("No valid Google Calendar credentials available")
    
    def _save_token(self):
        """Save the current token for future use."""
        if not self.credentials:
            return
        
        try:
            token_data = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
            
            with open(self.token_path, 'w') as token_file:
                json.dump(token_data, token_file)
            
            logger.info("Google Calendar token saved successfully")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    async def authorize_with_code(self, auth_code: str) -> bool:
        """Authorize with Google using the provided code."""
        if not self.enabled:
            return False
        
        try:
            # Parse the credentials JSON
            creds_data = json.loads(self.credentials_json)
            
            # Create a flow for user authorization
            flow = InstalledAppFlow.from_client_config(
                creds_data, 
                ['https://www.googleapis.com/auth/calendar.readonly'],
                redirect_uri="urn:ietf:wg:oauth:2.0:oob"
            )
            
            # Exchange the auth code for credentials
            self.credentials = flow.fetch_token(code=auth_code)
            
            # Save the token
            self._save_token()
            
            # Initialize the calendar service
            self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
            
            logger.info("Google Calendar successfully authorized")
            return True
        except Exception as e:
            logger.error(f"Failed to authorize with code: {e}")
            return False
    
    async def get_today_events(self) -> List[Dict[str, str]]:
        """Get events for today from Google Calendar."""
        if not self.enabled or not self.calendar_service:
            logger.warning("Google Calendar not enabled or initialized")
            return []
        
        try:
            # Get the current date in the right format
            now = datetime.datetime.utcnow()
            today_start = datetime.datetime.combine(now.date(), datetime.time.min).isoformat() + 'Z'
            today_end = datetime.datetime.combine(now.date(), datetime.time.max).isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = await asyncio.to_thread(
                self.calendar_service.events().list,
                calendarId='primary',
                timeMin=today_start,
                timeMax=today_end,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events
            formatted_events = []
            for event in events:
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                
                if not start:
                    continue
                
                # Convert to a readable format
                if 'T' in start:  # DateTime format
                    event_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                    time_str = event_time.strftime("%H:%M")
                else:  # Date format (all-day event)
                    time_str = "All day"
                
                formatted_events.append({
                    "time": time_str,
                    "event": event.get('summary', 'Unnamed event')
                })
            
            return formatted_events
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []

    async def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next X days."""
        if not self.enabled or not self.calendar_service:
            logger.warning("Google Calendar not enabled or initialized")
            return []
        
        try:
            # Get the current date and calculate end date
            now = datetime.datetime.utcnow()
            end_date = now + datetime.timedelta(days=days)
            
            now_iso = now.isoformat() + 'Z'
            end_iso = end_date.isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = await asyncio.to_thread(
                self.calendar_service.events().list,
                calendarId='primary',
                timeMin=now_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events
            formatted_events = []
            for event in events:
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                
                if not start:
                    continue
                
                # Convert to a readable format
                if 'T' in start:  # DateTime format
                    event_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                    date_str = event_time.strftime("%Y-%m-%d")
                    time_str = event_time.strftime("%H:%M")
                else:  # Date format (all-day event)
                    date_str = start
                    time_str = "All day"
                
                formatted_events.append({
                    "date": date_str,
                    "time": time_str,
                    "event": event.get('summary', 'Unnamed event'),
                    "description": event.get('description', ''),
                    "location": event.get('location', '')
                })
            
            return formatted_events
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return []
