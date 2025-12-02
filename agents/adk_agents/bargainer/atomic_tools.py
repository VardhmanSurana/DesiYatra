"""
Atomic tools for the Bargainer Agent's reasoning loop.
These tools break down negotiation into discrete, composable actions.
"""
from typing import Dict, Any, Optional
from loguru import logger
from google.adk.tools.tool_context import ToolContext
import os
from twilio.rest import Client
from google.cloud import firestore
from agents.shared.firestore_tools import _get_db
import redis # Synchronous Redis client
from agents.shared.audio_utils import generate_and_store_sarvam_audio # Re-imported for initial greeting

# Twilio client (lazy init)
_twilio_client = None

def _get_twilio_client():
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
    return _twilio_client

# Synchronous Redis helper for tools
def _push_to_redis_queue_sync(call_id: str, text: str):
    try:
        r = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )
        key = f"call_queue:{call_id}"
        r.rpush(key, text)
        r.expire(key, 3600)
    except Exception as e:
        logger.error(f"Redis push failed: {e}")

# Call state storage (Firestore)
def _get_call_state(call_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve call state from Firestore."""
    try:
        db = _get_db()
        doc = db.collection('active_calls').document(call_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Failed to get call state: {e}")
        return None

def _save_call_state(call_id: str, state: Dict[str, Any]):
    """Save call state to Firestore."""
    try:
        db = _get_db()
        db.collection('active_calls').document(call_id).set(state, merge=True)
    except Exception as e:
        logger.error(f"Failed to save call state: {e}")

def _delete_call_state(call_id: str):
    """Delete call state from Firestore."""
    try:
        db = _get_db()
        db.collection('active_calls').document(call_id).delete()
    except Exception as e:
        logger.error(f"Failed to delete call state: {e}")

def initiate_call(vendor: Dict[str, Any], trip_context: Dict[str, Any], use_real_twilio: bool = False) -> Dict[str, Any]:
    """Initiates a call to a vendor and returns the call session ID."""
    call_id = f"call_{vendor['phone']}"
    
    # Pre-generate greeting audio for zero-latency start
    vendor_name = vendor.get("name", "Vendor")
    greeting_text = f"हाँ, नमस्ते। {vendor_name} से बात हो रही है?"
    vendor_gender = vendor.get("gender", "female")
    
    # Determine agent gender (opposite of vendor for natural conversation)
    agent_gender = "female" if vendor_gender == "male" else "male"
    
    call_state = {
        "vendor": vendor,
        "trip_context": trip_context,
        "round": 0,
        "current_quote": None,
        "history": [],
        "twilio_call_sid": None,
        "status": "INITIATED",
        "greeting_audio_url": None,
        "agent_gender": agent_gender
    }
    
    # Generate greeting audio file before call starts
    if use_real_twilio:
        from agents.shared.audio_utils import generate_and_store_sarvam_audio
        greeting_url = generate_and_store_sarvam_audio(call_id, greeting_text, agent_gender)
        call_state["greeting_audio_url"] = greeting_url
        logger.info(f"🎵 Pre-generated greeting: {greeting_url}")
    
    _save_call_state(call_id, call_state)
    logger.info(f"📞 Initiated call to {vendor['name']} ({call_id})")
    
    # Real Twilio call with Media Streams
    if use_real_twilio:
        try:
            from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
            
            client = _get_twilio_client()
            twilio_from = os.getenv("TWILIO_PHONE_NUMBER")
            base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
            
            # Extract domain from base_url
            domain = base_url.replace('https://', '').replace('http://', '')
            ws_url = f"wss://{domain}/twilio/stream/{call_id}"
            
            logger.info(f"🔗 WebSocket URL: {ws_url}")
            
            # TwiML: Connect to WebSocket immediately, greeting plays via WebSocket
            response = VoiceResponse()
            connect = Connect()
            stream = Stream(url=ws_url)
            connect.append(stream)
            response.append(connect)
            
            # Keep call alive for 60 seconds
            response.pause(length=60)
            
            twiml_str = str(response)
            
            # Create call
            call = client.calls.create(
                to=vendor['phone'],
                from_=twilio_from,
                twiml=twiml_str,
                status_callback=f"{base_url}/twilio/status/{call_id}",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=True
            )
            
            _save_call_state(call_id, {"twilio_call_sid": call.sid})
            logger.info(f"📞 Dialing with Media Streams... (SID: {call.sid})")
        except Exception as e:
            logger.error(f"Twilio call failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Twilio call failed: {e}"}
    
    return {
        "call_id": call_id,
        "vendor_name": vendor["name"],
        "vendor_phone": vendor["phone"],
        "status": "CALL_INITIATED",
        "twilio_call_sid": call.sid if use_real_twilio else None
    }

def send_message(call_id: str, message: str, offer: Optional[float] = None) -> Dict[str, Any]:
    """Sends a message to the vendor and receives their response."""
    call = _get_call_state(call_id)
    if not call:
        return {"error": "Invalid call_id or call expired"}
    call["round"] += 1
    call["history"].append({"agent": message, "offer": offer})
    
    logger.info(f"🗣️ Agent: {message}")
    
    # Simulate vendor response
    if call["current_quote"] is None:
        call["current_quote"] = 4000.0
        vendor_msg = f"Our rate is ₹{call['current_quote']}"
    else:
        call["current_quote"] *= 0.92
        vendor_msg = f"Best I can do is ₹{call['current_quote']}"
    
    call["history"].append({"vendor": vendor_msg})
    logger.info(f"👤 Vendor: {vendor_msg}")
    
    _save_call_state(call_id, call)
    
    return {
        "call_id": call_id,
        "vendor_response": vendor_msg,
        "current_quote": call["current_quote"],
        "round": call["round"]
    }

def accept_deal(call_id: str, final_price: float) -> Dict[str, Any]:
    """Accepts the deal at the given price and ends the call."""
    call = _get_call_state(call_id)
    if not call:
        return {"error": "Invalid call_id"}
    vendor = call["vendor"]
    
    logger.success(f"✅ Deal ACCEPTED with {vendor['name']} at ₹{final_price}")
    
    deal = {
        "vendor_name": vendor["name"],
        "phone": vendor["phone"],
        "service_type": vendor["category"],
        "negotiated_price": final_price,
        "status": "DEAL_SUCCESS"
    }
    
    _delete_call_state(call_id)
    return deal

def end_call(tool_context: ToolContext, call_id: str, reason: str = "no_deal") -> Dict[str, Any]:
    """Ends the call without a deal and signals escalation to exit the loop."""
    call = _get_call_state(call_id)
    if not call:
        return {"error": "Invalid call_id"}
    vendor = call["vendor"]
    
    logger.warning(f"❌ Call ended with {vendor['name']}: {reason}")
    
    _delete_call_state(call_id)
    tool_context.actions.escalate = True
    
    return {
        "call_id": call_id,
        "status": "CALL_ENDED",
        "reason": reason
    }