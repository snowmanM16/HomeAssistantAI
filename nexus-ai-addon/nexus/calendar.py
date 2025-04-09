"""
Google Calendar integration for Nexus AI
"""
import os
import logging
import pickle
import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nexus.calendar")

class GoogleCalendar:
    """Interface for Google Calendar API."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the Google Calendar client."""
        # Set data directory for credentials and token
        if not data_dir:
            data_dir = os.environ.get('DATA_DIR', '/data/nexus')
        
        self.data_dir = data_dir
        self.credentials_path = os.path.join(data_dir, 'gcalendar_credentials.json')
        self.token_path = os.path.join(data_dir, 'gcalendar_token.pickle')
        
        # Create directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize client
        self.service = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load or refresh Google API credentials."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            # Define scopes
            SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
            
            creds = None
            
            # Load saved token if it exists
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh token if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_token(creds)
            
            # If we have valid credentials, build the service
            if creds and creds.valid:
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Google Calendar service initialized")
            else:
                logger.warning("No valid Google Calendar credentials found")
        except ImportError:
            logger.warning("Google API packages not installed")
        except Exception as e:
            logger.error(f"Error loading Google Calendar credentials: {e}")
    
    def _save_token(self, creds):
        """Save the current token for future use."""
        with open(self.token_path, 'wb') as token:
            pickle.dump(creds, token)
        logger.debug("Google Calendar token saved")
    
    async def authorize_with_code(self, auth_code: str) -> bool:
        """Authorize with Google using the provided code."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            # Check if credentials file exists
            if not os.path.exists(self.credentials_path):
                logger.error("Credentials file not found")
                return False
            
            # Set up the flow with the credentials file
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar.readonly'],
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            # Exchange auth code for credentials
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # Save the credentials for future use
            self._save_token(creds)
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            
            return True
        except Exception as e:
            logger.error(f"Error authorizing with Google: {e}")
            return False
    
    async def get_today_events(self) -> List[Dict[str, str]]:
        """Get events for today from Google Calendar."""
        if not self.service:
            logger.warning("Google Calendar service not initialized")
            return []
        
        try:
            # Get today's date boundaries
            now = datetime.datetime.utcnow()
            today_start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + 'Z'
            today_end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = self.service.events().list(
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
                formatted_events.append(self._format_event(event))
            
            return formatted_events
        except Exception as e:
            logger.error(f"Error getting today's events: {e}")
            return []
    
    async def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next X days."""
        if not self.service:
            logger.warning("Google Calendar service not initialized")
            return []
        
        try:
            # Calculate time boundaries
            now = datetime.datetime.utcnow()
            future = now + datetime.timedelta(days=days)
            now_str = now.isoformat() + 'Z'
            future_str = future.isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now_str,
                timeMax=future_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_events.append(self._format_event(event))
            
            return formatted_events
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []
    
    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Google Calendar event into a simplified structure."""
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Format start time
        start_time = None
        if 'dateTime' in start:
            start_dt = datetime.datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            start_time = start_dt.strftime('%H:%M')
        elif 'date' in start:
            # All-day event
            start_time = "All day"
        
        # Format end time
        end_time = None
        if 'dateTime' in end:
            end_dt = datetime.datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            end_time = end_dt.strftime('%H:%M')
        
        # Format date
        date = None
        if 'dateTime' in start:
            date_dt = datetime.datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            date = date_dt.strftime('%Y-%m-%d')
        elif 'date' in start:
            date = start['date']
        
        return {
            'id': event.get('id'),
            'summary': event.get('summary', 'Unnamed event'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start_time': start_time,
            'end_time': end_time,
            'date': date,
            'all_day': 'dateTime' not in start,
            'organizer': event.get('organizer', {}).get('email', ''),
            'attendees': [a.get('email') for a in event.get('attendees', [])],
            'status': event.get('status', '')
        }
