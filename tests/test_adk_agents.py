"""
Tests for the ADK-based agent system.
"""
import pytest
from agents.adk_agents.munshi.agent import MunshiAgent

@pytest.fixture
def munshi_agent():
    """Returns an instance of the MunshiAgent."""
    return MunshiAgent()

def test_trip_orchestration(munshi_agent):
    """
    Tests the full trip orchestration flow.
    """
    trip_request = {
        "trip_id": "test_trip_123",
        "user_id": "test_user_456",
        "destination": "Manali",
        "services": ["taxi", "homestay"],
        "budget": {
            "min": 25000,
            "max": 30000,
            "stretch": 32000,
        },
        "preferences": {},
    }

    result = munshi_agent.start_trip_orchestration(trip_request)

    assert result["status"] == "SUCCESS"
    assert "deals" in result
    assert len(result["deals"]) > 0
    # Add more assertions here to validate the deals
