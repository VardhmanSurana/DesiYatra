"""
Voice Pipeline using Sarvam AI TTS
"""
import os
import requests
import base64
from loguru import logger

class VoicePipeline:
    """
    Real-time voice interface with Sarvam AI TTS for Hindi.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.sarvam_api_key = os.getenv("SARVAM_API_KEY")
        logger.info(f"🎤 Voice Pipeline initialized for call {self.session_id}")

    def speak(self, text: str, use_real_tts: bool = False, speaker: str = "anushka") -> bytes:
        """
        Converts text to speech using Sarvam AI TTS.
        Returns audio bytes that can be streamed to Twilio.
        """
        logger.info(f"[{self.session_id}] AGENT SAYS (Speaker: {speaker}): {text}")
        
        if not use_real_tts:
            return b""  # Simulated mode
        
        if not self.sarvam_api_key:
            logger.error("❌ SARVAM_API_KEY not set!")
            return b""
        
        try:
            url = "https://api.sarvam.ai/text-to-speech"
            headers = {
                "api-subscription-key": self.sarvam_api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": [text],
                "target_language_code": "hi-IN",
                "speaker": speaker,
                "model": "bulbul:v2",
                "enable_preprocessing": True
            }
            
            logger.info(f"🔄 Calling Sarvam TTS API...")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            logger.info(f"📡 Sarvam API Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Sarvam API Error: {response.text}")
                return b""
            
            response.raise_for_status()
            
            # Decode base64 audio
            audio_base64 = response.json()["audios"][0]
            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"✅ Sarvam AI TTS generated {len(audio_bytes)} bytes")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"❌ Sarvam AI TTS failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        return b""

    def listen(self, audio_url: str = None, use_real_stt: bool = False) -> str:
        """
        Simulated STT - returns mock response.
        """
        if not use_real_stt:
            response = "Our best price is 3200."
            logger.info(f"[{self.session_id}] VENDOR SAYS: {response}")
            return response
        
        logger.info("Real STT not implemented yet")
        return ""
