"""
DesiYatra Multi-Agent Orchestrator

This module defines the main sequential pipeline that orchestrates the Scout,
Safety Officer, and Bargainer agents to perform the full trip negotiation workflow.
"""
from google.adk.agents import SequentialAgent

# Import the composable agent instances from the other modules.
from agents.adk_agents.scout.agent import scout_agent
from agents.adk_agents.safety_officer.agent import safety_officer_agent
from agents.adk_agents.bargainer.agent import bargainer_agent

# Define the main orchestrator as a SequentialAgent.
# This agent will execute its sub-agents in the order they are provided.
# The ADK framework automatically handles passing the output of one agent
# to the next agent via shared session state.
munshi_orchestrator_agent = SequentialAgent(
    name="MunshiOrchestrator",
    description="The master orchestrator for trip negotiation. Manages the workflow from finding vendors to securing deals.",
    sub_agents=[
        scout_agent,
        safety_officer_agent,
        bargainer_agent,
    ]
)
