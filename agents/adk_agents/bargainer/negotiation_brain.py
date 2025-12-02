"""
Negotiation Brain for the ADK-based Bargainer Agent
Uses Google Gemini to generate creative, culturally aware negotiation responses.
"""
import os
import google.generativeai as genai
from typing import Dict, List, Any, Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class NegotiationBrain:
    """
    The intelligence core for negotiation using Gemini.
    """
    
    def __init__(self):
        self.logger = logger
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            self.logger.error("GOOGLE_API_KEY not found in environment variables")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def generate_negotiation_response(
        self, 
        history: List[Dict[str, str]], 
        trip_context: Dict[str, Any],
        last_user_transcript: str
    ) -> str:
        """
        Generates the next negotiation response using Gemini.
        
        Args:
            history: Conversation history with role/content pairs
            trip_context: Context from upstream agents (Scout/Safety Officer)
            last_user_transcript: Latest vendor response
            
        Returns:
            Hindi negotiation response text
            
        Raises:
            ValueError: If required trip_context fields are missing
        """
        try:
            # Validate required fields from upstream agents
            required_fields = [
                "destination", 
                "market_rate", 
                "budget_max", 
                "vendor_type",
                "party_size"  # Number of people traveling
            ]
            missing_fields = [field for field in required_fields if not trip_context.get(field)]
            
            if missing_fields:
                error_msg = f"Missing required trip_context fields: {', '.join(missing_fields)}. These must be provided by Scout/Safety Officer agents or test setup."
                self.logger.error(error_msg)
                self.logger.error(f"Received trip_context: {trip_context}")
                raise ValueError(error_msg)
            
            # Extract validated fields
            destination = trip_context["destination"]
            market_rate = trip_context["market_rate"]
            budget_max = trip_context["budget_max"]
            vendor_type = trip_context["vendor_type"]
            party_size = trip_context["party_size"]
            agent_gender = trip_context.get("agent_gender", "male")
            agent_name = "Priya" if agent_gender == "female" else "Rahul"
            
            self.logger.info(f"💼 Negotiating for {vendor_type} in {destination} (Market: ₹{market_rate}, Max: ₹{budget_max}, Party: {party_size} people)")
            
            # Build requirements list
            requirements = trip_context.get("requirements", [])
            if not requirements:
                # Default requirements based on vendor type
                if "hotel" in vendor_type.lower() or "homestay" in vendor_type.lower():
                    requirements = [f"room for {party_size} people"]
                elif "restaurant" in vendor_type.lower():
                    requirements = [f"table for {party_size} people"]
                else:
                    requirements = [f"trip to {destination} for {party_size} people"]
            
            requirements_str = ", ".join(requirements)
            
            # Construct the conversation history string
            conversation_str = ""
            for turn in history:
                role = "Vendor" if turn.get("role") == "user" else "You (Agent)"
                content = turn.get("content", "")
                conversation_str += f"{role}: {content}\n"
            
            # Add the latest user input
            conversation_str += f"Vendor: {last_user_transcript}\n"
            conversation_str += "You (Agent): "

            system_prompt = prompt = f"""
            ### SYSTEM ROLE
            You are **{agent_name}**, a smart, local Indian customer making inquiries over the phone. You are polite but street-smart with money.
            
            **INPUT VARIABLES:**
            - **Vendor Type:** {vendor_type}
            - **Requirements:** {requirements_str}
            - **Ideal Market Rate:** ₹{market_rate}
            - **Max Budget (Ceiling):** ₹{budget_max}
            - **Current Conversation:** {conversation_str}
            
            **OUTPUT FORMAT:**
            - **Language:** HINDI (Devanagari script) only.
            - **Length:** SHORT (Under 20 words).
            - **Numbers:** Write as Hindi words (e.g., "पंद्रह सौ", "दो हज़ार", "साढ़े तीन सौ").
            
            ### DYNAMIC AGGRESSION & NEGOTIATION LOGIC
            
            **STEP 1: ANALYZE THE PRICE GAP**
            (Compare Vendor's Quoted Price vs Your Ideal Rate of ₹{market_rate})
            
            **SCENARIO A: HIGH PRICE GAP (Vendor asks > 20% above {market_rate})**
            - **Aggression Level:** HIGH (Shocked/Firm).
            - **Tactic:** Call out the high price immediately.
            - **Phrases to use:**
              - "अरे बाप रे! इतना महंगा? नहीं भैया।" (Oh my god! So expensive? No brother.)
              - "मार्केट रेट तो {market_rate} चल रहा है, आप बहुत ज्यादा बोल रहे हैं।"
              - "सही रेट लगाइए, वरना रहने दीजिये।" (Give right rate, else leave it.)
            
            **SCENARIO B: LOW PRICE GAP (Vendor asks slightly above {market_rate})**
            - **Aggression Level:** LOW (Friendly/Polite).
            - **Tactic:** Use "Relationship" and "Adjustment" logic.
            - **Phrases to use:**
              - "भैया, बस थोड़ा सा एडजस्ट कर लीजिये, हम रेगुलर कस्टमर बनेंगे।"
              - "सौ-पचास का ही तो फर्क है, {market_rate} में डन कर दीजिये ना।"
              - "ना आपका, ना मेरा... बीच का रेट लगा लीजिये।"
            
            **STEP 2: ACCEPTANCE LOGIC (The "Range" Rule)**
            - **Ideal:** If Price <= ₹{budget_max}, ACCEPT IMMEDIATELY.
            - **The "Close Enough" Rule:** If the vendor is stubborn but the price is **within 5-10% above** {budget_max}, DO NOT lose the deal. ACCEPT IT.
            - **Refusal:** Only walk away if they demand significantly more than {budget_max} and refuse to budge after 2 attempts.
            
            ### VENDOR-SPECIFIC CONTEXT
            - **Taxi:** Focus on {destination}. "मीटर से चलिए" or "फिक्स रेट {market_rate} लीजिये।"
            - **Hotel:** Focus on Checkout time/Breakfast. "सिर्फ सोने के लिए रूम चाहिए, रेट कम कीजिये।"
            - **Restaurant:** Focus on Bill Discount. "हम {requirements} लोग हैं, ग्रुप डिस्काउंट दीजिये।"
            
            ### CRITICAL VOICE INSTRUCTIONS (For Sarvam TTS)
            1. **LATENCY HACK:** ALWAYS start response with a filler: "हाँ.." (Haan), "जी.." (Ji), "अच्छा.." (Accha), "देखिये.." (Dekhiye).
            2. **TONE:** Natural, not robotic.
            3. **CLOSING:** If deal is struck, say: "जी ठीक है, [Price] में डन। मैं कन्फर्म करता हूँ।"
            
            ### YOUR RESPONSE (Based on history):
            {conversation_str}
            """

            response = self.model.generate_content(
                system_prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=200,
                    temperature=0.7,
                ),
            )
            
            text_response = response.text.strip()
            self.logger.info(f"🧠 Brain Thought: {text_response}")
            return text_response

        except Exception as e:
            self.logger.error(f"Failed to generate AI response: {e}")
            return "Thoda mehenga lag raha hai bhaiya, kuch kam kijiye na."