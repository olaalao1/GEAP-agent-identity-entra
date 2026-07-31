import os
import httpx
import logging
from token_agent.identity import fetch_gcp_oidc_token

logger = logging.getLogger(__name__)

def get_azure_secret(secret_name: str) -> str:
    """Retrieves a secure configuration secret from Azure Key Vault using federated credentials.

    Args:
        secret_name: The name of the secret to retrieve (e.g., "my-database-password").

    Returns:
        The secret value string, or an error message if retrieval fails.
    """
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    vault_name = os.environ.get("AZURE_KEY_VAULT_NAME")
    
    if not all([tenant_id, client_id, vault_name]):
        return "Error: Azure Federation environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_KEY_VAULT_NAME) are not fully configured on the agent container."
        
    # Step 1: Request GCP Agent Identity token from the local metadata server
    try:
        gcp_token = fetch_gcp_oidc_token(audience="api://AzureADTokenExchange")
    except Exception as e:
        return f"Error retrieving GCP Agent Identity token: {e}"
        
    # Step 2: Exchange GCP token for Microsoft Entra ID Access Token
    entra_token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": gcp_token,
        "scope": "https://vault.azure.net/.default",
    }
    
    try:
        resp = httpx.post(entra_token_url, data=payload, timeout=10)
        resp.raise_for_status()
        azure_token = resp.json()["access_token"]
    except Exception as e:
        return f"Error exchanging token with Microsoft Entra ID: {e}"
        
    # Step 3: Fetch the secret from Azure Key Vault using the obtained Entra token
    secret_url = f"https://{vault_name}.vault.azure.net/secrets/{secret_name}?api-version=7.4"
    kv_headers = {"Authorization": f"Bearer {azure_token}"}
    
    try:
        resp = httpx.get(secret_url, headers=kv_headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["value"]
    except Exception as e:
        return f"Error retrieving secret from Azure Key Vault: {e}"
