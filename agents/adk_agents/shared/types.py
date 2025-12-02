from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Deal(BaseModel):
    vendor_name: str
    phone: str
    service_type: str
    negotiated_price: float
    status: str

class Vendor(BaseModel):
    name: str
    phone: str
    category: str
    location: str
    source: str
    rating: Optional[float] = None
    metadata: Dict[str, Any] = {}

class DealsList(BaseModel):
    deals: List[Deal]

class VettedVendorsList(BaseModel):
    vendors: List[Vendor]

class FoundVendorsList(BaseModel):
    vendors: List[Vendor]

class TripContext(BaseModel):
    trip_id: str
    user_id: str = Field(description="User ID associated with the trip.")
    destination: str = Field(description="The destination for the trip.")
    category: str = Field(description="The category of service being requested (e.g., taxi, homestay).")
    query: str = Field(description="The search query for vendors.")
    budget_max: float = Field(description="The maximum budget for the service.")
    party_size: int = Field(description="Number of people traveling.")
    market_rate: Optional[float] = Field(default=None, description="The estimated market rate (calculated by Scout agent).")
    requirements: List[str] = Field(default_factory=list, description="List of specific requirements (e.g., 'one-way trip', '2 days stay', 'AC seat').")

class SessionState(BaseModel):
    """
    Strongly-typed session state model for the DesiYatra agent system.
    
    This model provides type safety and validation for all session data,
    making the data flow more explicit and reducing errors from typos.
    """
    trip_request: TripContext
    found_vendors: Optional[FoundVendorsList] = None
    safe_vendors: Optional[VettedVendorsList] = None
    final_deals: Optional[DealsList] = None