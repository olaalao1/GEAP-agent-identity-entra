import os
import vertexai
from vertexai import types
from vertexai.agent_engines import AdkApp
from token_agent.agent import root_agent

# Retrieve deployment parameters from environment variables
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
staging_bucket = os.environ.get("GOOGLE_CLOUD_BUCKET")

if not project_id or not staging_bucket:
    raise ValueError(
        "Please ensure GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_BUCKET "
        "environment variables are configured."
    )

print(f"Initializing Vertex AI (Project: {project_id}, Location: {location})...")
client = vertexai.Client(
    project=project_id,
    location=location,
    http_options=dict(api_version="v1beta1")  # Required for Agent Identity support
)

print("Wrapping ADK Agent into AdkApp...")
vertex_app = AdkApp(agent=root_agent)

print("Deploying Agent to Gemini Enterprise Agent Runtime with AGENT_IDENTITY enabled...")
remote_app = client.agent_engines.create(
    agent=vertex_app,
    config={
        "display_name": "google-agent-identity-entra",
        "staging_bucket": staging_bucket,
        "identity_type": types.IdentityType.AGENT_IDENTITY,
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]",
            "google-adk[agent-identity]",
            "httpx"
        ],
        "env_vars": {
            "AZURE_TENANT_ID": os.environ.get("AZURE_TENANT_ID", "your-entra-tenant-id-guid"),
            "AZURE_CLIENT_ID": os.environ.get("AZURE_CLIENT_ID", "your-entra-client-id-guid"),
            "AZURE_SUBSCRIPTION_ID": os.environ.get("AZURE_SUBSCRIPTION_ID", "your-azure-subscription-id"),
            "AZURE_RESOURCE_GROUP": os.environ.get("AZURE_RESOURCE_GROUP", "your-azure-resource-group"),
            "AZURE_VM_NAME": os.environ.get("AZURE_VM_NAME", "your-azure-vm-name"),
            # Security & Token Sharing Bypass
            "GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES": "False",
            # Telemetry & Observability Settings
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        }
    },
)

print(f"\nAgent successfully deployed with Agent Identity & Federated Credentials!")
print(f"Remote App Resource Name: {remote_app.resource_name}")
