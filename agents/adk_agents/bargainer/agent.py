from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from agents.adk_agents.bargainer import atomic_tools
from agents.shared import firestore_tools, vector_tools
from google.genai import types
from agents.adk_agents.shared.types import DealsList
from agents.adk_agents.shared.custom_planners import get_planner

# Negotiation Turn Agent - Makes decisions during each negotiation round
negotiation_turn_agent = LlmAgent(
    name="NegotiationTurnAgent",
    model="gemini-pro-latest",
    description="Conducts one turn of negotiation with a vendor.",
    instruction="""
    You are negotiating with a vendor.
    
    **Step 1: Check Context**
    - Call `get_vendor_profile` using `{vendor_phone}` to check their negotiation style.
    - Call `search_knowledge_base` with a query like "how to handle stubborn vendor" or "negotiation tactics for {vendor_name}" to find relevant strategies.
    
    **Step 2: Decide Move**
    Based on the call history, current quote, vendor profile, and **retrieved tactics**:
    - If current_quote <= budget_max: Call `accept_deal` with the current_quote.
    - If current_quote > budget_max but close: Use `send_message` with a counter-offer at market_rate.
      - If vendor is 'stubborn', make smaller concessions.
      - If vendor is 'flexible', hold firm on price.
    - If round >= 5: Call `end_call` with reason "max_rounds_reached".
    
    **Step 3: Update Memory**
    - Call `save_negotiation_memory` to record significant events (e.g., "offer_rejected", "counter_made").
    - If you detect a specific style (e.g., they refuse to budge), call `update_vendor_profile`.
    
    Current state:
    - Call ID: {call_id}
    - Vendor: {vendor_name} ({vendor_phone})
    - Current Quote: ₹{current_quote}
    - Market Rate: ₹{market_rate}
    - Budget Max: ₹{budget_max}
    - Round: {round}
    
    Use Hindi/Hinglish phrases like "Thoda kam kar dijiye", "Market rate ₹X hai", "Done, deal pakki".
    """,
    tools=[
        atomic_tools.send_message,
        atomic_tools.accept_deal,
        atomic_tools.end_call,
        firestore_tools.get_vendor_profile,
        firestore_tools.update_vendor_profile,
        firestore_tools.save_negotiation_memory,
        vector_tools.search_knowledge_base,
    ],
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=512,
    ),
)

# Negotiation Loop - Iterates until deal is made or call ends
negotiation_loop = LoopAgent(
    name="NegotiationLoop",
    sub_agents=[negotiation_turn_agent],
    max_iterations=6,
)

# Vendor Iterator Agent - Initiates calls for each vendor
vendor_iterator_agent = LlmAgent(
    name="VendorIteratorAgent",
    model="gemini-pro-latest",
    description="Initiates negotiation calls with each vendor.",
    instruction="""
    You will receive safe_vendors and trip_request from session state.
    
    For EACH vendor in safe_vendors:
    1. Call `initiate_call` with the vendor and trip_request
    2. Store the call_id in state
    3. The negotiation_loop will handle the actual negotiation
    
    After all vendors are processed, output the collected deals as JSON: {"deals": [...]}
    """,
    tools=[atomic_tools.initiate_call],
    output_key="final_deals",
    output_schema=DealsList,
    include_contents='none',
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
    ),
    planner=get_planner("negotiation", max_rounds=6)  # Custom negotiation strategy
)

# Main Bargainer Agent - Sequential pipeline
bargainer_agent = SequentialAgent(
    name="BargainerAgent",
    description="Reasoning-based negotiation agent that uses atomic tools in a loop.",
    sub_agents=[
        vendor_iterator_agent,
        negotiation_loop,
    ]
)
