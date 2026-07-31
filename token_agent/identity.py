import httpx
import logging

logger = logging.getLogger(__name__)

def fetch_gcp_oidc_token(audience: str = "api://AzureADTokenExchange") -> str:
    """Queries the local Google Metadata Server to retrieve the Agent's OIDC ID token.

    Args:
        audience: The target audience for the OIDC assertion.

    Returns:
        The raw cryptographically-signed GCP JWT assertion string.
    """
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
    headers = {"Metadata-Flavor": "Google"}
    params = {"audience": audience}

    try:
        logger.info(f"Fetching OIDC token from GCP metadata server (Audience: {audience})...")
        response = httpx.get(metadata_url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except httpx.HTTPStatusError as e:
        logger.error(f"Metadata server returned error: {e.response.status_code} - {e.response.text}")
        raise RuntimeError("GCP Metadata server failed to supply identity token") from e
    except httpx.RequestError as e:
        logger.error(f"Metadata server unreachable: {e}")
        raise RuntimeError("Metadata server is only accessible from deployed GCP runtimes") from e
