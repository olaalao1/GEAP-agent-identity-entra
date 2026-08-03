# Google Agent Identity OIDC Federation to Microsoft Entra

[![GCP Vertex AI](https://img.shields.io/badge/GCP-Vertex%20AI-blue?logo=google-cloud&logoColor=white)](https://cloud.google.com/vertex-ai)
[![Microsoft Entra](https://img.shields.io/badge/Microsoft-Entra%20ID-0078D4?logo=microsoft-azure&logoColor=white)](https://learn.microsoft.com/en-us/entra/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

This repository demonstrates how an agent built with the **Google Agent Development Kit (ADK)** and deployed to **Gemini Enterprise Agent Runtime** can use **Google Agent Identity** to securely authenticate across cloud providers.

Specifically, it illustrates a cross-cloud token exchange flow:
1.  **Retrieve Identity Token:** The agent fetches its short-lived GCP Agent Identity OIDC ID Token from the Google Metadata Server. This token is cryptographically bound to the unique SPIFFE identity of the reasoning engine container.
2.  **Exchange for Azure Token:** The agent exchanges this GCP OIDC ID Token at Microsoft Entra's token endpoint (`/oauth2/v2.0/token`) for a short-lived Azure Access Token.
3.  **Access Azure Virtual Machine:** The agent uses the temporary Entra credentials to securely access, manage, and execute command scripts on an Azure Virtual Machine via the Azure REST API.

---

## Architecture & Workflow

```mermaid
sequenceDiagram
    autonumber
    participant Agent as ADK Agent (Vertex AI Runtime)
    participant Meta as Google Metadata Server
    participant Entra as Microsoft Entra ID (OIDC Provider)
    participant VM as Azure Virtual Machine (REST API)
    participant Gemini as Gemini 2.5 Flash

    Note over Agent: Step 1: Request OIDC Identity Token
    Agent->>Meta: GET /instance/service-accounts/default/identity?audience=api://AzureADTokenExchange
    Meta-->>Agent: Return signed GCP Agent Identity OIDC Token (JWT)

    Note over Agent: Step 2: Exchange for Azure Access Token
    Agent->>Entra: POST /oauth2/v2.0/token (client_credentials with client_assertion)
    rect rgb(240, 248, 255)
        Note over Entra: Entra verifies GCP JWT against<br/>GCP STS OpenID Configuration & JWKS
    end
    Entra-->>Agent: Return Azure AD Access Token (Management Scope)

    Note over Agent: Step 3: Connect and Control VM
    Agent->>VM: POST /runCommand?api-version=2023-09-01 (Authorization: Bearer <Azure Token>, Command: "ls")
    VM-->>Agent: Return stdout / stderr results of script execution

    Note over Agent: Step 4: Multimodal Reasoning
    Agent->>Gemini: Parse stdout / list files and run deep analysis
    Gemini-->>Agent: Deliver contextual response to user
```

---

## Repository Structure

```
.
├── deploy.py               # Deploy/update the agent to Vertex AI Agent Runtime
├── requirements.txt        # Python dependencies for the agent container
├── .env.example            # Template for environment configuration
└── token_agent/
    ├── __init__.py         # Module entry point exporting `app`
    ├── agent.py            # ADK Root Agent and system prompt configuration
    ├── identity.py         # Google Metadata OIDC token retrieval utility
    └── tools/
        └── entra/
            ├── __init__.py # Exposes Entra tools
            └── entra_vm.py # Token Exchange & Virtual Machine control tools
```

---

## Azure & Entra ID Configuration Guide

To enable Google Cloud Agent Identity to authenticate to Microsoft Entra ID via Workload Identity Federation, complete the following configuration steps in the **Microsoft Entra Admin Center**:

### Step 1: Configure Microsoft Entra ID App Registration
1. Navigate to **Identity > Applications > App registrations** and click **New registration**.
   * **Name:** `GEAP-agent-identity-entra`
   * **Supported account types:** Single tenant (Accounts in this organizational directory only).
2. Click **Register** and note down the **Application (client) ID** and **Directory (tenant) ID**.

### Step 2: Add Federated Identity Credential in Entra ID
1. Inside your App Registration, go to **Certificates & secrets** > **Federated credentials**.
2. Click **Add credential** and choose the **Custom provider** / **Other scenario** in the dropdown.
3. Configure the credential fields exactly as follows:
   * **Issuer URL:**  
     `https://sts.googleapis.com/v1/organizations/YOUR_GCP_ORG_ID/locations/global/workloadIdentityPools/agents.global.org-YOUR_GCP_ORG_ID.system.id.goog`
   * **Subject identifier (`sub`):**  
     `spiffe://agents.global.org-YOUR_GCP_ORG_ID.system.id.goog/resources/aiplatform/projects/YOUR_GCP_PROJECT_ID/locations/us-central1/reasoningEngines/google-agent-identity-entra`
   * **Audience:** `api://AzureADTokenExchange`
   * **Name:** `gcp-agent-federation-credential`
4. Click **Add** to save.

> [!WARNING]
> Mappings are highly case-sensitive. The `sub` and `Issuer URL` values must match your Google Cloud variables character-for-character. Any deviation (such as a trailing slash) will result in authorization failures (`AADSTS700212`).

### Step 3: Grant Virtual Machine Access in Azure
To allow your App Registration to execute scripts and run basic command commands via the **Run Command API**, you must assign the appropriate RBAC roles:
1. Navigate to your target Azure Virtual Machine (or resource group) in the Azure Portal.
2. Select **Access control (IAM)** > **Add role assignment**.
3. Grant the `GEAP-agent-identity-entra` application the **Virtual Machine Contributor** role (or a custom role granting the `Microsoft.Compute/virtualMachines/runCommand/action` action).

---

## Deployment to Vertex AI Agent Runtime

### 1. Set Up Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Environment Variables
Copy `.env.example` to `.env` and supply your actual IDs:
```bash
cp .env.example .env
export $(cat .env | xargs)
```

### 3. Deploy Agent
```bash
python3 deploy.py
```

---

## Usage Examples & System Rules

The agent operates under precise directives designed to prioritize federated credentials and handle multimodal inputs:

*   **Rule 1: Token Queries:** If you ask the agent, *"What are your active identity credentials?"* or *"What is your token?"*, it will invoke `fetch_agent_identity_token_details` and print the returned JSON payload verbatim.
*   **Rule 2: Virtual Machine Commands:** If you request VM commands (e.g., *"List files inside my Azure VM"* or *"Create a file test.txt inside the Azure VM"*), the agent will automatically call `fetch_agent_identity_token_details` to acquire the active OIDC and Entra tokens, then use them to run `ls`, `pwd`, `touch`, or `cp` via the Run Command tool.
*   **Rule 3: Multimodal Vision:** The agent has full multimodal capabilities. You can upload PDFs, images, or documentation to have them parsed, verified, or compared with VM directory trees.

---

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
