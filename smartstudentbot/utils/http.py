import httpx
from typing import Optional

# Define a default timeout configuration.
# 5 seconds total, 3 seconds to connect.
DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=3.0)

def get_client(timeout: Optional[httpx.Timeout] = None) -> httpx.AsyncClient:
    """
    Returns a pre-configured asynchronous HTTP client.

    Args:
        timeout: An optional httpx.Timeout object. Defaults to DEFAULT_TIMEOUT.

    Returns:
        An instance of httpx.AsyncClient.
    """
    return httpx.AsyncClient(
        timeout=timeout or DEFAULT_TIMEOUT,
        follow_redirects=True
    )

# Example of how to use it:
#
# async def fetch_some_data():
#     async with get_client() as client:
#         response = await client.get("https://example.com")
#         return response.json()
