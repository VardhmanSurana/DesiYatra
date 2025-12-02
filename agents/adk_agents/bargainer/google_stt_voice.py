"""
Hybrid: Sarvam TTS + Google STT (Production Ready)
"""
import os
import asyncio
import base64
import json
import subprocess
from typing import Optional
from loguru import logger
from google.cloud import speech_v1
from sarvamai import AsyncSarvamAI, AudioOutput, EventResponse

def convert_mp3_to_mulaw(mp3_bytes: bytes) -> bytes:
    """Convert MP3 to mulaw using ffmpeg"""
    try:
        process = subprocess.Popen(
            ['ffmpeg', '-i', 'pipe:0', '-f', 'mulaw', '-ar', '8000', '-ac', '1', 'pipe:1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        mulaw_bytes, _ = process.communicate(input=mp3_bytes)
        return mulaw_bytes
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return b""

class GoogleSTTVoice:
    """Hybrid: Sarvam TTS + Google STT"""
    
    def __init__(self, call_id: str, gender: str = "male"):
        self.call_id = call_id
        self.gender = gender.lower()
        self.speaker = "hitesh" if self.gender == "male" else "manisha"
        self.sarvam_key = os.getenv("SARVAM_API_KEY")
        self.sarvam_client = AsyncSarvamAI(api_subscription_key=self.sarvam_key)
        self.google_client = speech_v1.SpeechClient()
        self.tts_ws = None
        self.twilio_ws = None
        self.audio_buffer = []
        logger.info(f"[{self.call_id}] Voice: {self.speaker} ({self.gender})")
        
    async def setup_tts(self):
        """Initialize Sarvam TTS - not needed with per-call connections"""
        logger.info(f"[{self.call_id}] Sarvam TTS ready (using per-call connections)")
        
    async def speak(self, text: str):
        """Generate speech with Sarvam TTS, convert to mulaw, send to Twilio"""
        logger.info(f"[{self.call_id}] 🗣️ Agent: {text}")
        
        # Create fresh TTS connection each time
        async with self.sarvam_client.text_to_speech_streaming.connect(
            model="bulbul:v2",
            send_completion_event=True
        ) as tts_ws:
            await tts_ws.configure(
                target_language_code="hi-IN",
                speaker=self.speaker
            )
            logger.info(f"[{self.call_id}] ✅ TTS configured")
            
            await tts_ws.convert(text)
            await tts_ws.flush()
            logger.info(f"[{self.call_id}] ✅ TTS convert & flush done, waiting for audio...")
            
            mp3_chunks = []
            async for message in tts_ws:
                if isinstance(message, AudioOutput):
                    chunk = base64.b64decode(message.data.audio)
                    mp3_chunks.append(chunk)
                    logger.info(f"[{self.call_id}] 📦 Got MP3 chunk: {len(chunk)} bytes")
                elif isinstance(message, EventResponse):
                    logger.info(f"[{self.call_id}] 📢 Event: {message.data.event_type}")
                    if message.data.event_type == "final":
                        break
        
        if not mp3_chunks:
            logger.error(f"[{self.call_id}] ❌ No MP3 chunks received!")
            return
            
        # Convert MP3 to mulaw
        full_mp3 = b"".join(mp3_chunks)
        logger.info(f"[{self.call_id}] 🔄 Converting {len(full_mp3)} bytes MP3 to mulaw...")
        
        mulaw_audio = await asyncio.to_thread(convert_mp3_to_mulaw, full_mp3)
        logger.info(f"[{self.call_id}] ✅ Converted to {len(mulaw_audio)} bytes mulaw")
        
        if mulaw_audio and self.twilio_ws:
            media_msg = {
                "event": "media",
                "streamSid": self.twilio_ws["streamSid"],
                "media": {"payload": base64.b64encode(mulaw_audio).decode()}
            }
            await self.twilio_ws["websocket"].send_text(json.dumps(media_msg))
            logger.info(f"[{self.call_id}] 📤 Sent {len(mulaw_audio)} bytes to Twilio")
        else:
            logger.error(f"[{self.call_id}] ❌ No audio or no WebSocket!")
                    
    async def listen(self) -> str:
        """Transcribe buffered audio with Google STT"""
        if not self.audio_buffer:
            logger.warning(f"[{self.call_id}] No audio to transcribe")
            return ""
            
        # Combine buffered audio
        full_audio = b"".join(self.audio_buffer)
        self.audio_buffer = []
        
        logger.info(f"[{self.call_id}] 🎧 Transcribing {len(full_audio)} bytes...")
        
        try:
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.MULAW,
                sample_rate_hertz=8000,
                language_code="hi-IN",
                enable_automatic_punctuation=True,
                model="default"
            )
            
            audio = speech_v1.RecognitionAudio(content=full_audio)
            response = self.google_client.recognize(config=config, audio=audio)
            
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                logger.info(f"[{self.call_id}] 👤 Vendor: {transcript} ({confidence:.0%})")
                return transcript
            else:
                logger.warning(f"[{self.call_id}] No transcription results")
                return ""
                
        except Exception as e:
            logger.error(f"[{self.call_id}] STT error: {e}")
            return ""
        
    async def process_twilio_audio(self, audio_payload: str):
        """Buffer incoming mulaw audio from Twilio"""
        audio_bytes = base64.b64decode(audio_payload)
        self.audio_buffer.append(audio_bytes)
        
    def attach_twilio_ws(self, websocket, stream_sid: str):
        """Attach Twilio WebSocket"""
        self.twilio_ws = {
            "websocket": websocket,
            "streamSid": stream_sid
        }
        logger.info(f"[{self.call_id}] Twilio attached")
        
    async def cleanup(self):
        """Cleanup"""
        logger.info(f"[{self.call_id}] Cleanup done")
