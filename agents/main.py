from fastapi import FastAPI, status, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from agents.shared import logger
import asyncio
import os
import time
import json
import httpx
from dotenv import load_dotenv
from agents.shared.audio_utils import generate_and_store_sarvam_audio
from agents.adk_agents.bargainer.google_stt_voice import GoogleSTTVoice  # Hybrid approach

# Load environment variables
load_dotenv()

app = FastAPI(
    title="DesiYatra Agent System",
    description="AI-powered travel negotiation agents for India",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory for serving audio files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    logger.info("DesiYatra Agent System starting up...")
    logger.info(f"Running in Docker: {os.getenv('DOCKER_ENV', 'False')}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("DesiYatra Agent System shutting down...")

@app.get("/")
async def root():
    return {
        "message": "DesiYatra Agent System",
        "status": "running",
        "environment": os.getenv("ENV", "development")
    }

@app.get("/health", status_code=status.HTTP_200_OK)
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    return {"ready": True, "status": "ready_to_serve"}

# --- Streaming WebSocket Endpoint (REMOVED) ---
# Previous WebSocket implementation was replaced by static audio file playback
# to resolve issues with Twilio <Gather> blocking.
# See generate_sarvam_response() for the current implementation.

# Helper for Sarvam TTS (Using Static Audio Files)
async def generate_sarvam_response(call_id: str, text: str, gender: str = "female"):
    """
    Generates TTS audio using Sarvam AI and returns TwiML with <Play>.
    This approach works with <Gather> unlike <Connect><Stream> which blocks it.
    """
    from twilio.twiml.voice_response import VoiceResponse
    
    logger.info(f"🎙️ Generating Sarvam audio for: {text[:50]}...")
    
    # Generate and store the audio file
    audio_url = generate_and_store_sarvam_audio(call_id, text, gender)
    
    response = VoiceResponse()
    
    if audio_url:
        logger.info(f"✅ Playing audio from: {audio_url}")
        response.play(audio_url)
    else:
        # Fallback to Twilio's built-in Hindi TTS
        logger.warning("⚠️ Sarvam API failed, using Twilio fallback")
        response.say(text, language="hi-IN")
    
    return response

# Twilio Webhook Endpoints

@app.post("/twilio/twiml-app")
async def twiml_app_handler(request: Request):
    """TwiML App endpoint."""
    return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Say>App initialized.</Say></Response>", media_type="application/xml")

@app.post("/twilio/start/{call_id}")
async def twilio_start_webhook(call_id: str, request: Request):
    """Start the call with a specific greeting using Sarvam."""
    from agents.shared.firestore_tools import _get_db
    
    logger.info(f"🎬 Call Started: {call_id}")
    
    db = _get_db()
    doc = db.collection('active_calls').document(call_id).get()
    call_state = doc.to_dict() if doc.exists else {}
    
    vendor = call_state.get("vendor", {})
    vendor_name = vendor.get("name", "Vendor")
    gender = vendor.get("gender", "female")
    
    greeting_text = f"Hello, {vendor_name} se bol rahe hain?"
    
    response = await generate_sarvam_response(call_id, greeting_text, gender)
    
    base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
    response.gather(
        input="speech",
        speech_timeout="auto",
        speech_model="phone_call",
        enhanced=True,
        language="hi-IN",
        action=f"{base_url}/twilio/gather/{call_id}"
    )
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/twilio/gather/{call_id}")
async def twilio_gather_callback(call_id: str, request: Request):
    """Handle speech-to-text result from <Gather> and manage conversation flow."""
    from agents.shared.firestore_tools import _get_db
    from agents.adk_agents.bargainer.negotiation_brain import NegotiationBrain
    
    form_data = await request.form()
    transcript = form_data.get("SpeechResult")
    
    logger.info(f"🗣️ User: {transcript}")
    
    db = _get_db()
    doc_ref = db.collection('active_calls').document(call_id)
    doc = doc_ref.get()
    call_state = doc.to_dict() if doc.exists else {}
    
    vendor = call_state.get("vendor", {})
    gender = vendor.get("gender", "female")
    
    current_stage = call_state.get("stage", "INITIATED")
    trip_context = call_state.get("trip_context", {})
    destination = trip_context.get("destination", "Manali")
    history = call_state.get("history", [])
    
    agent_msg = ""
    
    # State Machine
    if current_stage == "INITIATED":
        agent_msg = f"Hum {destination} ke liye taxi dekh rahe hain. 4 log hain, 3 din ke liye. Kya rate chal raha hai?"
        doc_ref.set({"stage": "NEGOTIATION"}, merge=True)
        
    elif current_stage == "NEGOTIATION":
        brain = NegotiationBrain()
        agent_msg = brain.generate_negotiation_response(
            history=history,
            trip_context=trip_context,
            last_user_transcript=transcript
        )
        history.append({"role": "user", "content": transcript})
        history.append({"role": "agent", "content": agent_msg})
        doc_ref.set({"history": history}, merge=True)
        
    else:
        agent_msg = "Theek hai, dhanyavaad."
    
    logger.info(f"🤖 Agent: {agent_msg}")
    
    response = await generate_sarvam_response(call_id, agent_msg, gender)
    
    base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
    response.gather(
        input="speech",
        speech_timeout="auto",
        speech_model="phone_call",
        enhanced=True,
        language="hi-IN",
        action=f"{base_url}/twilio/gather/{call_id}"
    )
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/twilio/status/{call_id}")
async def twilio_status_callback(call_id: str, request: Request):
    """Handle call status updates."""
    form_data = await request.form()
    call_status = form_data.get("CallStatus")
    
    if call_status in ["completed", "failed", "busy", "no-answer"]:
        logger.info(f"🏁 Call Ended: {call_status}")
    
    return {"status": "acknowledged"}

@app.post("/twilio/voice/{call_id}")
async def twilio_voice_webhook(call_id: str, request: Request):
    from twilio.twiml.voice_response import VoiceResponse
    response = VoiceResponse()
    response.say("Deprecated endpoint.")
    return Response(content=str(response), media_type="application/xml")

@app.post("/twilio/recording/{call_id}")
async def twilio_recording_callback(call_id: str, request: Request):
    return {"status": "processed"}

@app.post("/twilio/transcription/{call_id}")
async def twilio_transcription_callback(call_id: str, request: Request):
    return {"status": "acknowledged"}

@app.post("/twilio/incoming")
async def twilio_incoming_webhook(request: Request):
    from twilio.twiml.voice_response import VoiceResponse
    response = VoiceResponse()
    response.say("Incoming call handler")
    return Response(content=str(response), media_type="application/xml")

# --- Twilio Media Streams WebSocket ---
active_streams = {}  # Store active streaming sessions

@app.websocket("/twilio/stream/{call_id}")
async def twilio_media_stream(websocket: WebSocket, call_id: str):
    """Handle bidirectional audio streaming with Twilio Media Streams"""
    logger.info(f"🔌 WebSocket connection attempt for call: {call_id}")
    
    await websocket.accept()
    logger.info(f"✅ WebSocket accepted for call: {call_id}")
    
    # Get gender from call state
    from agents.shared.firestore_tools import _get_db
    db = _get_db()
    doc = db.collection('active_calls').document(call_id).get()
    call_state = doc.to_dict() if doc.exists else {}
    agent_gender = call_state.get("agent_gender", "male")
    
    stream_sid = None
    voice_stream = GoogleSTTVoice(call_id, gender=agent_gender)  # Hybrid: Sarvam TTS + Google STT
    negotiation_task = None
    
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")
            
            if event == "start":
                stream_sid = data["start"]["streamSid"]
                voice_stream.attach_twilio_ws(websocket, stream_sid)
                active_streams[call_id] = voice_stream
                logger.info(f"📞 Stream started: {stream_sid}")
                
                # Play greeting immediately via WebSocket
                vendor = call_state.get("vendor", {})
                vendor_name = vendor.get("name", "Vendor")
                greeting_text = f"Hello, {vendor_name} se bol rahe hain?"
                await voice_stream.speak(greeting_text)
                
                # Start negotiation loop
                from agents.adk_agents.bargainer.streaming_negotiator import run_streaming_negotiation
                negotiation_task = asyncio.create_task(
                    run_streaming_negotiation(call_id, voice_stream)
                )
                
            elif event == "media":
                # Incoming audio from vendor
                payload = data["media"]["payload"]
                await voice_stream.process_twilio_audio(payload)
                
            elif event == "stop":
                logger.info(f"🛑 Stream stopped: {stream_sid}")
                if negotiation_task:
                    negotiation_task.cancel()
                break
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {call_id}")
    except Exception as e:
        logger.error(f"❌ Stream error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if negotiation_task:
            negotiation_task.cancel()
        await voice_stream.cleanup()
        if call_id in active_streams:
            del active_streams[call_id]
