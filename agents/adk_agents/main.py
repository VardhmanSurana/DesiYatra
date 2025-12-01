"""
Main Entry Point for DesiYatra ADK Agent System

This script demonstrates how to configure and run the complete, refactored
multi-agent orchestration pipeline using the Google ADK framework.
"""
import asyncio
import os
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the main orchestrator agent
from agents.adk_agents.orchestrator import munshi_orchestrator_agent

# Import ADK components for running and managing the agent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService  # Persistent session storage
from google.genai import types

# Import strongly-typed models
from agents.adk_agents.shared.types import SessionState, TripContext

async def run_orchestration():
    """
    Sets up the ADK runner and executes the Munshi orchestrator agent pipeline.
    """
    logger.info("🚀 Starting DesiYatra Agent Orchestration...")

    # 1. Define the trip request using strongly-typed TripContext
    trip_request = TripContext(
        trip_id="trip-12345",
        user_id="user-abcde",
        destination="Manali",
        category="taxi",
        query="taxi service in Manali",
        budget_max=3000.0,
        party_size=4,
        # market_rate will be calculated by Scout agent ✅
    )
    logger.info(f"📋 Trip Request: {trip_request}")

    # 2. Set up services with persistent SQLite database
    db_path = "desiyatra_sessions.db"
    # Note: Requires 'aiosqlite' package installed
    session_service = DatabaseSessionService(
        db_url=f"sqlite+aiosqlite:///{db_path}",
    )
    logger.info(f"💾 Using persistent session storage: {db_path}")
    
    runner = Runner(
        agent=munshi_orchestrator_agent,
        app_name="agents",
        session_service=session_service,
    )

    # 3. Create a session with strongly-typed state
    initial_state = SessionState(trip_request=trip_request)
    session = await session_service.create_session(
        app_name="agents",
        user_id=trip_request.user_id,
        session_id=trip_request.trip_id,
        state=initial_state.model_dump(),  # Convert to dict for storage
    )
    logger.info(f"✅ Session created: {session.id}")

    # 4. Define the initial message to kick off the agent.
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=f"Start planning for a trip to {trip_request.destination}.")]
    )

    # 5. Run the agent pipeline
    logger.info("🏃 Running the agent pipeline...")
    event_stream = runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=user_message,
    )
    async for event in event_stream:
        if event.is_final_response():
            logger.info(f"Final response event received: {event}")

    # 6. Retrieve and display the final results from the session state
    final_session_raw = await session_service.get_session(
        app_name="agents",
        user_id=session.user_id,
        session_id=session.id,
    )
    
    # Parse the final state into our strongly-typed model
    final_state = SessionState(**final_session_raw.state)

    logger.info("🏁 Orchestration Complete!")
    logger.info("-" * 40)

    # Type-safe access to state data
    found_vendors_count = len(final_state.found_vendors.vendors) if final_state.found_vendors else 0
    safe_vendors_count = len(final_state.safe_vendors.vendors) if final_state.safe_vendors else 0
    final_deals_count = len(final_state.final_deals.deals) if final_state.final_deals else 0

    logger.info(f"📊 scout_agent found {found_vendors_count} potential vendors.")
    logger.info(f"✅ safety_officer_agent approved {safe_vendors_count} vendors.")
    logger.success(f"🤝 bargainer_agent secured {final_deals_count} deals!")

    if final_state.final_deals and final_state.final_deals.deals:
        logger.info("Best Deals Found:")
        for deal in final_state.final_deals.deals:
            logger.info(f"  - Vendor: {deal.vendor_name}, Price: ₹{deal.negotiated_price}")

    logger.info("-" * 40)
    logger.info(f"Full session state: {final_session_raw.state}")


if __name__ == "__main__":
    # To run this script, you need to have the Google GenAI SDK configured.
    # Make sure you have the GOOGLE_API_KEY environment variable set in .env file.
    try:
        import google.generativeai as genai
        if not os.getenv("GOOGLE_API_KEY"):
            logger.error("ERROR: The GOOGLE_API_KEY environment variable is not set.")
        else:
            asyncio.run(run_orchestration())
    except ImportError:
        logger.error("Please install the required libraries: pip install google-generativeai")
