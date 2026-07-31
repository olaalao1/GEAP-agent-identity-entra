import os
import httpx
import logging
from typing import Dict, Any
from token_agent.identity import fetch_gcp_oidc_token

logger = logging.getLogger(__name__)

def fetch_agent_identity_token_details() -> Dict[str, Any]:
    """Fetches the Google Agent Identity OIDC token and exchanges it with Microsoft Entra ID.

    Returns:
        A dictionary containing the OIDC token details and the federated Entra Access Token.
    """
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    
    if not tenant_id or not client_id:
        raise ValueError("AZURE_TENANT_ID and AZURE_CLIENT_ID environment variables must be set.")

    # 1. Fetch short-lived GCP Agent Identity token from Metadata Server
    try:
        gcp_token = fetch_gcp_oidc_token(audience="api://AzureADTokenExchange")
    except Exception as e:
        logger.error(f"Failed to fetch GCP Agent Identity token: {e}")
        raise RuntimeError(f"Error fetching GCP Agent Identity token: {e}")

    # 2. Exchange GCP token for Microsoft Entra ID Access Token (Management Scope)
    entra_token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": gcp_token,
        "scope": "https://management.azure.com/.default",
    }
    
    try:
        resp = httpx.post(entra_token_url, data=payload, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
        azure_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3599)
    except Exception as e:
        logger.error(f"Failed to exchange token with Microsoft Entra ID: {e}")
        raise RuntimeError(f"Error exchanging token with Microsoft Entra: {e}")

    return {
        "gcp_agent_identity_jwt_assertion": gcp_token,
        "microsoft_entra_access_token": azure_token,
        "token_type": "Bearer",
        "scope": "https://management.azure.com/.default",
        "expires_in_seconds": expires_in,
        "federation_details": {
            "azure_tenant_id": tenant_id,
            "azure_client_id": client_id,
            "audience": "api://AzureADTokenExchange"
        }
    }


def execute_command_on_azure_vm(command: str) -> str:
    """Connects to the Azure Virtual Machine and executes a basic shell command.

    Args:
        command: The shell command to run (e.g., "ls", "pwd", "touch test.txt", "cp src.txt dest.txt").

    Returns:
        The command output or simulation details.
    """
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
    vm_name = os.environ.get("AZURE_VM_NAME")

    # Step 1: Call fetch_agent_identity_token_details to retrieve the Entra Access Token
    try:
        token_details = fetch_agent_identity_token_details()
        azure_token = token_details["microsoft_entra_access_token"]
    except Exception as e:
        return f"Error acquiring authentication credentials: {e}"

    if not all([subscription_id, resource_group, vm_name]):
        # Provide a fully detailed simulation if VM environment variables are not yet configured
        return (
            f"[SIMULATED VM ACCESS]\n"
            f"Successfully authenticated using Google Agent Identity -> Microsoft Entra federated credentials.\n"
            f"GCP Agent Identity Assertion Token: {token_details['gcp_agent_identity_jwt_assertion'][:30]}...[TRUNCATED]\n"
            f"Microsoft Entra Access Token: {azure_token[:30]}...[TRUNCATED]\n\n"
            f"API Call Details:\n"
            f"POST https://management.azure.com/subscriptions/your-subscription-id/resourceGroups/your-resource-group/providers/Microsoft.Compute/virtualMachines/your-vm-name/runCommand?api-version=2023-09-01\n"
            f"Authorization: Bearer <microsoft_entra_access_token>\n"
            f"Content-Type: application/json\n"
            f"Payload: {{ \"commandId\": \"RunShellScript\", \"script\": [ \"{command}\" ] }}\n\n"
            f"Simulated command execution output for `{command}`:\n"
            f"total 4\n-rw-r--r-- 1 azureuser staff 128 Jul 30 20:34 README.md\n"
            f"working_directory: /home/azureuser\n"
        )

    # Step 2: Invoke the Azure ARM Run Command API to run the command on the real VM
    run_command_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
        f"providers/Microsoft.Compute/virtualMachines/{vm_name}/runCommand?api-version=2023-09-01"
    )
    headers = {
        "Authorization": f"Bearer {azure_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "commandId": "RunShellScript",
        "script": [command]
    }

    try:
        resp = httpx.post(run_command_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        # The Run Command API returns command output inside value[0].message
        value_list = result.get("value", [])
        if value_list:
            return value_list[0].get("message", "Command completed with no output.")
        return str(result)
    except Exception as e:
        return f"Error executing command on Azure VM via API: {e}"
