"""
Google Calendar integration for Nexus AI
"""
import os
import logging
import json
import pickle
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from pathlib import Path

import google.oauth2.credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar API configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class GoogleCalendar:
    """Interface for Google Calendar API."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the Google Calendar client."""
        self.data_dir = data_dir or os.environ.get("DATA_DIR", "/data/nexus")
        self.token_path = Path(self.data_dir) / "google_token.pickle"
        self.credentials_path = Path(self.data_dir) / "google_credentials.json"
        self.credentials = None
        self.service = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load or refresh Google API credentials."""
        # Check if token file exists
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token:
                    self.credentials = pickle.load(token)
            except Exception as e:
                logger.error(f"Error loading token file: {str(e)}")
                self.credentials = None
        
        # Check if credentials are valid
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                self.credentials.refresh(Request())
                self._save_token(self.credentials)
                logger.info("Refreshed Google Calendar credentials")
            except Exception as e:
                logger.error(f"Error refreshing credentials: {str(e)}")
                self.credentials = None
        
        # Initialize service if credentials are valid
        if self.credentials and not self.credentials.expired:
            try:
                self.service = build('calendar', 'v3', credentials=self.credentials)
                logger.info("Google Calendar service initialized")
            except Exception as e:
                logger.error(f"Error building calendar service: {str(e)}")
                self.service = None
        else:
            logger.warning("Google Calendar credentials not available or expired")
    
    def _save_token(self, creds):
        """Save the current token for future use."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            
            # Save credentials
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
                
            logger.info(f"Token saved to {self.token_path}")
        except Exception as e:
            logger.error(f"Error saving token: {str(e)}")
    
    async def authorize_with_code(self, auth_code: str) -> bool:
        """Authorize with Google using the provided code."""
        try:
            # Check if credentials file exists
            if not self.credentials_path.exists():
                logger.error("Google credentials file not found")
                return False
            
            # Run the authorization flow in a separate thread
            def auth_flow():
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                flow.fetch_token(code=auth_code)
                return flow.credentials
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            self.credentials = await loop.run_in_executor(None, auth_flow)
            
            # Save the credentials for future use
            self._save_token(self.credentials)
            
            # Initialize service
            self.service = build('calendar', 'v3', credentials=self.credentials)
            
            return True
        except Exception as e:
            logger.error(f"Error authorizing with code: {str(e)}")
            return False
    
    async def get_today_events(self) -> List[Dict[str, str]]:
        """Get events for today from Google Calendar."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_today_events_sync)
    
    def _get_today_events_sync(self) -> List[Dict[str, str]]:
        """Synchronous version of get_today_events."""
        if not self.service:
            logger.warning("Calendar service not initialized")
            return []
        
        try:
            # Get today's date
            now = datetime.utcnow()
            start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + 'Z'
            end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                logger.info('No events found for today.')
                return []
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_events.append(self._format_event(event))
            
            return formatted_events
        
        except Exception as e:
            logger.error(f"Error getting today's events: {str(e)}")
            return []
    
    async def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next X days."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._get_upcoming_events_sync(days))
    
    def _get_upcoming_events_sync(self, days: int) -> List[Dict[str, Any]]:
        """Synchronous version of get_upcoming_events."""
        if not self.service:
            logger.warning("Calendar service not initialized")
            return []
        
        try:
            # Get time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days)).isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                logger.info(f'No upcoming events found for next {days} days.')
                return []
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_events.append(self._format_event(event))
            
            return formatted_events
        
        except Exception as e:
            logger.error(f"Error getting upcoming events: {str(e)}")
            return []
    
    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Google Calendar event into a simplified structure."""
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Extract start time
        start_time = None
        all_day = False
        
        if 'dateTime' in start:
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            start_time = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        elif 'date' in start:
            start_time = start['date']
            all_day = True
        
        # Extract end time
        end_time = None
        if 'dateTime' in end:
            end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            end_time = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        elif 'date' in end:
            end_time = end['date']
        
        return {
            'id': event.get('id', ''),
            'summary': event.get('summary', 'No title'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start_time': start_time,
            'end_time': end_time,
            'all_day': all_day,
            'attendees': [
                attendee.get('email', '')
                for attendee in event.get('attendees', [])
                if attendee.get('email')
            ],
            'link': event.get('htmlLink', ''),
            'organizer': event.get('organizer', {}).get('email', '') if event.get('organizer') else '',
            'status': event.get('status', 'pending')
        }