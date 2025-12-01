"""
Tools for the Bargainer Agent
"""
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger

from agents.adk_agents.bargainer.negotiation_brain import NegotiationBrain, NegotiationContext
from agents.adk_agents.bargainer.voice_pipeline import VoicePipeline

async def _negotiate_one_vendor(vendor: Dict[str, Any], trip_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    (Private) Simulates a full negotiation voice call with a single vendor.
    """
    session_id = str(uuid.uuid4())
    logger.info(f"📞 [_BARGAINER_HELPER] Initiating call to {vendor.get('name')} ({session_id})")

    # In a real async implementation, VoicePipeline would have async methods.
    # For now, we treat them as blocking calls that happen fast in simulation.
    voice_pipeline = VoicePipeline(session_id)
    brain = NegotiationBrain()

    try:
        # Simulate network delay for realism
        await asyncio.sleep(0.5)
        
        voice_pipeline.speak(f"Namaste, kya meri baat {vendor.get('name')} se ho rahi hai?")
        vendor_response = voice_pipeline.listen()

        voice_pipeline.speak("Humein Manali ke liye taxi chahiye. Aapka kya rate hai?")
        vendor_response = voice_pipeline.listen()

        try:
            current_quote = float(vendor_response.split("is ")[-1].replace(".", ""))
        except (ValueError, IndexError):
            current_quote = 4000.0

        for round_num in range(1, 6):
            # Simulate thinking/processing time
            await asyncio.sleep(0.2)
            
            context = NegotiationContext(
                round_number=round_num,
                current_quote=current_quote,
                market_rate=trip_context.get("market_rate", 2800.0),
                budget_max=trip_context.get("budget_max", 3000.0),
                last_vendor_message=vendor_response
            )
            move = brain.determine_next_move(context)

            if move["action"] == "accept":
                script = brain.get_script_for_tactic(move["tactic"], move["offer"])
                voice_pipeline.speak(script)
                logger.success(f"✅ Deal ACCEPTED with {vendor.get('name')} at ₹{move['offer']}")
                return {
                    "vendor_name": vendor.get("name"),
                    "phone": vendor.get("phone"),
                    "service_type": vendor.get("category"),
                    "negotiated_price": move["offer"],
                    "status": "DEAL_SUCCESS",
                }
            else:
                script = brain.get_script_for_tactic(move["tactic"], move["offer"])
                voice_pipeline.speak(script)
                vendor_response = voice_pipeline.listen()
                current_quote *= 0.95
        
        logger.warning(f"Negotiation with {vendor.get('name')} reached a deadlock.")
        return None

    except Exception as e:
        logger.error(f"Call simulation with {vendor.get('name')} failed: {e}")
        return None

async def negotiate_all_vendors(
    vendors: List[Dict[str, Any]],
    trip_context: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Orchestrates negotiations with a list of vendors and returns the final list of deals.
    Executes negotiations in parallel with a concurrency limit.
    """
    logger.info(f"📞 [BARGAINER_TOOL] Starting mass negotiation with {len(vendors)} vendors.")
    
    # Limit concurrent calls to 3 to respect API rate limits and resource usage
    sem = asyncio.Semaphore(3)

    async def sem_task(vendor):
        async with sem:
            return await _negotiate_one_vendor(vendor, trip_context)

    tasks = [sem_task(vendor) for vendor in vendors]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_deals = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"A negotiation task failed with error: {result}")
        elif result:
            successful_deals.append(result)
            
    final_output = {"deals": successful_deals}
    
    response_message = f"Bargaining complete. Found {len(successful_deals)} deals."
    logger.info(response_message)
    return final_output