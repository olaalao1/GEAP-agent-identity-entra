import os
from google.adk import Agent, App, Gemini
from vertexai import types
from token_agent.tools.entra.entra_kv import get_azure_secret

MODEL = "gemini-2.5-flash"

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are an assistant designed to demonstrate cross-cloud credential-less integration. "
        "Your primary capability is securely retrieving secret values from Azure Key Vault using "
        "your Google Agent Identity federated with Microsoft Entra ID. "
        "When asked to retrieve or display a secret from Azure, use the get_azure_secret tool. "
        "Present any retrieved values cleanly and securely, and explain that no passwords or static "
        "keys were used during the entire token exchange process."
    ),
    tools=[get_azure_secret],
)

app = App(
    root_agent=root_agent,
    name="google-agent-identity-entra",
)
