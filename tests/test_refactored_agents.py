"""
Tests for the refactored ADK agents (Parallel-Sequential Scout and Loop-Based Bargainer)
"""
import pytest
from agents.adk_agents.scout.agent import scout_agent, parallel_search_agent, processing_agent
from agents.adk_agents.bargainer.agent import bargainer_agent, negotiation_loop, negotiation_turn_agent
from agents.adk_agents.bargainer import atomic_tools

def test_scout_agent_structure():
    """Test that ScoutAgent has the correct Parallel-Sequential structure."""
    assert scout_agent.name == "ScoutAgent"
    assert len(scout_agent.sub_agents) == 2
    
    # First sub-agent should be ParallelSearchAgent
    assert scout_agent.sub_agents[0].name == "ParallelSearchAgent"
    assert len(scout_agent.sub_agents[0].sub_agents) == 4  # 4 search agents
    
    # Second sub-agent should be ProcessingAgent
    assert scout_agent.sub_agents[1].name == "ProcessingAgent"

def test_parallel_search_agent_structure():
    """Test that ParallelSearchAgent has all 4 search sub-agents."""
    search_agent_names = [agent.name for agent in parallel_search_agent.sub_agents]
    
    assert "GoogleSearchAgent" in search_agent_names
    assert "GoogleMapsAgent" in search_agent_names
    assert "JustDialAgent" in search_agent_names
    assert "IndiaMartAgent" in search_agent_names

def test_bargainer_agent_structure():
    """Test that BargainerAgent has the correct Loop-Based structure."""
    assert bargainer_agent.name == "BargainerAgent"
    assert len(bargainer_agent.sub_agents) == 2
    
    # First sub-agent should be VendorIteratorAgent
    assert bargainer_agent.sub_agents[0].name == "VendorIteratorAgent"
    
    # Second sub-agent should be NegotiationLoop
    assert bargainer_agent.sub_agents[1].name == "NegotiationLoop"

def test_negotiation_loop_structure():
    """Test that NegotiationLoop has correct configuration."""
    assert negotiation_loop.name == "NegotiationLoop"
    assert negotiation_loop.max_iterations == 6
    assert len(negotiation_loop.sub_agents) == 1
    assert negotiation_loop.sub_agents[0].name == "NegotiationTurnAgent"

def test_negotiation_turn_agent_tools():
    """Test that NegotiationTurnAgent has all atomic tools."""
    tool_names = [tool.__name__ for tool in negotiation_turn_agent.tools]
    
    assert "send_message" in tool_names
    assert "accept_deal" in tool_names
    assert "end_call" in tool_names

def test_atomic_tool_initiate_call():
    """Test the initiate_call atomic tool."""
    vendor = {
        "name": "Test Vendor",
        "phone": "+919876543210",
        "category": "taxi"
    }
    trip_context = {
        "market_rate": 2800.0,
        "budget_max": 3000.0
    }
    
    result = atomic_tools.initiate_call(vendor, trip_context)
    
    assert "call_id" in result
    assert result["vendor_name"] == "Test Vendor"
    assert result["status"] == "CALL_INITIATED"
    assert result["call_id"] in atomic_tools._active_calls

def test_atomic_tool_send_message():
    """Test the send_message atomic tool."""
    # First initiate a call
    vendor = {"name": "Test Vendor", "phone": "+919876543210", "category": "taxi"}
    trip_context = {"market_rate": 2800.0, "budget_max": 3000.0}
    init_result = atomic_tools.initiate_call(vendor, trip_context)
    call_id = init_result["call_id"]
    
    # Send a message
    result = atomic_tools.send_message(call_id, "Thoda kam kar dijiye", offer=2800.0)
    
    assert result["call_id"] == call_id
    assert "vendor_response" in result
    assert "current_quote" in result
    assert result["round"] == 1

def test_atomic_tool_accept_deal():
    """Test the accept_deal atomic tool."""
    # First initiate a call
    vendor = {"name": "Test Vendor", "phone": "+919876543210", "category": "taxi"}
    trip_context = {"market_rate": 2800.0, "budget_max": 3000.0}
    init_result = atomic_tools.initiate_call(vendor, trip_context)
    call_id = init_result["call_id"]
    
    # Accept the deal
    result = atomic_tools.accept_deal(call_id, 2900.0)
    
    assert result["vendor_name"] == "Test Vendor"
    assert result["negotiated_price"] == 2900.0
    assert result["status"] == "DEAL_SUCCESS"
    assert call_id not in atomic_tools._active_calls  # Should be cleaned up

def test_atomic_tool_end_call():
    """Test the end_call atomic tool with escalation."""
    from unittest.mock import Mock
    
    # First initiate a call
    vendor = {"name": "Test Vendor", "phone": "+919876543210", "category": "taxi"}
    trip_context = {"market_rate": 2800.0, "budget_max": 3000.0}
    init_result = atomic_tools.initiate_call(vendor, trip_context)
    call_id = init_result["call_id"]
    
    # Mock tool context
    mock_context = Mock()
    mock_context.actions = Mock()
    
    # End the call
    result = atomic_tools.end_call(mock_context, call_id, "max_rounds_reached")
    
    assert result["status"] == "CALL_ENDED"
    assert result["reason"] == "max_rounds_reached"
    assert mock_context.actions.escalate == True
    assert call_id not in atomic_tools._active_calls  # Should be cleaned up

def test_output_schemas():
    """Test that agents have correct output schemas."""
    # Scout's ProcessingAgent should output FoundVendorsList
    assert processing_agent.output_key == "found_vendors"
    assert processing_agent.output_schema is not None
    
    # Bargainer's VendorIteratorAgent should output DealsList
    vendor_iterator = bargainer_agent.sub_agents[0]
    assert vendor_iterator.output_key == "final_deals"
    assert vendor_iterator.output_schema is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
