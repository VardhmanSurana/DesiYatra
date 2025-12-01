"""
Comprehensive tests for Bargainer Agent call state machine

Tests cover:
- Call initiation
- Vendor greeting and qualification
- Negotiation rounds with price convergence
- Deal confirmation
- Call termination
- Session state persistence
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.append('/home/vardhmansurana/Code/Projects/DesiYatra')

from agents.bargainer.agent import (
    BargainerAgent,
    CallState,
    NegotiationPhase,
    CallSession,
    CallAnalysis,
)


class TestBargainerAgent:
    """Test suite for Bargainer Agent"""
    
    @pytest.fixture(autouse=True)
    def mock_redis(self):
        """Mock Redis client for all tests"""
        # In-memory session store for testing
        self.session_store = {}
        
        async def mock_setex(key, ttl, data):
            self.session_store[key] = data
        
        async def mock_get(key):
            return self.session_store.get(key)
        
        with patch('agents.bargainer.agent.redis_client') as mock_redis:
            mock_redis.setex = mock_setex
            mock_redis.get = mock_get
            yield mock_redis
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return BargainerAgent()
    
    @pytest.fixture
    def sample_call_params(self):
        """Sample call parameters"""
        return {
            "trip_id": "trip_123",
            "vendor_id": "vendor_456",
            "user_id": "user_789",
            "destination": "Goa",
            "service_type": "accommodation",
            "user_budget": 3000.0,
            "check_in_date": "2024-12-20",
        }
    
    @pytest.mark.asyncio
    async def test_initiate_call_success(self, agent, sample_call_params):
        """Test successful call initiation"""
        with patch('agents.bargainer.agent.get_vendor') as mock_get_vendor, \
             patch('agents.bargainer.agent.get_trip') as mock_get_trip, \
             patch('agents.bargainer.agent.create_call') as mock_create_call, \
             patch('agents.bargainer.agent.add_call_event') as mock_log_event:
            
            # Mock responses
            mock_get_vendor.return_value = {
                "id": "vendor_456",
                "name": "Goa Beachfront Resort",
                "phone": "+919876543210"
            }
            mock_get_trip.return_value = {"id": "trip_123", "user_id": "user_789"}
            mock_create_call.return_value = "call_001"
            
            # Initiate call
            analysis = await agent.initiate_call(**sample_call_params)
            
            # Assertions
            assert analysis.state == CallState.DIALING
            assert analysis.vendor_name == "Goa Beachfront Resort"
            assert analysis.user_quote == 3000.0
            assert analysis.next_action == "WAIT_FOR_ANSWER"
            assert analysis.confidence_score == 0.8
            
            # Verify session was created
            session = await agent._get_session("call_001")
            assert session is not None
            assert session.destination == "Goa"
            assert session.user_budget == 3000.0
    
    @pytest.mark.asyncio
    async def test_initiate_call_vendor_not_found(self, agent, sample_call_params):
        """Test call initiation with missing vendor"""
        with patch('agents.bargainer.agent.get_vendor') as mock_get_vendor:
            mock_get_vendor.return_value = None
            
            analysis = await agent.initiate_call(**sample_call_params)
            
            assert analysis.state == CallState.DEADLOCK
            assert analysis.next_action == "ABORT"
            assert analysis.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_vendor_greeting_and_quote(self, agent):
        """Test vendor responds with quote"""
        # Setup: Create a session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.DIALING,
        )
        await agent._save_session(session)
        
        # Process vendor response
        analysis = await agent.process_vendor_response(
            call_id="call_001",
            vendor_quote=5000.0,
            vendor_message="We can offer ₹5000 per night"
        )
        
        # Assertions
        assert analysis.state == CallState.GREETING
        assert analysis.current_quote == 5000.0
        assert "₹5000" in analysis.transcript_snippet
        assert analysis.next_action == "QUALIFY_VENDOR"
    
    @pytest.mark.asyncio
    async def test_vendor_qualification_high_price(self, agent):
        """Test vendor qualification with high quote"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.GREETING,
            vendor_quote=6000.0,
        )
        await agent._save_session(session)
        
        # Qualify vendor
        analysis = await agent.qualify_vendor("call_001")
        
        # Assertions: High quote but interested
        assert analysis.state == CallState.QUALIFYING
        assert analysis.current_quote == 6000.0
        assert analysis.next_action == "REQUEST_FLEXIBILITY"
        assert analysis.confidence_score == 0.75
    
    @pytest.mark.asyncio
    async def test_vendor_qualification_no_response(self, agent):
        """Test vendor qualification with zero quote (no response)"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.GREETING,
            vendor_quote=0.0,
        )
        await agent._save_session(session)
        
        # Qualify vendor
        analysis = await agent.qualify_vendor("call_001")
        
        # Assertions: No quote = deadlock
        assert analysis.state == CallState.DEADLOCK
        assert analysis.next_action == "END_CALL"
    
    @pytest.mark.asyncio
    async def test_start_negotiation(self, agent):
        """Test starting negotiation pitch"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.QUALIFYING,
            vendor_quote=5000.0,
        )
        await agent._save_session(session)
        
        # Start negotiation
        analysis = await agent.start_negotiation("call_001")
        
        # Assertions
        assert analysis.state == CallState.PITCHING
        assert analysis.negotiation_phase == NegotiationPhase.INITIAL_QUOTE
        assert "₹3150" in analysis.transcript_snippet  # Budget + 5% negotiation room
        assert analysis.next_action == "AWAIT_VENDOR_RESPONSE"
    
    @pytest.mark.asyncio
    async def test_negotiation_convergence_within_budget(self, agent):
        """Test negotiation round - vendor comes within budget"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.PITCHING,
            vendor_quote=5000.0,
            negotiation_attempts=0,
        )
        await agent._save_session(session)
        
        # Process negotiation round - vendor reduces to within budget
        analysis = await agent.process_negotiation_round(
            call_id="call_001",
            vendor_response_quote=3100.0,  # Within 5% flex
            vendor_willing_to_negotiate=True
        )
        
        # Assertions: Deal should be confirmed
        assert analysis.state == CallState.CONFIRMING
        assert analysis.current_quote == 3100.0
        assert analysis.next_action == "CONFIRM_DEAL"
        assert analysis.confidence_score == 0.9
    
    @pytest.mark.asyncio
    async def test_negotiation_convergence_partial(self, agent):
        """Test negotiation round - vendor partially converges"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.NEGOTIATING,
            vendor_quote=5000.0,
            negotiation_attempts=1,
            max_negotiation_attempts=5,
        )
        await agent._save_session(session)
        
        # Process negotiation round - vendor reduces but not enough
        analysis = await agent.process_negotiation_round(
            call_id="call_001",
            vendor_response_quote=4200.0,  # 800 reduction, still above budget
            vendor_willing_to_negotiate=True
        )
        
        # Assertions: Continue negotiation
        assert analysis.state == CallState.NEGOTIATING
        assert analysis.current_quote == 4200.0
        assert analysis.discount_offered == 800.0
        assert analysis.next_action == "CONTINUE_NEGOTIATION"
        assert analysis.negotiation_phase == NegotiationPhase.VALUE_ADD
    
    @pytest.mark.asyncio
    async def test_negotiation_max_attempts(self, agent):
        """Test hitting maximum negotiation attempts"""
        # Setup session at max attempts
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.NEGOTIATING,
            vendor_quote=3500.0,
            negotiation_attempts=5,
            max_negotiation_attempts=5,
        )
        await agent._save_session(session)
        
        # Process final negotiation round
        analysis = await agent.process_negotiation_round(
            call_id="call_001",
            vendor_response_quote=3400.0,
            vendor_willing_to_negotiate=True
        )
        
        # Assertions: Move to final offer
        assert analysis.state == CallState.CLOSING
        assert analysis.next_action == "FINAL_OFFER_OR_REJECT"
        assert analysis.confidence_score == 0.6
    
    @pytest.mark.asyncio
    async def test_confirm_booking(self, agent):
        """Test booking confirmation"""
        # Setup session in confirming state
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.CONFIRMING,
            vendor_quote=3100.0,
        )
        await agent._save_session(session)
        
        # Mock database functions
        with patch('agents.bargainer.agent.add_call_event') as mock_log, \
             patch('agents.bargainer.agent.update_vendor_stats') as mock_stats:
            
            # Confirm booking
            analysis = await agent.confirm_booking("call_001")
            
            # Assertions
            assert analysis.state == CallState.CONFIRMING
            assert analysis.current_quote == 3100.0
            assert analysis.next_action == "CLOSE_CALL"
            assert analysis.confidence_score == 0.95
            assert "Booking confirmed" in analysis.transcript_snippet
    
    @pytest.mark.asyncio
    async def test_end_call_successful(self, agent):
        """Test successful call termination"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.CONFIRMING,
            vendor_quote=3100.0,
            agreed_quote=3100.0,
            started_at=datetime.utcnow(),
        )
        await agent._save_session(session)
        
        # Mock database functions
        with patch('agents.bargainer.agent.update_call_status') as mock_update, \
             patch('agents.bargainer.agent.add_call_event') as mock_log:
            
            # End call
            analysis = await agent.end_call("call_001", success=True)
            
            # Assertions
            assert analysis.state == CallState.COMPLETED
            assert analysis.next_action == "DONE"
            assert analysis.confidence_score == 1.0
    
    @pytest.mark.asyncio
    async def test_end_call_failed(self, agent):
        """Test failed call termination (no agreement)"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.DEADLOCK,
            vendor_quote=5000.0,
            started_at=datetime.utcnow(),
        )
        await agent._save_session(session)
        
        # Mock database functions
        with patch('agents.bargainer.agent.update_call_status') as mock_update, \
             patch('agents.bargainer.agent.add_call_event') as mock_log:
            
            # End call
            analysis = await agent.end_call("call_001", success=False)
            
            # Assertions
            assert analysis.state == CallState.DEADLOCK
            assert analysis.confidence_score == 0.3
    
    @pytest.mark.asyncio
    async def test_get_session_details(self, agent):
        """Test retrieving full session details"""
        # Setup session
        session = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.NEGOTIATING,
            vendor_quote=4000.0,
            agreed_quote=3100.0,
            negotiation_attempts=2,
        )
        await agent._save_session(session)
        
        # Get session details
        details = await agent.get_session_details("call_001")
        
        # Assertions
        assert details["call_id"] == "call_001"
        assert details["vendor_name"] == "Goa Beachfront Resort"
        assert details["state"] == "NEGOTIATING"
        assert details["user_budget"] == 3000.0
        assert details["vendor_quote"] == 4000.0
        assert details["negotiation_attempts"] == 2
    
    @pytest.mark.asyncio
    async def test_session_persistence(self, agent):
        """Test session persistence across calls"""
        # Create and save session
        session1 = CallSession(
            call_id="call_001",
            trip_id="trip_123",
            vendor_id="vendor_456",
            user_id="user_789",
            vendor_name="Goa Beachfront Resort",
            vendor_phone="+919876543210",
            destination="Goa",
            check_in_date="2024-12-20",
            service_type="accommodation",
            user_budget=3000.0,
            state=CallState.NEGOTIATING,
        )
        await agent._save_session(session1)
        
        # Retrieve session
        session2 = await agent._get_session("call_001")
        
        # Assertions
        assert session2 is not None
        assert session2.call_id == session1.call_id
        assert session2.vendor_name == session1.vendor_name
        assert session2.state == session1.state
        assert session2.destination == session1.destination
    
    @pytest.mark.asyncio
    async def test_full_call_flow(self, agent):
        """Test complete call flow from initiation to completion"""
        with patch('agents.bargainer.agent.get_vendor') as mock_vendor, \
             patch('agents.bargainer.agent.get_trip') as mock_trip, \
             patch('agents.bargainer.agent.create_call') as mock_create, \
             patch('agents.bargainer.agent.add_call_event'), \
             patch('agents.bargainer.agent.update_call_status'), \
             patch('agents.bargainer.agent.update_vendor_stats'):
            
            # Setup mocks
            mock_vendor.return_value = {
                "id": "vendor_456",
                "name": "Goa Resort",
                "phone": "+919876543210"
            }
            mock_trip.return_value = {"id": "trip_123"}
            mock_create.return_value = "call_001"
            
            # 1. Initiate call
            analysis1 = await agent.initiate_call(
                trip_id="trip_123",
                vendor_id="vendor_456",
                user_id="user_789",
                destination="Goa",
                service_type="accommodation",
                user_budget=3000.0,
                check_in_date="2024-12-20",
            )
            assert analysis1.state == CallState.DIALING
            
            # 2. Vendor responds
            analysis2 = await agent.process_vendor_response(
                call_id="call_001",
                vendor_quote=4500.0,
                vendor_message="We can offer ₹4500"
            )
            assert analysis2.state == CallState.GREETING
            
            # 3. Qualify vendor
            analysis3 = await agent.qualify_vendor("call_001")
            assert analysis3.state == CallState.QUALIFYING
            
            # 4. Start negotiation
            analysis4 = await agent.start_negotiation("call_001")
            assert analysis4.state == CallState.PITCHING
            
            # 5. Negotiation round 1
            analysis5 = await agent.process_negotiation_round(
                call_id="call_001",
                vendor_response_quote=4000.0,
                vendor_willing_to_negotiate=True
            )
            assert analysis5.state == CallState.NEGOTIATING
            
            # 6. Negotiation round 2 - converge to budget
            analysis6 = await agent.process_negotiation_round(
                call_id="call_001",
                vendor_response_quote=3100.0,
                vendor_willing_to_negotiate=True
            )
            assert analysis6.state == CallState.CONFIRMING
            
            # 7. Confirm booking
            analysis7 = await agent.confirm_booking("call_001")
            assert analysis7.state == CallState.CONFIRMING
            
            # 8. End call
            analysis8 = await agent.end_call("call_001", success=True)
            assert analysis8.state == CallState.COMPLETED
            
            # Verify final session state
            final_session = await agent._get_session("call_001")
            assert final_session.agreed_quote == 3100.0
            assert final_session.negotiation_attempts == 2
            assert final_session.state == CallState.COMPLETED


def test_call_session_serialization():
    """Test CallSession serialization/deserialization"""
    original = CallSession(
        call_id="call_001",
        trip_id="trip_123",
        vendor_id="vendor_456",
        user_id="user_789",
        vendor_name="Goa Resort",
        vendor_phone="+919876543210",
        destination="Goa",
        check_in_date="2024-12-20",
        service_type="accommodation",
        user_budget=3000.0,
        state=CallState.NEGOTIATING,
        negotiation_phase=NegotiationPhase.VALUE_ADD,
        vendor_quote=4000.0,
        negotiation_attempts=2,
    )
    
    # Convert to dict
    data = original.to_dict()
    
    # Verify serialization
    assert data["state"] == "NEGOTIATING"
    assert data["negotiation_phase"] == "VALUE_ADD"
    assert isinstance(data["started_at"], str)
    
    # Reconstruct
    restored = CallSession.from_dict(data)
    
    # Verify restoration
    assert restored.call_id == original.call_id
    assert restored.state == original.state
    assert restored.negotiation_phase == original.negotiation_phase
    assert restored.vendor_quote == original.vendor_quote


def test_call_analysis_model():
    """Test CallAnalysis Pydantic model"""
    analysis = CallAnalysis(
        state=CallState.NEGOTIATING,
        vendor_name="Goa Resort",
        user_quote=3000.0,
        current_quote=4000.0,
        discount_offered=100.0,
        negotiation_phase=NegotiationPhase.VALUE_ADD,
        call_duration_seconds=120,
        transcript_snippet="Can you offer lower?",
        next_action="CONTINUE_NEGOTIATION",
        confidence_score=0.75
    )
    
    # Verify model validation
    assert analysis.state == CallState.NEGOTIATING
    assert analysis.confidence_score == 0.75
    assert 0 <= analysis.confidence_score <= 1
    
    # Test serialization
    json_data = analysis.model_dump_json()
    assert "NEGOTIATING" in json_data
    assert "0.75" in json_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
