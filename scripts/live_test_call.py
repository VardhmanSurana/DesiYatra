import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.adk_agents.bargainer.atomic_tools import initiate_call

# Load env vars
load_dotenv()

def main():
    print("\n📞 DesiYatra Live Streaming Agent Test 📞\n")
    
    # Check for command-line arguments
    if len(sys.argv) >= 3:
        user_phone = sys.argv[1]
        choice = sys.argv[2]
        print(f"Using args: {user_phone}, scenario {choice}")
    else:
        print("This script will trigger a REAL call with streaming voice.")
        print("You will act as the Vendor. The Agent will negotiate with you.\n")
        
        # Get User Input
        user_phone = input("Enter your phone number (e.g., +919876543210): ").strip()
        if not user_phone:
            print("❌ Phone number is required!")
            return

        print("\nChoose your role:")
        print("1. Taxi Driver (Manali Trip)")
        print("2. Hotel Manager (Room Booking)")
        print("3. Restaurant Manager (Dinner Table)")
        choice = input("Selection [1]: ").strip() or "1"

    # 2. Setup Context
    scenarios = {
        "1": {
            "vendor_type": "Taxi",
            "destination": "Manali",
            "market_rate": 2500.0,
            "budget_max": 3000.0,
            "requirements": ["one-way trip", "AC vehicle"],
            "vendor_name": "Raju Taxi Service",
            "party_size": 2
        },
        "2": {
            "vendor_type": "Hotel",
            "destination": "Manali",
            "market_rate": 1500.0,
            "budget_max": 2000.0,
            "requirements": ["2 days stay", "deluxe room", "breakfast included"],
            "vendor_name": "Hotel Mountain View",
            "party_size": 2
        },
        "3": {
            "vendor_type": "Restaurant",
            "destination": "Manali",
            "market_rate": 800.0,
            "budget_max": 1000.0,
            "requirements": ["dinner table", "AC seating", "reserved for 8 PM"],
            "vendor_name": "Sher-e-Punjab Dhaba",
            "party_size": 4
        }
    }

    if choice not in scenarios:
        print("❌ Invalid choice.")
        return

    scenario = scenarios[choice]
    
    print(f"\n🚀 Initiating streaming call as '{scenario['vendor_name']}' ({scenario['vendor_type']})...")
    print(f"💰 Agent Budget: ₹{scenario['budget_max']} | Market Rate: ₹{scenario['market_rate']}")
    print(f"👥 Party Size: {scenario['party_size']} people")
    
    # 3. Prepare Data
    vendor = {
        "name": scenario["vendor_name"],
        "phone": user_phone,
        "category": scenario["vendor_type"].lower(),
        "gender": "female"  # For TTS voice
    }
    
    trip_context = {
        "destination": scenario["destination"],
        "market_rate": scenario["market_rate"],
        "budget_max": scenario["budget_max"],
        "vendor_type": scenario["vendor_type"],
        "requirements": scenario["requirements"],
        "party_size": scenario["party_size"]
    }

    # 4. Trigger Call with Streaming
    try:
        print("\n⏳ Initiating call with Media Streams...")
        result = initiate_call(vendor, trip_context, use_real_twilio=True)
        
        if "error" in result:
            logger.error(f"❌ Call failed: {result['error']}")
            print("\nTroubleshooting:")
            print("1. Check WEBHOOK_BASE_URL in .env matches ngrok URL")
            print("2. Ensure ngrok is running: ngrok http 8000")
            print("3. Verify TWILIO_* credentials are correct")
            print("4. Check server is running: fastapi dev agents/main.py")
        else:
            logger.success(f"✅ Call initiated! SID: {result.get('twilio_call_sid')}")
            print("\n📲 Check your phone! The agent should be calling shortly.")
            print("\n💡 Tips:")
            print("  - Speak naturally in Hindi/Hinglish")
            print("  - Quote a high price first (e.g., ₹4000)")
            print("  - Negotiate down gradually")
            print("  - Watch server logs for real-time transcripts")
            print("\n🔍 Monitor logs:")
            print("  - 🗣️ Agent: = What agent says")
            print("  - 👤 Vendor: = What you say (transcribed)")
            print("  - 🎤 = Voice activity detected")
            
    except Exception as e:
        logger.error(f"❌ Script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
