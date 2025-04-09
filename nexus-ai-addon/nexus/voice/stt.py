import os
import logging
import tempfile
import asyncio
import base64
from typing import Optional, Union

logger = logging.getLogger("nexus.voice.stt")

class SpeechToText:
    """Speech-to-Text using OpenAI Whisper API."""
    
    def __init__(self):
        """Initialize the STT engine."""
        # Check if voice processing is enabled
        self.enabled = os.getenv("VOICE_ENABLED", "false").lower() == "true"
        if not self.enabled:
            logger.info("Voice processing is disabled")
            return
        
        # Get OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            logger.warning("OpenAI API key not set. Voice transcription will not work.")
            self.enabled = False
        
        # Check if we have the openai package
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized for Whisper STT")
        except ImportError:
            logger.error("OpenAI package not installed")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.enabled = False
    
    async def transcribe(self, audio_data: Union[bytes, str]) -> str:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Either raw audio bytes or a base64-encoded audio string
            
        Returns:
            Transcribed text
        """
        if not self.enabled:
            return "Voice transcription is not enabled"
        
        import openai
        
        try:
            # Handle base64-encoded audio
            if isinstance(audio_data, str):
                try:
                    audio_data = base64.b64decode(audio_data)
                except Exception as e:
                    logger.error(f"Failed to decode base64 audio: {e}")
                    return "Failed to decode audio data"
            
            # Write audio data to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # Transcribe using OpenAI Whisper API
            try:
                with open(temp_path, "rb") as audio_file:
                    response = await asyncio.to_thread(
                        self.client.audio.transcriptions.create,
                        file=audio_file,
                        model="whisper-1",
                        language="en"
                    )
                
                transcription = response.text
                logger.info(f"Transcription successful: {transcription[:50]}...")
                return transcription
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Failed to delete temporary file: {e}")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Failed to transcribe audio: {str(e)}"
