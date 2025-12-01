from google.adk.agents import LlmAgent
from agents.adk_agents.shared.custom_planners import get_planner
from agents.adk_agents.safety_officer import tools as safety_tools
from google.genai import types
from agents.adk_agents.shared.types import Vendor, VettedVendorsList

# Define the Safety Officer Agent as a configured LlmAgent instance.
safety_officer_agent = LlmAgent(
    name="SafetyOfficerAgent",
    model="gemini-pro-latest",
    description="Vets vendors for safety by querying a BigQuery data warehouse.",
    instruction="""
    You are a diligent Safety Officer with access to a BigQuery data warehouse
    containing vendor history. Your duty is to vet a list of potential vendors
    to ensure they are safe to contact.

    You will receive a list of vendors from the session state under the 'found_vendors' key.

    **Execution Plan:**
    1. Call the `filter_safe_vendors` tool, passing the 'found_vendors' list to it.
    2. The tool will return a list of safe vendor dictionaries.
    3. Your final response MUST be a JSON object that strictly follows this schema: `{"vendors": [...]}`.
       Your response MUST start with `{` and end with `}`. Do NOT add any other text, explanation, or markdown.
    """,
    tools=[
        safety_tools.filter_safe_vendors,
        safety_tools.analyze_transcript_chunk,
    ],
    output_key="safe_vendors",
    include_contents='none',
    output_schema=VettedVendorsList,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
    ),
    planner=get_planner("safety")  # Custom safety decision logic
)
