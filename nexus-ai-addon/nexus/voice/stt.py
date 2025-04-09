"""
Speech-to-text functionality for Nexus AI using OpenAI Whisper API
"""
import os
import tempfile
import logging
from typing import Optional
import openai

logger = logging.getLogger(__name__)

class SpeechToText:
    """Speech-to-text conversion using OpenAI Whisper"""
    
    def __init__(self):
        """Initialize the STT service"""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Set OpenAI API key if available
        if self.api_key:
            openai.api_key = self.api_key
    
    async def transcribe(self, audio_data: bytes, language: Optional[str] = None) -> dict:
        """
        Transcribe audio data to text using OpenAI Whisper API
        
        Args:
            audio_data: Raw audio data (WAV format)
            language: Optional language code (e.g., 'en', 'fr')
            
        Returns:
            Dictionary with transcription result
        """
        if not self.api_key:
            return {"success": False, "error": "OpenAI API key not configured"}
        
        try:
            # Save audio data to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # Transcribe using OpenAI Whisper API
            with open(temp_path, "rb") as audio_file:
                transcription = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return {
                "success": True,
                "text": transcription.text
            }
        
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            
            # Clean up temporary file in case of error
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return {
                "success": False,
                "error": str(e)
            }
