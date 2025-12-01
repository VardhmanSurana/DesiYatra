"""
Custom Planners for DesiYatra Agent System

These planners provide domain-specific reasoning and decision-making logic
to replace the generic BuiltInPlanner.
"""
from typing import List, Dict, Any, Optional
from google.adk.planners import Planner
from google.genai import types
from loguru import logger


class NegotiationPlanner(Planner):
    """
    Custom planner for negotiation agent.
    
    Makes strategic decisions during price negotiation based on:
    - Vendor's quoted price vs market rate
    - Negotiation history (rounds, previous offers)
    - Budget constraints
    - Vendor profile (stubborn vs flexible)
    """
    
    def __init__(self, max_rounds: int = 6):
        self.max_rounds = max_rounds
        
    async def plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan the next negotiation move.
        
        Returns a plan with:
        - action: "counter", "accept", or "end_call"
        - reasoning: Why this action was chosen
        - message: What to say to vendor
        """
        # Extract context
        current_quote = context.get("current_quote")
        market_rate = context.get("market_rate")
        budget_max = context.get("budget_max")
        round_num = context.get("round", 0)
        vendor_profile = context.get("vendor_profile", {})
        
        logger.info(f"🧠 Planning negotiation move (Round {round_num})")
        logger.info(f"   Quote: ₹{current_quote}, Market: ₹{market_rate}, Budget: ₹{budget_max}")
        
        # Decision logic
        if not current_quote:
            return {
                "action": "ask_price",
                "reasoning": "No quote received yet, need to ask for initial price",
                "message": "भैया, रेट क्या लगेगा?"
            }
        
        # Accept if within budget
        if current_quote <= budget_max:
            return {
                "action": "accept",
                "reasoning": f"Quote ₹{current_quote} is within budget ₹{budget_max}",
                "message": f"ठीक है भैया, ₹{current_quote} में कन्फर्म करते हैं। डील पक्की।"
            }
        
        # End if max rounds reached
        if round_num >= self.max_rounds:
            return {
                "action": "end_call",
                "reasoning": f"Max rounds ({self.max_rounds}) reached without agreement",
                "message": "नहीं भैया, बजट के बाहर है। धन्यवाद।"
            }
        
        # Counter-offer strategy
        vendor_style = vendor_profile.get("negotiation_style", "unknown")
        
        if vendor_style == "stubborn":
            # Small decrements for stubborn vendors
            counter_offer = current_quote * 0.95
            reasoning = "Vendor is stubborn, making small 5% reduction request"
        elif vendor_style == "flexible":
            # Larger decrements for flexible vendors
            counter_offer = current_quote * 0.90
            reasoning = "Vendor is flexible, trying 10% reduction"
        else:
            # Default: aim for market rate
            counter_offer = market_rate
            reasoning = f"Aiming for market rate of ₹{market_rate}"
        
        # Don't go below market rate
        counter_offer = max(counter_offer, market_rate)
        
        return {
            "action": "counter",
            "reasoning": reasoning,
            "offer": counter_offer,
            "message": f"भैया, ₹{counter_offer:.0f} में हो जाएगा? मार्केट रेट भी यही चल रहा है।"
        }


class VendorSelectionPlanner(Planner):
    """
    Custom planner for selecting which vendors to call.
    
    Prioritizes based on:
    - Trust score / safety rating
    - Distance from user's location
    - Reviews and ratings
    - Price competitiveness
    """
    
    async def plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan vendor selection strategy.
        """
        vendors = context.get("safe_vendors", [])
        budget_max = context.get("budget_max")
        
        if not vendors:
            return {
                "action": "no_vendors",
                "reasoning": "No safe vendors available",
                "vendors_to_call": []
            }
        
        logger.info(f"🎯 Planning vendor selection from {len(vendors)} candidates")
        
        # Score each vendor
        scored_vendors = []
        for vendor in vendors:
            score = 0
            
            # Trust score (0-1) × 40 points
            trust = vendor.get("trust_score", 0.5)
            score += trust * 40
            
            # Rating (0-5) × 20 points
            rating = vendor.get("rating", 3.0)
            score += (rating / 5.0) * 20
            
            # Source preference (20 points)
            source = vendor.get("source", "")
            if "google_maps" in source:
                score += 20
            elif "justdial" in source:
                score += 15
            else:
                score += 10
            
            # Recency (if available) × 20 points
            # Newer listings preferred
            
            scored_vendors.append({
                "vendor": vendor,
                "score": score
            })
        
        # Sort by score descending
        scored_vendors.sort(key=lambda x: x["score"], reverse=True)
        
        # Select top 3-5 vendors
        top_vendors = [sv["vendor"] for sv in scored_vendors[:5]]
        
        logger.info(f"✅ Selected {len(top_vendors)} vendors to call")
        for i, sv in enumerate(scored_vendors[:5], 1):
            logger.info(f"   {i}. {sv['vendor']['name']} (score: {sv['score']:.1f})")
        
        return {
            "action": "call_vendors",
            "reasoning": f"Selected top {len(top_vendors)} vendors by trust, rating, and source quality",
            "vendors_to_call": top_vendors,
            "call_order": [v["phone"] for v in top_vendors]
        }


class SafetyDecisionPlanner(Planner):
    """
    Custom planner for safety vetting decisions.
    
    Makes nuanced safety decisions beyond simple pass/fail:
    - GREEN: Safe to call
    - YELLOW: Caution - call but monitor extra
    - RED: Block - do not call
    """
    
    async def plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan safety vetting decision for a vendor.
        """
        vendor = context.get("vendor", {})
        fraud_signals = context.get("fraud_signals", [])
        vendor_history = context.get("vendor_history", {})
        
        logger.info(f"🛡️ Safety vetting: {vendor.get('name')}")
        
        risk_score = 0
        reasons = []
        
        # Check fraud signals
        high_risk_signals = ["known_scammer", "fake_listing", "multiple_reports"]
        medium_risk_signals = ["new_vendor", "no_reviews", "suspicious_pricing"]
        
        for signal in fraud_signals:
            if signal in high_risk_signals:
                risk_score += 50
                reasons.append(f"High risk: {signal}")
            elif signal in medium_risk_signals:
                risk_score += 20
                reasons.append(f"Medium risk: {signal}")
        
        # Check history
        past_issues = vendor_history.get("fraud_reports", 0)
        if past_issues > 0:
            risk_score += past_issues * 30
            reasons.append(f"{past_issues} past fraud reports")
        
        # Trust score inverse
        trust_score = vendor.get("trust_score", 0.5)
        if trust_score < 0.3:
            risk_score += 30
            reasons.append(f"Low trust score: {trust_score}")
        
        # Make decision
        if risk_score >= 70:
            decision = "RED"
            action = "block"
        elif risk_score >= 30:
            decision = "YELLOW"
            action = "caution"
        else:
            decision = "GREEN"
            action = "approve"
        
        logger.info(f"   Decision: {decision} (risk: {risk_score})")
        
        return {
            "action": action,
            "decision": decision,
            "risk_score": risk_score,
            "reasons": reasons,
            "monitoring_required": decision == "YELLOW"
        }


# Factory function to get appropriate planner
def get_planner(agent_type: str, **kwargs) -> Optional[Planner]:
    """
    Get custom planner for specific agent type.
    
    Args:
        agent_type: "negotiation", "vendor_selection", or "safety"
        **kwargs: Additional planner-specific config
        
    Returns:
        Planner instance or None for default behavior
    """
    planners = {
        "negotiation": NegotiationPlanner,
        "vendor_selection": VendorSelectionPlanner,
        "safety": SafetyDecisionPlanner,
    }
    
    planner_class = planners.get(agent_type)
    if planner_class:
        return planner_class(**kwargs)
    else:
        logger.warning(f"No custom planner for '{agent_type}', using default")
        return None
