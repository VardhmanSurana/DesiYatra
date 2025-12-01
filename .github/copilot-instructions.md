# DesiYatra - Copilot Instructions

## Project Overview

**DesiYatra** is an AI-powered travel negotiation system for India that finds local vendors, calls them via Twilio, and negotiates prices in natural Hindi/Hinglish. It uses a **multi-agent orchestration pattern** with specialized agents coordinated by a central Munshi (orchestrator).

### Core Architecture

- **Multi-Agent System**: Four specialized agents coordinate to negotiate travel services
  - **Munshi** (`agents/munshi/orchestrator.py`): Orchestrator - manages state machine and delegates to sub-agents
  - **Scout** (`agents/scout/agent.py`): Finds vendors via Google Maps/JustDial/web search
  - **Bargainer** (`agents/bargainer/agent.py`): Makes voice calls and negotiates prices
  - **Safety Officer** (`agents/safety_officer/agent.py`): Pre-call vetting and real-time fraud detection

- **Tech Stack**: Python 3.12 (backend), FastAPI (API), Supabase PostgreSQL (data), Redis (state), Twilio (calls), Sarvam AI (Hindi voice)

---

## Project-Specific Conventions (IMPORTANT)

### 1. **File Creation Policy**

**DO NOT create markdown (`.md`) or shell (`.sh`) files unless explicitly asked by the user.** This prevents unnecessary file clutter and keeps the project organized. Users should request specific file creation when needed.

### 2. **Python Package & Environment Management**

**Use `uv` for ALL package management operations:**
```bash
# Install packages
uv pip install package_name

# Install from requirements
uv pip install -r requirements.txt

# List installed packages
uv pip list
```

**Use `venv` (virtual environment) ONLY for running Python files:**
```bash
# Activate venv for running scripts
source .venv/bin/activate

# Run Python files after activation
python script.py
uvicorn agents.main:app --reload
```

**NEVER use `python` for:**
- Installing packages → use `uv pip install`
- Running Docker commands → use `docker-compose up`
- Building containers → use `docker build`

### 3. **Test Script Location**

**Write ALL test scripts in the `tests/` folder** (not in root). Follow naming convention `test_*.py`:
```
tests/
├── test_bargainer.py
├── test_scout.py
├── test_safety_officer.py
└── test_munshi.py
```

Run tests from project root:
```bash
source .venv/bin/activate  # activate venv first
pytest tests/              # run all tests
pytest tests/test_bargainer.py -v  # run specific test
```

---

## Critical Architecture Patterns

### 1. **State Machine Design** (Munshi Orchestrator)

The orchestrator follows a strict state progression for each trip:

```
PLANNING → SCOUTING → VETTING → NEGOTIATING → CONFIRMING → COMPLETE
```

**Key insight**: Each state is an async method that returns an `OrchestrationResult` with success flag and data payload. States must be idempotent (safe to retry). See `agents/munshi/orchestrator.py` lines 30-120 for the main `orchestrate_trip()` method.

**Important**: The Munshi delegates to sub-agents (Scout, Safety, Bargainer) via simulation methods (lines 350+). In production, these would be replaced with webhook calls to actual agent services.

### 2. **Call Session State Management** (Bargainer Agent)

Bargainer maintains call state in Redis with structure:
```
call_id → {state, vendor_info, offers[], counters[], transcript[], user_budget}
```

The call follows this state machine:
```
DIALING → GREETING → QUALIFYING → PITCHING → NEGOTIATING → CONFIRMING → CLOSING
```

**Critical detail**: Use `asyncio.Semaphore` to limit concurrent calls (default 3) to prevent resource exhaustion.

### 3. **Database Integration Pattern**

All database operations use the Supabase client in `agents/shared/database.py`. Pattern:
- **Create**: `create_trip()`, `create_call()` return created record or None
- **Read**: `get_trip()`, `get_user()` fetch by ID
- **Update**: `update_trip_status()`, `add_call_event()` modify records
- **Query**: All operations log errors, never raise (fail gracefully)

See schema migrations in `migrations/` for table structure.

### 4. **Logging Convention**

Use `loguru` logger with emoji prefixes for visibility:
```python
logger.info(f"🔍 [SCOUT] Searching...")    # Info with emoji
logger.warning(f"⚠️  Issue detected")      # Warnings
logger.error(f"❌ Failed: {error}")        # Errors
logger.success(f"✅ Completed")            # Success
```

This creates scannable logs. Always include context: trip_id, vendor info, state.

---

## Developer Workflows

### Running Locally

```bash
# Activate virtual environment
source .venv/bin/activate

# Start all services (Redis, Postgres, Agents API)
docker-compose up

# OR run without Docker:
redis-server &
uvicorn agents.main:app --reload
```

The API will be at `http://localhost:8000`. Health endpoint: `GET /health`

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest test_bargainer.py -v

# With coverage
pytest --cov=agents --cov-report=html
```

Test fixtures use mocking extensively. Key mock pattern in `test_bargainer.py`:
```python
with patch('agents.bargainer.agent.redis_client') as mock_redis:
    # Mock Redis operations
```

### Adding New Migrations

SQL migrations live in `migrations/` numbered sequentially (001_*, 002_*, etc).

```bash
# New migration
cat > migrations/008_create_your_table.sql << 'EOF'
CREATE TABLE your_table (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- columns
);
EOF

# Apply on next docker-compose up or manually via Supabase console
```

---

## Project-Specific Conventions & Patterns

### 1. **Async-First**

All I/O operations are async:
```python
async def orchestrate_trip(trip_id: str):
    # Always use await for database, network, asyncio operations
    trip = get_trip(trip_id)  # ❌ blocks event loop
    trip = await asyncio.to_thread(get_trip, trip_id)  # ✅ proper
```

### 2. **Error Recovery Over Failure**

Never crash the entire orchestration for a single vendor failure:
```python
# ✅ Good: Continue to next vendor
try:
    result = await negotiate_with_vendor(vendor)
except Exception as e:
    logger.warning(f"Vendor failed: {e}")
    continue  # Try next vendor

# ❌ Bad: Crash whole trip
raise  # Propagates to user failure
```

### 3. **Budget Constraints**

Three-tier budget model enforced throughout:
- `budget_min`: Minimum acceptable price
- `budget_max`: Target/comfortable price
- `budget_stretch`: Absolute max for exceptional deal

Negotiation logic must respect these boundaries. See `agents/bargainer/agent.py` for tactic selection that honors budget limits.

### 4. **Vendor Deduplication**

Scout agent normalizes Indian phone numbers before deduplicating:
```python
# Scout._deduplicate_vendors() uses phone number as unique key
# Handles: +91, 0 prefix, spaces, dashes
# e.g., "+91 9876543210", "09876543210", "+919876543210" → single vendor
```

### 5. **Data Model Consistency**

Models defined in `agents/shared/models.py` use Pydantic enums:
- `TripStatus`: PLANNING, SCOUTING, VETTING, NEGOTIATING, CONFIRMING, COMPLETE, FAILED
- `CallStatus`: INITIATED, CONNECTED, IN_PROGRESS, COMPLETED, FAILED, NO_ANSWER
- `CallOutcome`: AGREED, REJECTED, NO_ANSWER, FRAUD_DETECTED, VENDOR_UNAVAILABLE

Always use these enums; never use raw strings.

---

## Integration Points & External Dependencies

### 1. **Twilio Integration**

Calls are initiated via Twilio. Expected flow:
```python
twilio_client.calls.create(
    to=vendor_phone,
    from_=settings.twilio_phone_number,
    url=f"{settings.webhook_base_url}/api/webhooks/twilio/voice"
)
```

Webhooks at `/api/webhooks/twilio/voice` and `/api/webhooks/twilio/stream` handle call state updates and media streams.

### 2. **Sarvam AI Voice API**

STT (speech-to-text) and TTS (text-to-speech) for Hindi/Hinglish:
```python
# STT: Convert vendor audio to text
response = await sarvam_client.speech_to_text(
    audio_data=audio_bytes,
    language="hi",  # Hindi, mixed with English
)

# TTS: Convert negotiation text to audio
audio_url = await sarvam_client.text_to_speech(
    text="Bhaiya, aap kitna kar doge?",
    language="hi"
)
```

### 3. **Supabase Real-time Subscriptions** (Optional)

For real-time frontend updates, agents publish to Redis pub/sub. Frontend subscribes via Server-Sent Events:
```python
# Python agent publishes
redis_client.publish(f"trip:{trip_id}:updates", json.dumps({
    "type": "vendor_found",
    "data": {"vendor_name": "City Taxis"}
}))

# Next.js frontend subscribes
GET /api/trips/[tripId]/stream
```

### 4. **Google Serper API** (Scout searches)

Scout uses Serper for web search:
```python
headers = {"X-API-KEY": settings.serper_api_key}
payload = {"q": "taxi service manali phone", "num": 10}
```

---

## Common Development Tasks

### Adding a New Negotiation Tactic

Tactics are defined in a retrievable knowledge base (RAG-style) in Bargainer:

1. **Pattern**: When-to-use condition → Recommended script → Price calculation
2. **Example** (Competitor Anchoring):
   ```python
   # In bargainer.negotiation_tactics
   {
       "name": "competitor_anchoring",
       "trigger": "quote_1_3x_market_rate",  # When vendor > 1.3x market
       "script_hindi": "Bhaiya ₹{lower_price} bola tha",
       "price_calc": "min(market_rate, vendor_quote * 0.85)"
   }
   ```
3. Add to tactic selection logic (`_select_tactic()`)

### Adding a New Fraud Pattern (Safety Officer)

1. **Add trigger phrase** to `safety_officer.fraud_patterns`
2. **Assign severity**: CRITICAL (immediate hangup), WARNING (flag and continue), LOG_ONLY
3. **Provide deflection response**: Hindi script to redirect vendor

Example:
```python
fraud_patterns = {
    "otp": {
        "triggers": ["otp", "code bhejo", "verification"],
        "severity": "CRITICAL",
        "action": "IMMEDIATE_HANGUP"
    }
}
```

### Implementing a New Search Source (Scout)

1. Create new `_search_[source]()` method in `ScoutAgent`
2. Returns: `List[Dict[str, Any]]` with keys: `phone`, `name`, `location`, `source`, `rating` (optional)
3. Add to parallel search in `search_vendors()` using `asyncio.gather()`
4. Deduplication happens automatically in `_deduplicate_vendors()`

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `agents/munshi/orchestrator.py` | Main state machine - READ FIRST for trip lifecycle |
| `agents/shared/models.py` | Pydantic models - reference for data structures |
| `agents/shared/database.py` | Database operations - all Supabase queries here |
| `agents/shared/config.py` | Settings/env variables - never hardcode secrets |
| `migrations/` | SQL schema - source of truth for data model |
| `pyproject.toml` | Dependencies and test config |
| `docker-compose.yml` | Local dev environment - modify for new services |

---

## Debugging & Troubleshooting

### Call Connection Issues
- Check Twilio account SID/auth token in `.env`
- Verify phone number format is normalized (Scout handles this)
- Check Redis for stale call sessions that prevent reconnection

### Vendor Not Found
- Scout searches Google Serper, JustDial (simulated), returns empty list if all fail
- Check Serper API key and rate limits
- Verify destination name matches expected format (city name, not region)

### State Machine Stuck
- Check Redis session for `call_id:state` key
- Review logs for which state failed and why
- Munshi retries are limited (2x for calls, 3x for API calls)

### Database Connection Pool Exhausted
- Check `Supabase` client is reused (singleton in `database.py`)
- Verify not opening new connections in loops
- Monitor concurrent trips (default max 10 in settings)

---

## Testing Guidelines

### Unit Tests
- Mock Twilio, Sarvam AI, external APIs
- Test state transitions in isolation
- Use `@pytest.fixture` for setup/teardown

### Integration Tests  
- Use `test_database.py` pattern: create test user/trip, verify state changes
- Mock only external services (Twilio, Sarvam)
- Keep Supabase/Redis real (use test database)

### End-to-End
- Full trip from submission to completion
- Verify all agents ran correctly
- Check Redis, Supabase state is consistent

---

## Performance Considerations

1. **Concurrency Limits**: Max 3 concurrent calls (Semaphore) to stay within Twilio limits and avoid audio processing bottleneck
2. **Redis Expiry**: Call sessions expire after 300s (call timeout), preventing zombie sessions
3. **Database Indexes**: Queries on `trip_id`, `user_id`, `vendor_phone` - check `migrations/` for indexes
4. **Batch Operations**: Call events added via `add_call_event()` - consider batching if > 10 events/call

---

## When to Ask for Context

- **Complex negotiation scenarios**: Check `agents/bargainer/agent.py` for tactic logic
- **New fraud patterns**: Review `agents/safety_officer/agent.py` for existing pattern structure
- **Database schema changes**: Reference `migrations/` and `agents/shared/models.py`
- **State transitions failing**: Check `agents/munshi/orchestrator.py` state method implementations
