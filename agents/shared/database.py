from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from uuid import UUID
from loguru import logger
from .config import settings


# Initialize Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)


# ============================================================================
# USER OPERATIONS
# ============================================================================

def create_user(phone_number: str, name: str, preferred_language: str = "hinglish") -> Optional[Dict[str, Any]]:
    """Create a new user."""
    try:
        data = {
            "phone_number": phone_number,
            "name": name,
            "preferred_language": preferred_language,
            "trust_score": 1.0,
        }
        response = supabase.table("users").insert(data).execute()
        logger.info(f"Created user: {phone_number}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        return None


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        return None


def get_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """Get user by phone number."""
    try:
        response = supabase.table("users").select("*").eq("phone_number", phone_number).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to get user by phone: {str(e)}")
        return None


# ============================================================================
# TRIP OPERATIONS
# ============================================================================

def create_trip(
    user_id: str,
    destination: str,
    start_date: str,
    end_date: str,
    party_size: int,
    budget_min: float,
    budget_max: float,
    budget_stretch: float,
    services: List[str],
    preferences: Dict[str, Any] = None,
) -> Optional[Dict[str, Any]]:
    """Create a new trip."""
    try:
        data = {
            "user_id": user_id,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "party_size": party_size,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "budget_stretch": budget_stretch,
            "services": services,
            "preferences": preferences or {},
            "status": "planning",
        }
        response = supabase.table("trips").insert(data).execute()
        logger.info(f"Created trip: {destination} for user {user_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to create trip: {str(e)}")
        return None


def get_trip(trip_id: str) -> Optional[Dict[str, Any]]:
    """Get trip by ID."""
    try:
        response = supabase.table("trips").select("*").eq("id", trip_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to get trip: {str(e)}")
        return None


def update_trip_status(trip_id: str, status: str, failure_reason: str = None) -> bool:
    """Update trip status."""
    try:
        data = {"status": status}
        if failure_reason:
            data["failure_reason"] = failure_reason
        
        response = supabase.table("trips").update(data).eq("id", trip_id).execute()
        logger.info(f"Updated trip {trip_id} status to {status}")
        return bool(response.data)
    except Exception as e:
        logger.error(f"Failed to update trip status: {str(e)}")
        return False


def get_user_trips(user_id: str) -> List[Dict[str, Any]]:
    """Get all trips for a user."""
    try:
        response = supabase.table("trips").select("*").eq("user_id", user_id).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get user trips: {str(e)}")
        return []


# ============================================================================
# VENDOR OPERATIONS
# ============================================================================

def create_vendor(
    phone_number: str,
    name: str,
    category: str,
    location: str,
    source: str,
    metadata: Dict[str, Any] = None,
) -> Optional[Dict[str, Any]]:
    """Create a new vendor."""
    try:
        data = {
            "phone_number": phone_number,
            "name": name,
            "category": category,
            "location": location,
            "source": source,
            "trust_score": 0.7,
            "metadata": metadata or {},
        }
        response = supabase.table("vendors").insert(data).execute()
        logger.info(f"Created vendor: {name} ({phone_number})")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to create vendor: {str(e)}")
        return None


def get_vendor(vendor_id: str) -> Optional[Dict[str, Any]]:
    """Get vendor by ID."""
    try:
        response = supabase.table("vendors").select("*").eq("id", vendor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to get vendor: {str(e)}")
        return None


def get_vendors_by_category_location(
    category: str,
    location: str,
    exclude_blacklisted: bool = True,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get vendors by category and location."""
    try:
        query = supabase.table("vendors").select("*").eq("category", category)
        
        # Filter by location (using ILIKE for case-insensitive matching)
        response = query.execute()
        
        vendors = [v for v in response.data if location.lower() in v.get("location", "").lower()]
        
        if exclude_blacklisted:
            vendors = [v for v in vendors if not v.get("is_blacklisted", False)]
        
        # Sort by trust score
        vendors.sort(key=lambda x: x.get("trust_score", 0), reverse=True)
        
        return vendors[:limit]
    except Exception as e:
        logger.error(f"Failed to get vendors: {str(e)}")
        return []


def blacklist_vendor(vendor_id: str, reason: str) -> bool:
    """Blacklist a vendor."""
    try:
        data = {
            "is_blacklisted": True,
            "blacklist_reason": reason,
        }
        response = supabase.table("vendors").update(data).eq("id", vendor_id).execute()
        logger.warning(f"Blacklisted vendor {vendor_id}: {reason}")
        return bool(response.data)
    except Exception as e:
        logger.error(f"Failed to blacklist vendor: {str(e)}")
        return False


def update_vendor_stats(
    vendor_id: str,
    success: bool,
    discount_percentage: float = 0,
) -> bool:
    """Update vendor statistics after a call."""
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return False
        
        total_calls = vendor.get("total_calls_made", 0) + 1
        successful_deals = vendor.get("successful_deals_count", 0) + (1 if success else 0)
        
        # Calculate new average discount
        old_avg = vendor.get("average_discount_percentage", 0)
        new_avg = (old_avg * (total_calls - 1) + (discount_percentage if success else 0)) / total_calls
        
        # Calculate new trust score
        trust_score = 0.5 + (successful_deals / total_calls) if total_calls > 0 else 0.7
        trust_score = min(0.95, trust_score)
        
        data = {
            "total_calls_made": total_calls,
            "successful_deals_count": successful_deals,
            "average_discount_percentage": new_avg,
            "trust_score": trust_score,
        }
        
        response = supabase.table("vendors").update(data).eq("id", vendor_id).execute()
        logger.info(f"Updated vendor {vendor_id} stats: {total_calls} calls, {successful_deals} deals")
        return bool(response.data)
    except Exception as e:
        logger.error(f"Failed to update vendor stats: {str(e)}")
        return False


# ============================================================================
# CALL OPERATIONS
# ============================================================================

def create_call(
    trip_id: str,
    vendor_id: str,
    twilio_call_sid: str = None,
) -> Optional[Dict[str, Any]]:
    """Create a new call record."""
    try:
        data = {
            "trip_id": trip_id,
            "vendor_id": vendor_id,
            "twilio_call_sid": twilio_call_sid,
            "status": "initiated",
        }
        response = supabase.table("calls").insert(data).execute()
        logger.info(f"Created call record for trip {trip_id} and vendor {vendor_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to create call: {str(e)}")
        return None


def get_call(call_id: str) -> Optional[Dict[str, Any]]:
    """Get call by ID."""
    try:
        response = supabase.table("calls").select("*").eq("id", call_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to get call: {str(e)}")
        return None


def update_call_status(
    call_id: str,
    status: str,
    outcome: str = None,
    duration_seconds: int = 0,
    initial_ask: float = None,
    final_offer: float = None,
    recording_url: str = None,
    safety_flags: List[str] = None,
) -> bool:
    """Update call status and details."""
    try:
        data = {
            "status": status,
            "duration_seconds": duration_seconds,
        }
        
        if outcome:
            data["outcome"] = outcome
        if initial_ask:
            data["initial_ask"] = initial_ask
        if final_offer:
            data["final_offer"] = final_offer
        if recording_url:
            data["recording_url"] = recording_url
        if safety_flags:
            data["safety_flags"] = safety_flags
        
        response = supabase.table("calls").update(data).eq("id", call_id).execute()
        logger.info(f"Updated call {call_id} status to {status}")
        return bool(response.data)
    except Exception as e:
        logger.error(f"Failed to update call: {str(e)}")
        return False


def add_call_event(
    call_id: str,
    event_type: str,
    data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Add an event to a call."""
    try:
        event_data = {
            "call_id": call_id,
            "event_type": event_type,
            "data": data,
        }
        response = supabase.table("call_events").insert(event_data).execute()
        logger.debug(f"Added {event_type} event to call {call_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to add call event: {str(e)}")
        return None


def get_call_events(call_id: str) -> List[Dict[str, Any]]:
    """Get all events for a call."""
    try:
        response = supabase.table("call_events").select("*").eq("call_id", call_id).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get call events: {str(e)}")
        return []


def get_trip_calls(trip_id: str) -> List[Dict[str, Any]]:
    """Get all calls for a trip."""
    try:
        response = supabase.table("calls").select("*").eq("trip_id", trip_id).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get trip calls: {str(e)}")
        return []


# ============================================================================
# MARKET RATE OPERATIONS
# ============================================================================

def get_market_rate(
    category: str,
    location: str,
) -> Optional[Dict[str, Any]]:
    """Get market rate for a service in a location."""
    try:
        response = supabase.table("market_rates").select("*").eq("category", category).execute()
        
        rates = response.data or []
        # Filter by location
        rates = [r for r in rates if location.lower() in r.get("location", "").lower()]
        
        if rates:
            # Return the most recent one
            rates.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return rates[0]
        
        return None
    except Exception as e:
        logger.error(f"Failed to get market rate: {str(e)}")
        return None


def get_market_rates_for_location(location: str) -> List[Dict[str, Any]]:
    """Get all market rates for a location."""
    try:
        response = supabase.table("market_rates").select("*").execute()
        rates = response.data or []
        
        # Filter by location
        rates = [r for r in rates if location.lower() in r.get("location", "").lower()]
        
        return rates
    except Exception as e:
        logger.error(f"Failed to get market rates: {str(e)}")
        return []


# ============================================================================
# HEALTH CHECK
# ============================================================================

def health_check() -> bool:
    """Check if Supabase connection is working."""
    try:
        response = supabase.table("users").select("*").limit(1).execute()
        logger.success("✓ Supabase connection healthy")
        return True
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {str(e)}")
        return False
