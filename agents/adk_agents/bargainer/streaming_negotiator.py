"""
Streaming negotiation loop that integrates Brain + Voice
"""
import asyncio
import os
from loguru import logger
from agents.adk_agents.bargainer.streaming_voice import StreamingVoice
from agents.adk_agents.bargainer.negotiation_brain import NegotiationBrain
from agents.shared.firestore_tools import _get_db
from twilio.rest import Client

def _hangup_call(call_id: str):
    """Hang up the Twilio call"""
    try:
        # Get call SID from Firestore
        db = _get_db()
        doc = db.collection('active_calls').document(call_id).get()
        if not doc.exists:
            logger.warning(f"[{call_id}] No call state found")
            return
            
        call_state = doc.to_dict()
        call_sid = call_state.get("twilio_call_sid")
        
        if not call_sid:
            logger.warning(f"[{call_id}] No Twilio SID found")
            return
            
        # Hang up via Twilio API
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        client.calls(call_sid).update(status="completed")
        logger.success(f"[{call_id}] ☎️ Call hung up")
        
    except Exception as e:
        logger.error(f"[{call_id}] Failed to hang up: {e}")

async def run_streaming_negotiation(call_id: str, voice_stream):
    """
    Main negotiation loop using streaming voice
    """
    db = _get_db()
    doc_ref = db.collection('active_calls').document(call_id)
    doc = doc_ref.get()
    call_state = doc.to_dict() if doc.exists else {}
    
    trip_context = call_state.get("trip_context", {})
    history = call_state.get("history", [])
    round_num = 0
    max_rounds = 6
    
    brain = NegotiationBrain()
    
    try:
        while round_num < max_rounds:
            round_num += 1
            logger.info(f"[{call_id}] 🔄 Round {round_num}/{max_rounds}")
            
            # Wait for audio to be buffered (5 seconds of speech)
            logger.info(f"[{call_id}] ⏳ Waiting for vendor to speak...")
            await asyncio.sleep(5)  # Give vendor time to speak
            
            # Listen to vendor
            vendor_transcript = await voice_stream.listen()
            
            if not vendor_transcript:
                logger.warning(f"[{call_id}] No transcript, waiting longer...")
                await asyncio.sleep(3)
                vendor_transcript = await voice_stream.listen()
                
            if not vendor_transcript:
                logger.warning(f"[{call_id}] Still no transcript, skipping round")
                continue
                
            # Update history
            history.append({"role": "user", "content": vendor_transcript})
            
            # Generate response
            agent_response = brain.generate_negotiation_response(
                history=history,
                trip_context=trip_context,
                last_user_transcript=vendor_transcript
            )
            
            history.append({"role": "assistant", "content": agent_response})
            
            # Save state
            doc_ref.set({
                "history": history,
                "round": round_num,
                "last_update": asyncio.get_event_loop().time()
            }, merge=True)
            
            # Speak response
            await voice_stream.speak(agent_response)
            
            # Check if agent decided to end the call
            end_signals = [
                "धन्यवाद", "thank you", "थैंक यू",
                "फिर हम और कहीं देख लेते हैं",
                "बजट के बाहर है",
                "कन्फर्म करता हूँ", "डन", "done",
                "ठीक है भैया"
            ]
            
            if any(signal in agent_response.lower() for signal in end_signals):
                logger.success(f"[{call_id}] ✅ Agent decided to end call")
                break
                
    except Exception as e:
        logger.error(f"[{call_id}] Negotiation error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Give time for last message to play
        await asyncio.sleep(3)
        
        # Hang up the call
        _hangup_call(call_id)
        
        # Final state update
        doc_ref.set({
            "status": "COMPLETED",
            "final_round": round_num
        }, merge=True)
