"""
Google Search Grounding Tool using raw Gemini API

This tool bypasses ADK to directly use the Gemini API's native Google Search Grounding feature.
It provides access to real-time web search results with grounding and citations.
"""
import os
from typing import Dict, Any, List
from loguru import logger
from google import genai
from google.genai import types


def search_with_google_search_grounding(query: str, location: str, category: str) -> List[Dict[str, Any]]:
    """
    Search for vendors using Google Search Grounding via the raw Gemini API.
    
    This tool uses Gemini's native Google Search integration to find vendors
    with accurate, up-to-date information directly from web search results.
    
    Args:
        query: The search query (e.g., "taxi service")
        location: The location to search in (e.g., "Manali")
        category: The category of service (e.g., "taxi", "hotel")
    
    Returns:
        List of vendor dictionaries with name, phone, rating, address, etc.
    """
    logger.info(f"🔍 [GOOGLE_SEARCH_GROUNDING] Searching for '{query}' in '{location}'")
    
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
- Website or contact information
- Any other relevant details

Return the results as a structured list of vendors."""
        
        # Make the API call with Google Search Grounding enabled
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        
        # Extract vendors from the response
        vendors = []
        
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            
            # Get the text response
            response_text = ""
            if hasattr(candidate, 'content') and candidate.content:
                if candidate.content.parts:
                    response_text = candidate.content.parts[0].text
                    logger.debug(f"Search response: {response_text[:500]}...")
            
            # Check if we have grounding metadata
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                
                if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                    logger.info(f"Found {len(grounding.grounding_chunks)} grounded results from Google Search")
                    
                    # For now, we'll parse the response text to extract vendor information
                    # In a production system, you'd want more sophisticated parsing
                    # or use the grounding metadata more directly
                    
                    # Simple extraction: look for patterns in the response
                    # This is a simplified approach - you may want to enhance this
                    lines = response_text.split('\n')
                    current_vendor = {}
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            if current_vendor and 'name' in current_vendor:
                                vendors.append(current_vendor)
                                current_vendor = {}
                            continue
                        
                        # Try to extract structured information
                        if line.startswith('*') or line.startswith('-') or line.startswith('•'):
                            line = line[1:].strip()
                        
                        # Look for name patterns
                        if not current_vendor.get('name') and any(keyword in line.lower() for keyword in ['name:', 'business:', 'vendor:']):
                            current_vendor['name'] = line.split(':', 1)[-1].strip()
                        elif not current_vendor.get('name') and len(line) < 100 and line[0].isupper():
                            current_vendor['name'] = line
                            current_vendor['phone'] = None
                            current_vendor['category'] = category
                            current_vendor['location'] = location
                            current_vendor['source'] = "google_search_grounding"
                            current_vendor['rating'] = None
                            current_vendor['metadata'] = {
                                'grounding_chunks': len(grounding.grounding_chunks) if grounding.grounding_chunks else 0
                            }
                    
                    # Add last vendor if exists
                    if current_vendor and 'name' in current_vendor:
                        vendors.append(current_vendor)
                    
                    # If no vendors extracted from parsing, create a generic entry
                    if not vendors and response_text:
                        vendors.append({
                            "name": f"Search Result from Google ({location})",
                            "phone": None,
                            "category": category,
                            "location": location,
                            "source": "google_search_grounding",
                            "rating": None,
                            "metadata": {
                                "search_summary": response_text[:200],
                                "grounding_chunks": len(grounding.grounding_chunks)
                            }
                        })
                else:
                    logger.warning("No grounding chunks found in response")
            else:
                logger.warning("No grounding metadata in response")
        
        logger.info(f"✅ Google Search Grounding returned {len(vendors)} vendors")
        return vendors
        
    except Exception as e:
        logger.error(f"❌ Google Search Grounding failed: {str(e)}")
        logger.exception(e)
        return []
