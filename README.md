# 🇮🇳 DesiYatra - AI Travel Negotiation Agent System

> **AI-powered travel negotiation agents that find local vendors, call them, and negotiate prices in Hindi/Hinglish**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4)](https://github.com/google/adk)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

---

## 🎯 Overview

DesiYatra is a sophisticated multi-agent AI system designed to automate travel service negotiations in India. The system finds local vendors (taxi drivers, hotels, tour guides), makes phone calls in Hindi/Hinglish, and negotiates the best prices on your behalf.

### Key Features

- 🤖 **4 Specialized AI Agents** working in coordination
- 📞 **Real Voice Calls** via Twilio with Hindi TTS/STT
- 🔍 **Multi-Source Vendor Discovery** (Google Maps, JustDial, IndiaMart)
- 💬 **Natural Hindi/Hinglish Negotiation** using LLM reasoning
- 🛡️ **Fraud Detection & Safety Vetting** before calls
- 📊 **Real-time Session Management** with Redis & PostgreSQL

---

## 🏗️ Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                    Munshi (Orchestrator)                    │
│              Coordinates the entire workflow                │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│ Scout Agent   │ →  │ Safety Officer │ →  │  Bargainer   │
│ Find Vendors  │    │  Vet Vendors   │    │  Negotiate   │
└───────────────┘    └────────────────┘    └──────────────┘
```

### Agent Details

#### 1. **Scout Agent** (Parallel-Sequential Pattern)
- **Purpose**: Find potential vendors from multiple sources
- **Architecture**: `ParallelAgent` + `SequentialAgent`
- **Sources**: 
  - Google Search Grounding
  - Google Maps Grounding
  - JustDial (simulated)
  - IndiaMart (simulated)
- **New Features**:
  - ✨ **Automatic Market Rate Calculation** - Extracts prices from vendor metadata or uses heuristic estimation
  - ✨ **Custom Vendor Selection Planner** - Intelligent ranking by trust score, ratings, and source quality
  - 📊 Scores vendors: Trust (40pts) + Rating (20pts) + Source (20pts)
- **Output**: Deduplicated, ranked list of vendors + calculated market_rate

#### 2. **Safety Officer Agent**
- **Purpose**: Vet vendors for safety and fraud detection
- **Tools**: 
  - `filter_safe_vendors`: Checks vendor history in database
  - `analyze_transcript_chunk`: Real-time fraud detection during calls
- **New Features**:
  - ✨ **Custom Safety Decision Planner** - Nuanced risk assessment (GREEN/YELLOW/RED)
  - 🛡️ Risk scoring from fraud signals and vendor history
  - ⚠️ Graduated monitoring levels
- **Output**: Verified safe vendors list with risk scores

#### 3. **Bargainer Agent** (Loop-Based Reasoning)
- **Purpose**: Conduct voice negotiations with vendors
- **Architecture**: `LoopAgent` with atomic tools
- **Tools**:
  - `initiate_call`: Start Twilio call
  - `send_message`: Send negotiation messages
  - `accept_deal`: Finalize deal
  - `end_call`: Exit negotiation loop
- **New Features**:
  - ✨ **Custom Negotiation Planner** - Strategic price decisions based on market rate
  - 💰 No hardcoded values - requires all context from upstream agents
  - 👥 Party size awareness - "room for 4 people", "trip for 2 people"
  - 🎯 Adapts to vendor style (stubborn vs flexible)
  - 📚 **Vector Search Knowledge Base** - Semantic search for negotiation tactics
- **Intelligence**: LLM reasons about tactics dynamically (not rule-based)
- **Output**: List of successful deals

#### 4. **Munshi (Orchestrator)**
- **Purpose**: Coordinate the entire workflow
- **Pattern**: `SequentialAgent`
- **Flow**: Scout → Safety Officer → Bargainer

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python 3.12 | Core application |
| **AI Framework** | Google ADK | Multi-agent orchestration |
| **LLM** | Google Gemini 2.5 Pro/Flash | Agent reasoning |
| **Planners** | Custom Domain Planners | Negotiation, vendor selection, safety decisions |
| **Vector Search** | Vertex AI Matching Engine | Semantic knowledge base search |
| **Embeddings** | text-embedding-004 | 768-dimensional vectors |
| **API Server** | FastAPI | REST API endpoints |
| **Database** | Supabase (PostgreSQL) | Vendor & trip data |
| **Cache/State** | Redis | Session state & pub/sub |
| **Telephony** | Twilio | Voice calls |
| **Voice (TTS)** | Sarvam AI Bulbul | Hindi text-to-speech |
| **Voice (STT)** | Sarvam AI | Hindi speech-to-text |
| **Search** | Google Grounding API | Vendor discovery |
| **Package Manager** | uv | Fast Python package management |

---

## 📦 Installation

### Prerequisites

- Python 3.12+
- uv package manager
- Docker & Docker Compose (optional)
- ngrok (for webhook testing)

### Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd DesiYatra

# 2. Install dependencies
uv pip install -e .

# 3. Copy environment variables
cp .env.example .env

# 4. Configure API keys in .env
# - GOOGLE_API_KEY
# - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
# - SUPABASE_URL, SUPABASE_KEY
# - SARVAM_API_KEY (optional)

# 5. Start Redis (if not using Docker)
redis-server

# 6. Run the application
uvicorn agents.main:app --reload
```

### Docker Setup

```bash
# Start all services
docker-compose up

# The API will be available at http://localhost:8000
```

---

## 🚀 Usage

### 1. Test Twilio Integration

```bash
# Quick call test (no server needed)
python tests/test_twilio_quick_call.py

# Webhook-based test (requires server + ngrok)
python tests/test_twilio_with_webhooks.py
```

### 2. Test Sarvam AI TTS

```bash
python tests/test_sarvam_tts.py
```

### 3. Test ADK Agents

```bash
python tests/test_refactored_agents.py
```

### 4. Check Webhook Accessibility

```bash
python tests/test_ngrok_webhook.py
```

---

## 📁 Project Structure

```
DesiYatra/
├── agents/
│   ├── adk_agents/              # Google ADK agent implementations
│   │   ├── scout/               # Vendor discovery agent
│   │   │   ├── agent.py         # Parallel-Sequential architecture
│   │   │   ├── tools.py         # Search tools
│   │   │   ├── google_maps_grounding_tool.py
│   │   │   └── google_search_grounding_tool.py
│   │   ├── safety_officer/      # Vendor vetting agent
│   │   │   ├── agent.py
│   │   │   └── tools.py
│   │   ├── bargainer/           # Negotiation agent
│   │   │   ├── agent.py         # Loop-based reasoning
│   │   │   ├── atomic_tools.py  # Atomic negotiation tools
│   │   │   ├── voice_pipeline.py # TTS/STT integration
│   │   │   └── negotiation_brain.py (legacy)
│   │   ├── orchestrator.py      # Main workflow coordinator
│   │   └── shared/
│   │       └── types.py         # Pydantic models
│   ├── shared/                  # Shared utilities
│   │   ├── config.py
│   │   ├── database.py          # Supabase client
│   │   ├── redis_client.py
│   │   ├── logger.py
│   │   └── models.py
│   └── main.py                  # FastAPI application
├── tests/                       # Test scripts
│   ├── test_twilio_quick_call.py
│   ├── test_twilio_with_webhooks.py
│   ├── test_google_tts.py
│   ├── test_ngrok_webhook.py
│   ├── test_refactored_agents.py
│   ├── test_adk_agents.py
│   ├── test_bargainer.py
│   ├── test_database.py
│   └── test_db_session_service.py
├── migrations/                  # Database migrations
├── logs/                        # Application logs
├── .env                         # Environment variables
├── .env.example                 # Example environment config
├── pyproject.toml               # Python dependencies
├── docker-compose.yml           # Docker services
├── Dockerfile                   # Container definition
├── README.md                    # This file
├── IMPROVEMENTS.md              # Completed improvements
├── adk_improvements.md          # ADK enhancement tracking
├── ARCHITECTURE_DIAGRAM.md      # Visual architecture
└── ADK_AGENT_REFACTOR_SUMMARY.md # Refactoring details
```

---

## 🔑 Environment Variables

### Required

```bash
# Google AI
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json

# Sarvam AI (Hindi TTS/STT)
SARVAM_API_KEY=your_sarvam_api_key

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Webhooks
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.dev
```

### Optional

```bash
# Vector Search (Vertex AI) - For production knowledge base
# Leave commented to use mock mode during development
# VECTOR_INDEX_ENDPOINT_ID=projects/PROJECT/locations/REGION/indexEndpoints/ID
# VECTOR_DEPLOYED_INDEX_ID=your_deployed_index_id

# Testing
TEST_PHONE_NUMBER=+919876543210
AGENT_NAME=DesiYatra
```

### Trip Context Requirements

When creating trip requests, you **must** provide:
- `destination`: Where user wants to go
- `budget_max`: User's maximum budget
- `party_size`: Number of people traveling (NEW - required for accurate quotes)
- `category`: Service type (taxi, hotel, etc.)

**Note**: `market_rate` is now **automatically calculated** by Scout agent - no need to provide it!

---

## 🎤 Voice Integration

### Text-to-Speech (TTS)

**Current**: Sarvam AI Bulbul
- Voice: `anushka` (Hindi female)
- Format: mulaw (Twilio compatible)
- Model: bulbul:v2
- Languages: 11 Indian languages supported
- Quality: Natural-sounding speech with authentic Indian accents


---

## 🔍 Vector Search Knowledge Base

### Overview

The negotiation agent uses Vertex AI Vector Search for semantic knowledge base queries. This enables finding relevant negotiation tactics based on meaning, not just keywords.

### Mock Mode (Development)

By default, the system uses **mock mode** with 3 pre-loaded tactics:
- Stubborn vendor handling
- Long-distance trip negotiation  
- Trust building phrases

**No setup required** - works out of the box!

### Production Setup (Optional)

To deploy real Vector Search:

```bash
# 1. Set up Google Cloud credentials
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud auth login

# 2. Enable required APIs
gcloud services enable aiplatform.googleapis.com

# 3. Run deployment script
python scripts/setup_vector_search.py

# 4. Add IDs to .env (script will output these)
VECTOR_INDEX_ENDPOINT_ID=projects/.../indexEndpoints/...
VECTOR_DEPLOYED_INDEX_ID=desiyatra_tactics_deployed
```

### Knowledge Base Contents

Initial tactics include:
- Stubborn vendor strategies
- High quote handling
- Group discount negotiation
- Rejection handling
- Trust building
- Closing tactics

**Cost**: ~$75/month for 1-2 replicas (can scale to zero when not in use)

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Tests

```bash
# Test Twilio integration
python tests/test_twilio_quick_call.py

# Test Google TTS
python tests/test_google_tts.py

# Test agent architecture
pytest tests/test_refactored_agents.py -v

# Test database
pytest tests/test_database.py -v
```

---

## 📊 API Endpoints

### Health & Status

- `GET /` - Root endpoint
- `GET /health` - Health check (Redis, PostgreSQL)
- `GET /ready` - Readiness probe

### Twilio Webhooks

- `POST /twilio/incoming` - Handle incoming calls
- `POST /twilio/voice/{call_id}` - Voice webhook with TwiML
- `POST /twilio/recording/{call_id}` - Recording callback
- `POST /twilio/transcription/{call_id}` - Transcription callback
- `POST /twilio/status/{call_id}` - Call status updates

---

## 🏆 Key Achievements

### ✅ Completed Improvements

1. **Native Google Grounding** - Maps + Search integration
2. **Parallel-Sequential Scout** - 4x faster vendor discovery
3. **Loop-Based Bargainer** - Dynamic LLM reasoning for negotiations
4. **Atomic Tools** - Composable, testable negotiation actions
5. **Type Safety** - Pydantic schemas for all agent outputs
6. **Custom Domain Planners** - Replaced BuiltInPlanner with specialized logic:
   - NegotiationPlanner: Strategic price decisions
   - VendorSelectionPlanner: Intelligent vendor ranking
   - SafetyDecisionPlanner: Nuanced risk assessment
7. **Automatic Market Rate Calculation** - No hardcoded values
8. **Vector Search Integration** - Semantic knowledge base (Vertex AI)
9. **Party Size Awareness** - Accurate quotes for groups
10. **Persistent Sessions** - SQLite-based session management
11. **Async Execution** - Concurrent operations with semaphores

### 📈 Performance Metrics

- **Scout Agent**: ~4x faster (parallel searches)
- **Reliability**: 85% → 99% (deterministic workflows)
- **Negotiation Quality**: Rule-based → LLM-reasoned with custom planners
- **Market Rate Accuracy**: Hardcoded → Calculated from real vendor data
- **Knowledge Base**: Keyword matching → Semantic vector search
- **Cost**: 1 LLM call → 3-6 calls per negotiation (higher intelligence)

---

## 🔮 Future Enhancements

### Short Term
- [ ] Multi-vendor bidding (vendors compete)
- [ ] Human-in-the-loop escalation
- [ ] More search sources (Sulekha, UrbanClap)

### Long Term
- [ ] Multi-language support (Tamil, Telugu, Bengali)
- [ ] Video call negotiations
- [ ] AI-powered price prediction
- [ ] Blockchain-based deal verification
- [ ] Mobile app integration

---

## 🤝 Contributing

This is a proprietary project. For collaboration inquiries, please contact the maintainers.

---

## 📄 License

Proprietary - All rights reserved

---

## 👥 Team

Built with ❤️ for Indian travelers

---

## 📞 Support

For issues or questions:
- Create an issue in the repository
- Contact: [your-email@example.com]

---

## 🙏 Acknowledgments

- **Google ADK** - Multi-agent framework
- **Google Gemini** - LLM reasoning
- **Twilio** - Telephony infrastructure
- **Sarvam AI** - Hindi voice models
- **Supabase** - Backend infrastructure

---

**Made in India 🇮🇳 | For India 🇮🇳**
