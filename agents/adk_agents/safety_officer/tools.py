"""
Tools for the Safety Officer Agent.
"""
from typing import Dict, Any, List
from loguru import logger
import re
import random
import json
from agents.adk_agents.shared.types import VettedVendorsList

def _get_vendor_safety_report(vendor: Dict[str, Any]) -> Dict[str, Any]:
    """
    (Private) Simulates a data-driven safety check on a single vendor by
    querying a BigQuery data warehouse.
    """
    vendor_phone = vendor.get("phone")
    logger.info(f"  Getting safety report for {vendor.get('name')} ({vendor_phone}) from BigQuery.")

    # --- BigQuery Simulation ---
    history = {
        "total_calls": random.randint(5, 50),
        "successful_deals": random.randint(4, 45),
        "fraud_flags": random.choices([0, 1, 2], weights=[90, 8, 2], k=1)[0],
    }
    logger.info(f"  [SIMULATED BQ] History for {vendor_phone}: {history}")
    # --- End Simulation ---

    safety_score = 0.8
    if history["total_calls"] > 0:
        success_rate = history["successful_deals"] / history["total_calls"]
        if success_rate < 0.5:
            safety_score -= 0.3
        if success_rate > 0.8:
            safety_score += 0.2
    
    safety_score -= history["fraud_flags"] * 0.4

    recommendation = "BLOCK"
    if safety_score >= 0.7:
        recommendation = "SAFE"
    elif safety_score >= 0.4:
        recommendation = "CAUTION"

    vendor["recommendation"] = recommendation
    vendor["safety_score"] = round(safety_score, 2)
    vendor["history"] = history
    return vendor

def filter_safe_vendors(
    found_vendors: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Vets a list of vendors and returns the filtered list of safe ones.
    """
    logger.info(f"🛡️ [SAFETY_TOOL] Vetting {len(found_vendors)} vendors...")
    
    safe_vendors = []
    for vendor in found_vendors:
        vetted_vendor = _get_vendor_safety_report(vendor)
        if vetted_vendor.get("recommendation") == "SAFE":
            safe_vendors.append(vetted_vendor)

    response_message = f"Vetting complete. Found {len(safe_vendors)} safe vendors."
    logger.info(response_message)
    return safe_vendors


def analyze_transcript_chunk(transcript_chunk: str) -> Dict[str, Any]:
    """
    Analyzes a chunk of a call transcript for fraud indicators.
    """
    logger.info(f"Analyzing transcript chunk: '{transcript_chunk}'")
    
    otp_triggers = ["otp", "code bhejo", "verification code"]
    if any(re.search(trigger, transcript_chunk, re.IGNORECASE) for trigger in otp_triggers):
        return {
            "fraud_detected": True,
            "severity": "CRITICAL",
            "flags": ["otp_request"],
            "suggested_response": "Bhaiya OTP nahi de sakte.",
            "should_terminate": True,
        }
        
    return {
        "fraud_detected": False,
        "severity": "low",
        "flags": [],
        "suggested_response": None,
        "should_terminate": False,
    }

def parse_vetted_vendors_output(llm_output: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses the LLM's raw output to extract and validate the JSON containing vetted vendors.
    """
    logger.info("Attempting to parse LLM output for vetted vendors...")
    try:
        match = re.search(r"```json\n({.*?})\n```", llm_output, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = llm_output.strip()

        parsed_data = json.loads(json_str)
        validated_data = VettedVendorsList(**parsed_data)
        logger.info("Successfully parsed and validated VettedVendorsList.")
        return validated_data.model_dump()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e} in LLM output: {llm_output}")
        raise ValueError(f"Invalid JSON output from LLM: {llm_output}") from e
    except Exception as e:
        logger.error(f"Error parsing VettedVendorsList output: {e} in LLM output: {llm_output}")
        raise ValueError(f"Failed to parse VettedVendorsList output: {llm_output}") from e