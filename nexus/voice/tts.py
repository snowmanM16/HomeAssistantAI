"""
Text-to-speech functionality for Nexus AI using OpenAI TTS API
"""
import os
import tempfile
import logging
from typing import Optional
import openai

logger = logging.getLogger(__name__)

class TextToSpeech:
    """Text-to-speech conversion using OpenAI TTS"""
    
    def __init__(self):
        """Initialize the TTS service"""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.voice = "alloy"  # Default voice
        
        # Set OpenAI API key if available
        if self.api_key:
            openai.api_key = self.api_key
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> dict:
        """
        Synthesize text to speech using OpenAI TTS API
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Dictionary with audio data or error
        """
        if not self.api_key:
            return {"success": False, "error": "OpenAI API key not configured"}
        
        try:
            # Use provided voice or default
            selected_voice = voice or self.voice
            
            # Ensure valid voice
            valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            if selected_voice not in valid_voices:
                selected_voice = "alloy"
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech using OpenAI TTS API
            response = openai.audio.speech.create(
                model="tts-1",
                voice=selected_voice,
                input=text
            )
            
            # Save to the temporary file
            response.stream_to_file(temp_path)
            
            # Read the file
            with open(temp_path, "rb") as audio_file:
                audio_data = audio_file.read()
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return {
                "success": True,
                "audio_data": audio_data,
                "format": "mp3"
            }
        
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            
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
    
    def set_voice(self, voice: str) -> bool:
        """
        Set the default voice for TTS
        
        Args:
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Success status
        """
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice in valid_voices:
            self.voice = voice
            return True
        return False
