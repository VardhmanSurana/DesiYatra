
import os
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.api_core.exceptions import NotFound
from loguru import logger

# Singleton Firestore Client
_firestore_client = None

def _get_db():
    global _firestore_client
    if _firestore_client is None:
        try:
            _firestore_client = firestore.Client()
            logger.info("🔥 Firestore Client Initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore: {e}")
            raise e
    return _firestore_client

# ============================================================================
# AGENT TOOLS
# ============================================================================

def save_negotiation_memory(
    session_id: str,
    memory_type: str,
    content: Dict[str, Any]
) -> str:
    """
    Saves a piece of information to the agent's long-term memory (Firestore).
    
    Args:
        session_id: The unique ID of the call/session.
        memory_type: The category of memory (e.g., 'vendor_profile', 'negotiation_tactic', 'user_preference').
        content: The actual data to save as a JSON object.
        
    Returns:
        A success message with the document ID.
    """
    try:
        db = _get_db()
        # We store memories in a sub-collection of the session or a root 'memories' collection
        # For easy retrieval, let's use a root collection 'agent_memories'
        
        doc_ref = db.collection('agent_memories').document()
        data = {
            "session_id": session_id,
            "type": memory_type,
            "content": content,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(data)
        return f"✅ Memory saved successfully (ID: {doc_ref.id})"
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")
        return f"❌ Error saving memory: {str(e)}"

def get_negotiation_history(session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves the recent negotiation history for a specific session.
    
    Args:
        session_id: The unique ID of the call/session.
        limit: Max number of recent entries to return (default: 5).
        
    Returns:
        A list of memory objects containing the history.
    """
    try:
        db = _get_db()
        query = (
            db.collection('agent_memories')
            .where('session_id', '==', session_id)
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            # Convert timestamp to string for JSON serialization
            if 'timestamp' in data:
                data['timestamp'] = str(data['timestamp'])
            results.append(data)
            
        return results
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return []

def update_vendor_profile(
    phone_number: str,
    updates: Dict[str, Any]
) -> str:
    """
    Updates the persistent profile of a vendor based on new findings.
    Use this to record if a vendor is 'stubborn', 'flexible', or has specific constraints.
    
    Args:
        phone_number: The vendor's phone number (unique ID).
        updates: A dictionary of attributes to update (e.g., {"negotiation_style": "aggressive"}).
        
    Returns:
        Status message.
    """
    try:
        db = _get_db()
        # Sanitize phone number for use as doc ID
        doc_id = phone_number.replace("+", "").replace(" ", "")
        doc_ref = db.collection('vendor_profiles').document(doc_id)
        
        doc_ref.set(updates, merge=True)
        return f"✅ Vendor profile updated for {phone_number}"
    except Exception as e:
        logger.error(f"Failed to update vendor profile: {e}")
        return f"❌ Error updating profile: {str(e)}"

def get_vendor_profile(phone_number: str) -> Dict[str, Any]:
    """
    Retrieves the known profile of a vendor.
    
    Args:
        phone_number: The vendor's phone number.
        
    Returns:
        The vendor's profile data or an empty dict if new.
    """
    try:
        db = _get_db()
        doc_id = phone_number.replace("+", "").replace(" ", "")
        doc_ref = db.collection('vendor_profiles').document(doc_id)
        
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return {"status": "new_vendor", "message": "No prior history found."}
    except Exception as e:
        logger.error(f"Failed to get vendor profile: {e}")
        return {}
