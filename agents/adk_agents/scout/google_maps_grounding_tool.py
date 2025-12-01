"""
Google Maps Grounding Tool using raw Gemini API

This tool bypasses ADK to directly use the Gemini API's native Google Maps Grounding feature.
It provides access to real-time, grounded location data from Google Maps.
"""
import os
from typing import Dict, Any, List
from loguru import logger
from google import genai
from google.genai import types


def search_with_google_maps_grounding(query: str, location: str, category: str) -> List[Dict[str, Any]]:
    """
    Search for vendors using Google Maps Grounding via the raw Gemini API.
    
    This tool uses Gemini's native Google Maps integration to find real-world
    vendors with accurate, up-to-date information directly from Google Maps.
    
    Args:
        query: The search query (e.g., "taxi service")
        location: The location to search in (e.g., "Manali")
        category: The category of service (e.g., "taxi", "hotel")
    
    Returns:
        List of vendor dictionaries with name, phone, rating, address, etc.
    """
    logger.info(f"🗺️ [GOOGLE_MAPS_GROUNDING] Searching for '{query}' in '{location}'")
    
    try:
        # Initialize the Gemini client
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Construct the search prompt
        prompt = f"""Find {category} vendors for "{query}" in {location}.
        
For each vendor found, extract:
- Business name
- Phone number (if available)
- Rating
- Address
- Any other relevant details

Return the results as a structured list."""
        
        # Make the API call with Google Maps Grounding enabled
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_maps=types.GoogleMaps())],
            ),
        )
        
        # Extract vendors from the grounding metadata
        vendors = []
        
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            
            # Check if we have grounding metadata
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                
                if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                    logger.info(f"Found {len(grounding.grounding_chunks)} grounded results from Google Maps")
                    
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'maps') and chunk.maps:
                            maps_data = chunk.maps
                            
                            vendor = {
                                "name": getattr(maps_data, 'title', 'Unknown'),
                                "phone": None,  # Phone not directly in grounding metadata
                                "category": category,
                                "location": location,
                                "source": "google_maps_grounding",
                                "rating": None,  # Rating not directly in grounding metadata
                                "metadata": {
                                    "place_id": getattr(maps_data, 'place_id', None),
                                    "uri": getattr(maps_data, 'uri', None),
                                }
                            }
                            vendors.append(vendor)
                else:
                    logger.warning("No grounding chunks found in response")
            else:
                logger.warning("No grounding metadata in response")
            
            # Log the response text for debugging
            if hasattr(candidate, 'content') and candidate.content:
                logger.debug(f"Response text: {candidate.content.parts[0].text if candidate.content.parts else 'No text'}")
        
        logger.info(f"✅ Google Maps Grounding returned {len(vendors)} vendors")
        return vendors
        
    except Exception as e:
        logger.error(f"❌ Google Maps Grounding search failed: {str(e)}")
        logger.exception(e)
        return []
