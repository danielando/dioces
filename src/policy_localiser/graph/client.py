import logging
import time

import requests

from .auth import GraphAuth

logger = logging.getLogger(__name__)


class GraphClient:
    """Low-level HTTP client for Microsoft Graph API with retry logic."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, auth: GraphAuth):
        self._auth = auth
        self._session = requests.Session()

    def _headers(self, content_type: str = "application/json") -> dict:
        return {
            "Authorization": f"Bearer {self._auth.get_token()}",
            "Content-Type": content_type,
        }

    def get(self, path: str, params: dict = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def get_binary(self, path: str) -> bytes:
        """GET request that returns raw bytes (for file downloads)."""
        resp = self._request("GET", path)
        return resp.content

    def post(self, path: str, json: dict = None) -> requests.Response:
        return self._request("POST", path, json=json)

    def put_binary(
        self, path: str, data: bytes, content_type: str
    ) -> requests.Response:
        return self._request(
            "PUT", path, data=data, headers=self._headers(content_type)
        )

    def _request(
        self, method: str, path: str, max_retries: int = 3, **kwargs
    ) -> requests.Response:
        url = f"{self.BASE_URL}{path}" if path.startswith("/") else path
        if "headers" not in kwargs:
            kwargs["headers"] = self._headers()

        for attempt in range(max_retries):
            resp = self._session.request(method, url, **kwargs)

            if resp.status_code == 429:  # Throttled
                retry_after = int(resp.headers.get("Retry-After", 5))
                logger.warning(f"Throttled by Graph API, retrying in {retry_after}s")
                time.sleep(retry_after)
                continue

            if resp.status_code >= 500 and attempt < max_retries - 1:
                wait = 2**attempt
                logger.warning(f"Server error {resp.status_code}, retrying in {wait}s")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp

        resp.raise_for_status()
        return resp
