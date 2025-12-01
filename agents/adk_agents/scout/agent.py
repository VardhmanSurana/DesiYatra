"""
ADK-based Scout Agent with Parallel-Sequential Workflow

This module defines a composable Scout Agent using ParallelAgent for concurrent
searches and SequentialAgent for the overall pipeline.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from agents.adk_agents.shared.custom_planners import get_planner
from agents.adk_agents.scout import tools as scout_tools
from agents.adk_agents.scout.google_maps_grounding_tool import search_with_google_maps_grounding
from agents.adk_agents.scout.google_search_grounding_tool import search_with_google_search_grounding
from google.genai import types
from agents.adk_agents.shared.types import FoundVendorsList

# Individual search agents for parallel execution
google_search_agent = LlmAgent(
    name="GoogleSearchAgent",
    model="gemini-pro-latest",
    description="Searches vendors using Google Search grounding.",
    instruction="""
    Extract query, location, and category from trip_request in session state.
    Call `search_with_google_search_grounding` with these parameters.
    Store results in state under 'google_search_results'.
    """,
    tools=[search_with_google_search_grounding],
    output_key="google_search_results",
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

google_maps_agent = LlmAgent(
    name="GoogleMapsAgent",
    model="gemini-pro-latest",
    description="Searches vendors using Google Maps grounding.",
    instruction="""
    Extract query, location, and category from trip_request in session state.
    Call `search_with_google_maps_grounding` with these parameters.
    Store results in state under 'google_maps_results'.
    """,
    tools=[search_with_google_maps_grounding],
    output_key="google_maps_results",
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

justdial_agent = LlmAgent(
    name="JustDialAgent",
    model="gemini-pro-latest",
    description="Searches vendors on JustDial.",
    instruction="""
    Extract query, location, and category from trip_request in session state.
    Call `search_justdial` with these parameters.
    Store results in state under 'justdial_results'.
    """,
    tools=[scout_tools.search_justdial],
    output_key="justdial_results",
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

indiamart_agent = LlmAgent(
    name="IndiaMartAgent",
    model="gemini-pro-latest",
    description="Searches vendors on IndiaMart.",
    instruction="""
    Extract query, location, and category from trip_request in session state.
    Call `search_indiamart` with these parameters.
    Store results in state under 'indiamart_results'.
    """,
    tools=[scout_tools.search_indiamart],
    output_key="indiamart_results",
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

# Parallel search execution
parallel_search_agent = ParallelAgent(
    name="ParallelSearchAgent",
    description="Executes all vendor searches concurrently.",
    sub_agents=[
        google_search_agent,
        google_maps_agent,
        justdial_agent,
        indiamart_agent,
    ]
)

# Processing agent to consolidate and rank results
processing_agent = LlmAgent(
    name="ProcessingAgent",
    model="gemini-pro-latest",
    description="Consolidates and ranks vendor search results.",
    instruction="""
    Consolidate all vendor results from:
    - {google_search_results}
    - {google_maps_results}
    - {justdial_results}
    - {indiamart_results}
    
    Merge them into a single list, then call `deduplicate_and_rank_vendors`.
    
    **OUTPUT FORMAT:**
    Your response MUST be ONLY valid JSON matching this schema: {"vendors": [...]}
    Do NOT include any explanatory text, greetings, or markdown formatting.
    Start with { and end with }.
    """,
    tools=[scout_tools.deduplicate_and_rank_vendors],
    output_key="found_vendors",
    output_schema=FoundVendorsList,
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
    ),
    planner=get_planner("vendor_selection")  # Custom vendor selection logic
)

# Market rate calculation agent
market_rate_agent = LlmAgent(
    name="MarketRateAgent",
    model="gemini-pro-latest",
    description="Calculates market rate from vendor pricing.",
    instruction="""
    You have access to found_vendors and trip_request from session state.
    
    Call `calculate_market_rate` with:
    - vendors: the list from found_vendors.vendors
    - destination: from trip_request.destination
    - category: from trip_request.category
    
    This will calculate the market rate and store it in session state.
    
    Simply acknowledge that market rate has been calculated.
    """,
    tools=[scout_tools.calculate_market_rate],
    output_key="market_rate_calculated",
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=256,
    ),
)

# Main Scout Agent - Sequential pipeline: Parallel Search → Process → Calculate Market Rate
scout_agent = SequentialAgent(
    name="ScoutAgent",
    description="Finds vendors, ranks them, and calculates market rate.",
    sub_agents=[
        parallel_search_agent,
        processing_agent,
        market_rate_agent,  # Added market rate calculation
    ]
)