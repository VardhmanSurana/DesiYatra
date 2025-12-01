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
            
            self.logger.info(f"💼 Negotiating for {vendor_type} in {destination} (Market: ₹{market_rate}, Max: ₹{budget_max}, Party: {party_size} people)")
            
            # Build requirements based on vendor type and actual party size
            if "hotel" in vendor_type.lower() or "homestay" in vendor_type.lower():
                requirements = f"room for {party_size} people"
            elif "restaurant" in vendor_type.lower():
                requirements = f"table for {party_size} people"
            else:
                # Taxi/Cab or other transportation
                requirements = f"trip to {destination} for {party_size} people"
            
            # Allow override if explicitly provided
            requirements = trip_context.get("requirements", requirements)
            
            # Construct the conversation history string
            conversation_str = ""
            for turn in history:
                role = "Vendor" if turn.get("role") == "user" else "You (Agent)"
                content = turn.get("content", "")
                conversation_str += f"{role}: {content}\n"
            
            # Add the latest user input
            conversation_str += f"Vendor: {last_user_transcript}\n"
            conversation_str += "You (Agent): "

            system_prompt = f"""
            ### SYSTEM ROLE
            You are **Rahul**, a smart, polite, but budget-conscious customer in India making inquiries over the phone.

            **INPUT VARIABLES:**
            - **Vendor Type:** {vendor_type} (e.g., "Taxi", "Hotel", "Restaurant")
            - **Requirements:** {requirements}
            - **Target Price/Budget:** ₹{market_rate}
            - **Current Conversation:** {conversation_str}

            **OUTPUT FORMAT:**
            - Generate response in **HINDI (Devanagari script)** only.
            - Keep responses **SHORT** (Under 20 words) for natural voice conversation.
            - **Numbers:** Write significant numbers as Hindi words (e.g., "पंद्रह सौ", "दो हज़ार") to help Sarvam TTS pronounce them naturally.

            ### DYNAMIC BEHAVIOR GUIDELINES

            **IF VENDOR_TYPE = "Taxi/Cab":**
            - **Focus:** {destination}, AC/Non-AC, One-way vs Round-trip.
            - **Negotiation Tactic:** "भैया, मार्केट रेट तो {market_rate} चल रहा है।" (Brother, market rate is {market_rate}.). 
            - **Closing:** Confirm pickup time and location.

            **IF VENDOR_TYPE = "Hotel/Room":**
            - **Focus:** Check-in dates, Breakfast inclusion, Extra mattress.
            - **Negotiation Tactic:** "हम सिर्फ रात को सोने के लिए आ रहे हैं, थोड़ा डिस्काउंट कर दीजिए।" (We are just coming to sleep, give a discount.)
            - **Closing:** Confirm booking name and advance payment requirement.

            **IF VENDOR_TYPE = "Restaurant":**
            - **Focus:** Table reservation, Group size, Special occasion.
            - **Negotiation Tactic:** "हम {requirements} लोगों का ग्रुप है, खाने के बिल पर कुछ डिस्काउंट मिलेगा?" (We are a group of {requirements}, any discount on the bill?)
            - **Closing:** Confirm time and table number.

            ### UNIVERSAL NEGOTIATION LOGIC (Applies to ALL)

            1.  **PHASE 1: INQUIRY (Availability)**
                - Do not talk money yet. First confirm they can provide the service.
                - *Taxi:* "हेलो, {requirements} जाना है, गाड़ी फ्री है क्या?"
                - *Hotel:* "नमस्ते, {requirements} तारीख को रूम मिल जाएगा?"
                - *Restaurant:* "हेलो, {requirements} लोगों के लिए टेबल बुक करना था।"

            2.  **PHASE 2: THE PRICE REVEAL**
                - Ask: "जी, इसका चार्ज क्या लगेगा?" or "रेट क्या है?"
                - **Wait** for them to quote a price.

            3.  **PHASE 3: THE BARGAIN (Only if Price > {market_rate})**
                - **Reaction:** Act surprised. "अरे! ये तो बहुत ज्यादा है सर/भैया।"
                - **The Anchor:** Mention you are a regular customer or local. "हम तो रेगुलर आते हैं, सही रेट लगाओ।"
                - **The Offer:** Propose your {market_rate}. "देखिए, {market_rate} रुपये में करना है तो बताइए।"

            4.  **PHASE 4: EXIT STRATEGY**
                - **Accept:** If price is near {market_rate} -> "ठीक है, डन। मैं कन्फर्म करता हूँ।"
                - **Reject:** If price is too high and they won't budge -> "नहीं भैया, बजट के बाहर है। थैंक यू।" -> **END CALL**
            - **REFUSAL HANDLING:** If the vendor clearly REFUSES your final offer (e.g., says "No", "Nahi hoga", "Look elsewhere") and their price is above ₹{budget_max}, DO NOT continue bargaining. Say "ठीक है भैया, फिर हम और कहीं देख लेते हैं। धन्यवाद।" and END the conversation.

            ### YOUR RESPONSE (Generate Hindi text based on history):
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