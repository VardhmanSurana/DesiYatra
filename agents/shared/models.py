from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TripStatus(str, Enum):
    PLANNING = "planning"
    SCOUTING = "scouting"
    VETTING = "vetting"
    NEGOTIATING = "negotiating"
    CONFIRMING = "confirming"
    COMPLETE = "complete"
    FAILED = "failed"


class CallStatus(str, Enum):
    INITIATED = "initiated"
    CONNECTED = "connected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class CallOutcome(str, Enum):
    AGREED = "agreed"
    REJECTED = "rejected"
    NO_ANSWER = "no_answer"
    FRAUD_DETECTED = "fraud_detected"
    VENDOR_UNAVAILABLE = "vendor_unavailable"


class VendorCategory(str, Enum):
    TAXI = "taxi"
    HOMESTAY = "homestay"
    GUIDE = "guide"
    ACTIVITY = "activity"


class SafetyRecommendation(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    BLOCK = "BLOCK"


class Trip(BaseModel):
    id: Optional[str] = None
    user_id: str
    destination: str
    start_date: str
    end_date: str
    party_size: int
    budget_min: float
    budget_max: float
    budget_stretch: float
    services: List[str]
    preferences: Dict[str, Any] = {}
    status: TripStatus = TripStatus.PLANNING
    created_at: Optional[datetime] = None


class Vendor(BaseModel):
    id: Optional[str] = None
    phone: str
    name: str
    category: VendorCategory
    location: str
    source: str
    trust_score: float = 0.7
    metadata: Dict[str, Any] = {}


class Call(BaseModel):
    id: Optional[str] = None
    trip_id: str
    vendor_id: str
    twilio_call_sid: Optional[str] = None
    status: CallStatus = CallStatus.INITIATED
    duration: int = 0
    initial_ask: Optional[float] = None
    final_offer: Optional[float] = None
    outcome: Optional[CallOutcome] = None
    recording_url: Optional[str] = None
    transcript: List[Dict[str, Any]] = []
    safety_flags: List[str] = []
    negotiation_summary: Dict[str, Any] = {}


class AgentUpdate(BaseModel):
    trip_id: str
    agent: str
    state: str
    message: str
    data: Dict[str, Any] = {}
    timestamp: datetime = datetime.now()
