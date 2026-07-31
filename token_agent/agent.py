import os
from google.adk import Agent, App, Gemini
from vertexai import types
from token_agent.tools.entra import fetch_agent_identity_token_details, execute_command_on_azure_vm

MODEL = "gemini-2.5-flash"

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are an ADK agent with full multimodal vision and document analysis capabilities. "
        "You can connect to an Azure virtual machine to run basic command commands such as ls, pwd, touch and cp.\n\n"
        "Follow these rules for tool usage:\n"
        "1. Token / Identity Queries: When the user asks specifically for your token or identity credentials, "
        "call `fetch_agent_identity_token_details` and return the JSON payload verbatim to the user.\n\n"
        "2. Azure Virtual Machine Access: For all other requests (such as listing files, copying and making files within and Azure VM):\n"
        "   - Call `fetch_agent_identity_token_details` to retrieve the agent identity token.\n"
        "3. Multimodal Analysis: You HAVE FULL MULTIMODAL CAPABILITIES for analyzing images, PDFs, and documents."
    ),
    tools=[fetch_agent_identity_token_details, execute_command_on_azure_vm],
)

app = App(
    root_agent=root_agent,
    name="google-agent-identity-entra",
)
