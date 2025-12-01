import os
import time
import base64
from twilio.twiml.voice_response import VoiceResponse
from agents.adk_agents.bargainer.voice_pipeline import VoicePipeline
from agents.shared.logger import logger

def generate_and_store_sarvam_audio(call_id: str, text: str, gender: str = "female") -> str:
    """
    Generates audio using Sarvam TTS, saves it to a static file, and returns the URL.
    """
    speaker_map = {
        "male": "viraj",
        "female": "anushka"
    }
    speaker = speaker_map.get(gender.lower(), "anushka")
    
    pipeline = VoicePipeline(call_id)
    audio_bytes = pipeline.speak(text, use_real_tts=True, speaker=speaker)
    
    if audio_bytes:
        filename = f"{call_id}_{int(time.time())}.wav"
        filepath = f"static/audio/{filename}"
        
        os.makedirs("static/audio", exist_ok=True)
        
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
            
        base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        audio_url = f"{base_url}/static/audio/{filename}"
        
        logger.info(f"🔊 Sarvam Audio generated and saved: {audio_url}")
        return audio_url
    else:
        logger.warning(f"⚠️ Sarvam TTS failed to generate audio for text: {text}")
        return ""
