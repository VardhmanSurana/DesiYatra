"""
Production-ready tools for the Scout Agent.
"""
import httpx
import re
from typing import Dict, Any, List, Optional
from loguru import logger
import phonenumbers
import os
import json
from agents.adk_agents.shared.types import FoundVendorsList

# --- Private Helper Functions ---

def _normalize_phone(phone: str) -> Optional[str]:
    # ... (implementation unchanged)
    if not phone:
        return None
    try:
        parsed_number = phonenumbers.parse(phone, "IN")
        if phonenumbers.is_valid_number(parsed_number):
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.phonenumberutil.NumberParseException:
        logger.warning(f"Could not parse phone number: {phone}")
    return None

def _extract_and_normalize_phone(text: str) -> Optional[str]:
    # ... (implementation unchanged)
    phone_pattern = re.compile(r"(\+91[\-\s]?)?[789]\d{9}|\d{10}")
    matches = phone_pattern.finditer(text)
    for match in matches:
        normalized = _normalize_phone(match.group(0))
        if normalized:
            return normalized
    return None


# --- Live Search Tools ---

def search_google_maps(query: str, location: str, category: str) -> List[Dict[str, Any]]:
    """
    Searches Google for vendors using ADK's built-in GoogleSearchTool.
    
    This uses the native Google Search grounding feature which provides
    accurate, up-to-date information with citations.
    
    Note: This is a wrapper function. The actual GoogleSearchTool is used
    directly in the agent's tools list for better integration.
    """
    logger.info(f"🔍 Searching Google for '{query}' in '{location}' via ADK GoogleSearchTool")
    
    # This function serves as a placeholder/documentation.
    # The actual GoogleSearchTool is added directly to the agent's tools list
    # because it's a BaseTool instance that needs to be used by the LLM directly.
    
    logger.warning("This function should not be called directly. Use GoogleSearchTool in agent's tools list.")
    return []


def search_justdial(query: str, location: str, category: str) -> List[Dict[str, Any]]:
    """
    (SIMULATED) Searches JustDial for vendors.
    """
    logger.info(f"Simulating JustDial search for '{query}' in '{location}'")
    return [
        {
            "name": f"Manali Travels from JustDial",
            "phone": "+919876543210",
            "category": category,
            "location": location,
            "source": "justdial_simulated",
            "rating": 4.2,
            "metadata": {}
        }
    ]

def search_indiamart(query: str, location: str, category: str) -> List[Dict[str, Any]]:
    """
    (SIMULATED) Searches IndiaMart for vendors.
    """
    logger.info(f"Simulating IndiaMart search for '{query}' in '{location}'")
    return [
        {
            "name": f"HP Taxi Union from IndiaMart",
            "phone": "+919876543211",
            "category": category,
            "location": location,
            "source": "indiamart_simulated",
            "rating": 4.0,
            "metadata": {}
        }
    ]

def deduplicate_and_rank_vendors(vendors: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Deduplicates a list of vendors based on their phone number and ranks them.
    """
    logger.info(f"Processing {len(vendors)} vendors for deduplication and ranking.")
    
    seen_phones = set()
    deduplicated = []
    for vendor in vendors:
        phone = vendor.get("phone")
        if phone and phone not in seen_phones:
            seen_phones.add(phone)
            deduplicated.append(vendor)

    def rank_score(vendor):
        score = 0
        if vendor.get("rating"):
            score += vendor["rating"] * 10
        if vendor.get("metadata", {}).get("reviews"):
            score += vendor["metadata"]["reviews"] * 0.1
        return score

    deduplicated.sort(key=rank_score, reverse=True)
    
    final_vendors = {"vendors": deduplicated}
    logger.info(f"Returning {len(deduplicated)} unique, ranked vendors.")
    return final_vendors

def calculate_market_rate(
    vendors: List[Dict[str, Any]], 
    destination: str,
    category: str
) -> Dict[str, float]:
    """
    Calculate market rate from vendor pricing or use heuristic estimation.
    
    Returns a dict with 'market_rate' key to be merged into session state.
    """
    import statistics
    
    prices = []
    
    # Try to extract prices from vendor metadata
    for vendor in vendors:
        metadata = vendor.get("metadata", {})
        price = (
            metadata.get("quoted_price") or
            metadata.get("starting_price") or
            metadata.get("base_fare") or
            metadata.get("price")
        )
        
        if price and isinstance(price, (int, float)) and price > 0:
            prices.append(float(price))
    
    if prices:
        # Use median to avoid outliers
        market_rate = statistics.median(prices)
        logger.info(f"📊 Calculated market_rate from {len(prices)} vendors: ₹{market_rate}")
    else:
        # Fallback to heuristic estimation
        logger.warning("⚠️ No vendor pricing found, using heuristic estimation")
        market_rate = _estimate_market_rate(destination, category)
        logger.info(f"📉 Estimated market_rate: ₹{market_rate}")
    
    return {"market_rate": market_rate}


def _estimate_market_rate(destination: str, category: str) -> float:
    """Heuristic market rate estimation when vendor pricing unavailable."""
    category_lower = category.lower()
    dest_lower = destination.lower()
    
    # Hill stations
    if any(place in dest_lower for place in ["manali", "shimla", "kullu", "dharamshala", "spiti"]):
        if "taxi" in category_lower or "cab" in category_lower:
            return 3000
        elif "hotel" in category_lower or "homestay" in category_lower:
            return 1500
        elif "restaurant" in category_lower:
            return 500
    
    # Goa
    elif "goa" in dest_lower:
        if "taxi" in category_lower:
            return 2000
        elif "hotel" in category_lower:
            return 2500
        elif "restaurant" in category_lower:
            return 600
    
    # Kerala
    elif any(place in dest_lower for place in ["kerala", "kochi", "munnar", "alleppey"]):
        if "taxi" in category_lower:
            return 2200
        elif "hotel" in category_lower:
            return 1800
    
    # Default fallback
    if "taxi" in category_lower:
        return 2500
    elif "hotel" in category_lower or "homestay" in category_lower:
        return 2000
    elif "restaurant" in category_lower:
        return 500
    else:
        return 1500


def parse_found_vendors_output(llm_output: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses the LLM's raw output to extract and validate the JSON containing found vendors.
    """
    logger.info("Attempting to parse LLM output for found vendors...")
    try:
        # Try to find a JSON block in the output
        match = re.search(r"```json\n({.*?})\n```", llm_output, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = llm_output.strip() # Assume the entire output is JSON if no markdown block

        parsed_data = json.loads(json_str)
        # Validate against the Pydantic schema
        validated_data = FoundVendorsList(**parsed_data)
        logger.info("Successfully parsed and validated FoundVendorsList.")
        return validated_data.model_dump() # Return as dict for consistent handling
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e} in LLM output: {llm_output}")
        raise ValueError(f"Invalid JSON output from LLM: {llm_output}") from e
    except Exception as e:
        logger.error(f"Error parsing FoundVendorsList output: {e} in LLM output: {llm_output}")
        raise ValueError(f"Failed to parse FoundVendorsList output: {llm_output}") from e