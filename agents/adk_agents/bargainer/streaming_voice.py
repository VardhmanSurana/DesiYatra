"""
Real-time voice streaming using Sarvam AI + Twilio Media Streams
"""
import os
import asyncio
import base64
import json
import subprocess
from typing import Optional
from loguru import logger
from sarvamai import AsyncSarvamAI, AudioOutput, EventResponse

def convert_mp3_to_mulaw(mp3_bytes: bytes) -> bytes:
    """Convert MP3 audio to mulaw format for Twilio using ffmpeg"""
    try:
        process = subprocess.Popen(
            [
                'ffmpeg',
                '-i', 'pipe:0',  # Input from stdin
                '-f', 'mulaw',   # Output format
                '-ar', '8000',   # Sample rate 8kHz
                '-ac', '1',      # Mono
                'pipe:1'         # Output to stdout
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        mulaw_bytes, stderr = process.communicate(input=mp3_bytes)
        
        if process.returncode != 0:
            logger.error(f"ffmpeg conversion failed: {stderr.decode()}")
            return b""
            
        return mulaw_bytes
    except FileNotFoundError:
        logger.error("ffmpeg not found - install with: apt-get install ffmpeg")
        return b""
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        return b""

class StreamingVoice:
    """Bidirectional streaming: Twilio -> Sarvam STT -> Brain -> Sarvam TTS -> Twilio"""
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.sarvam_key = os.getenv("SARVAM_API_KEY")
        self.client = AsyncSarvamAI(api_subscription_key=self.sarvam_key)
        self.tts_ws = None
        self.stt_ws = None
        self.twilio_ws = None
        self.listening = False
        
    async def setup_tts(self):
        """Initialize TTS WebSocket with basic settings (codec not supported by SDK)"""
        self.tts_ws = await self.client.text_to_speech_streaming.connect(
            model="bulbul:v2",
            send_completion_event=True
        ).__aenter__()
        
        await self.tts_ws.configure(
            target_language_code="hi-IN",
            speaker="anushka"
            # Note: output_audio_codec not supported by SDK
            # Default output is MP3, need to convert to mulaw for Twilio
        )
        logger.info(f"[{self.call_id}] TTS configured (default MP3 output)")
        
    async def setup_stt(self):
        """Initialize STT WebSocket for Hindi recognition"""
        self.stt_ws = await self.client.speech_to_text_streaming.connect(
            language_code="hi-IN",
            model="saarika:v2.5",
            sample_rate=8000,  # Twilio telephony
            high_vad_sensitivity=True,
            vad_signals=True,
            flush_signal=True
        ).__aenter__()
        logger.info(f"[{self.call_id}] STT configured (8kHz Hindi)")
        
    async def speak(self, text: str):
        """Stream Hindi text as audio to Twilio (with MP3→mulaw conversion)"""
        if not self.tts_ws:
            await self.setup_tts()
            
        logger.info(f"[{self.call_id}] 🗣️ Agent: {text}")
        
        # Send text to Sarvam TTS
        await self.tts_ws.convert(text)
        await self.tts_ws.flush()
        
        # Collect MP3 chunks and convert to mulaw
        mp3_chunks = []
        
        async for message in self.tts_ws:
            if isinstance(message, AudioOutput):
                audio_chunk = base64.b64decode(message.data.audio)
                mp3_chunks.append(audio_chunk)
                    
            elif isinstance(message, EventResponse):
                if message.data.event_type == "final":
                    logger.info(f"[{self.call_id}] ✅ TTS complete, converting to mulaw...")
                    
                    # Combine MP3 chunks
                    full_mp3 = b"".join(mp3_chunks)
                    
                    # Convert to mulaw for Twilio
                    mulaw_audio = await asyncio.to_thread(convert_mp3_to_mulaw, full_mp3)
                    
                    if mulaw_audio and self.twilio_ws:
                        # Send mulaw audio to Twilio
                        media_msg = {
                            "event": "media",
                            "streamSid": self.twilio_ws.get("streamSid"),
                            "media": {
                                "payload": base64.b64encode(mulaw_audio).decode()
                            }
                        }
                        await self.twilio_ws["websocket"].send_text(json.dumps(media_msg))
                        logger.info(f"[{self.call_id}] 📤 Sent {len(mulaw_audio)} bytes mulaw audio")
                    
                    self.listening = True
                    break
                    
    async def listen(self) -> str:
        """Listen to vendor speech and return transcript"""
        if not self.stt_ws:
            await self.setup_stt()
            
        self.listening = True
        transcript = ""
        
        async for message in self.stt_ws:
            if not self.listening:
                break
                
            if message.get("type") == "speech_start":
                logger.info(f"[{self.call_id}] 🎤 Vendor speaking...")
                
            elif message.get("type") == "speech_end":
                logger.info(f"[{self.call_id}] 🔇 Vendor stopped")
                # Force processing
                await self.stt_ws.flush()
                
            elif message.get("type") == "transcript":
                transcript = message.get("text", "")
                logger.info(f"[{self.call_id}] 👤 Vendor: {transcript}")
                self.listening = False
                break
                
        return transcript
        
    async def process_twilio_audio(self, audio_payload: str):
        """Process incoming audio from Twilio Media Stream"""
        if not self.stt_ws:
            await self.setup_stt()
            
        if not self.listening:
            return
            
        # Twilio sends mulaw, convert to PCM if needed
        audio_bytes = base64.b64decode(audio_payload)
        
        # Send to Sarvam STT
        await self.stt_ws.transcribe(
            audio=base64.b64encode(audio_bytes).decode(),
            encoding="audio/wav",
            sample_rate=8000
        )
        
    def attach_twilio_ws(self, websocket, stream_sid: str):
        """Attach Twilio WebSocket for bidirectional streaming"""
        self.twilio_ws = {
            "websocket": websocket,
            "streamSid": stream_sid
        }
        logger.info(f"[{self.call_id}] Twilio WS attached (SID: {stream_sid})")
        
    async def cleanup(self):
        """Close all WebSocket connections"""
        if self.tts_ws:
            await self.tts_ws.__aexit__(None, None, None)
        if self.stt_ws:
            await self.stt_ws.__aexit__(None, None, None)
        logger.info(f"[{self.call_id}] Streaming cleanup complete")
