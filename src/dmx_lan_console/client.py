"""Bridge API client for dmx-lan-console."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Callable, Optional

import httpx
import websockets
from websockets.client import WebSocketClientProtocol


class BridgeClient:
    """Client for interacting with the DMX LAN Bridge API."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize the bridge client.

        Args:
            base_url: Base URL of the bridge API (e.g., http://127.0.0.1:8000)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers with authentication if configured."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def client(self) -> httpx.Client:
        """Get or create synchronous HTTP client."""
        if self._client is None:
            limits = httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            )
            transport = httpx.HTTPTransport(retries=3, limits=limits)
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=self.timeout,
                transport=transport,
                follow_redirects=True,
            )
        return self._client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create asynchronous HTTP client."""
        if self._async_client is None:
            limits = httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            )
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=self.timeout,
                limits=limits,
                follow_redirects=True,
            )
        return self._async_client

    def close(self) -> None:
        """Close HTTP clients."""
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            asyncio.create_task(self._async_client.aclose())
            self._async_client = None

    async def aclose(self) -> None:
        """Close HTTP clients asynchronously."""
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self) -> BridgeClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    async def __aenter__(self) -> BridgeClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.aclose()

    # Health and status endpoints

    def health(self) -> dict[str, Any]:
        """Check API health."""
        response = self.client.get("/health")
        response.raise_for_status()
        return response.json()

    def status(self) -> dict[str, Any]:
        """Get API status and metrics."""
        response = self.client.get("/status")
        response.raise_for_status()
        return response.json()

    # Device endpoints

    def list_devices(self) -> list[dict[str, Any]]:
        """List all devices."""
        response = self.client.get("/devices")
        response.raise_for_status()
        return response.json()

    def get_device(self, device_id: str) -> dict[str, Any]:
        """Get a specific device by ID."""
        response = self.client.get(f"/devices/{device_id}")
        response.raise_for_status()
        return response.json()

    def create_device(self, device_data: dict[str, Any]) -> dict[str, Any]:
        """Create a manual device."""
        response = self.client.post("/devices", json=device_data)
        response.raise_for_status()
        return response.json()

    def update_device(self, device_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a device."""
        response = self.client.patch(f"/devices/{device_id}", json=updates)
        response.raise_for_status()
        return response.json()

    def send_device_test(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a test payload to a device."""
        response = self.client.post(f"/devices/{device_id}/test", json={"payload": payload})
        response.raise_for_status()
        return response.json()

    def send_device_command(
        self, device_id: str, command_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a command to a device."""
        response = self.client.post(f"/devices/{device_id}/command", json=command_data)
        response.raise_for_status()
        return response.json()

    # Mapping endpoints

    def list_mappings(self) -> list[dict[str, Any]]:
        """List all DMX mappings."""
        response = self.client.get("/mappings")
        response.raise_for_status()
        return response.json()

    def get_mapping(self, mapping_id: int) -> dict[str, Any]:
        """Get a specific mapping by ID."""
        response = self.client.get(f"/mappings/{mapping_id}")
        response.raise_for_status()
        return response.json()

    def create_mapping(self, mapping_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new mapping."""
        response = self.client.post("/mappings", json=mapping_data)
        response.raise_for_status()
        return response.json()

    def update_mapping(self, mapping_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a mapping."""
        response = self.client.put(f"/mappings/{mapping_id}", json=updates)
        response.raise_for_status()
        return response.json()

    def delete_mapping(self, mapping_id: int) -> None:
        """Delete a mapping."""
        response = self.client.delete(f"/mappings/{mapping_id}")
        response.raise_for_status()

    def get_channel_map(self) -> dict[str, Any]:
        """Get the DMX channel map."""
        response = self.client.get("/channel-map")
        response.raise_for_status()
        return response.json()

    # Log endpoints

    def get_logs(
        self,
        level: Optional[str] = None,
        logger: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> dict[str, Any]:
        """Get logs with optional filtering."""
        params = {}
        if level:
            params["level"] = level
        if logger:
            params["logger"] = logger
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        response = self.client.get("/logs", params=params)
        response.raise_for_status()
        return response.json()

    def search_logs(
        self,
        pattern: str,
        case_sensitive: bool = False,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        """Search logs for a pattern."""
        params = {"pattern": pattern, "case_sensitive": case_sensitive}
        if limit:
            params["limit"] = limit

        response = self.client.get("/logs/search", params=params)
        response.raise_for_status()
        return response.json()

    # System endpoints

    def reload(self) -> dict[str, Any]:
        """Trigger a configuration reload."""
        response = self.client.post("/reload")
        response.raise_for_status()
        return response.json()

    # WebSocket connections

    def _get_ws_url(self, path: str) -> str:
        """Convert HTTP URL to WebSocket URL."""
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_base}{path}"

    def _get_ws_headers(self) -> list[tuple[str, str]]:
        """Get WebSocket headers with authentication."""
        headers = []
        if self.api_key:
            headers.append(("X-API-Key", self.api_key))
            headers.append(("Authorization", f"Bearer {self.api_key}"))
        return headers

    async def stream_logs(
        self,
        level: Optional[str] = None,
        logger: Optional[str] = None,
        callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream logs via WebSocket.

        Args:
            level: Optional log level filter
            logger: Optional logger name filter
            callback: Optional callback function for each log entry

        Yields:
            Log entry dictionaries
        """
        url = self._get_ws_url("/logs/stream")
        params = []
        if level:
            params.append(f"level={level}")
        if logger:
            params.append(f"logger={logger}")
        if params:
            url += "?" + "&".join(params)

        async with websockets.connect(
            url, additional_headers=self._get_ws_headers()
        ) as websocket:
            async for message in websocket:
                try:
                    log_entry = json.loads(message)
                    if callback:
                        callback(log_entry)
                    yield log_entry
                except json.JSONDecodeError:
                    continue

    async def stream_events(
        self, callback: Optional[Callable[[dict[str, Any]], None]] = None
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream system events via WebSocket.

        Args:
            callback: Optional callback function for each event

        Yields:
            Event dictionaries
        """
        url = self._get_ws_url("/events/stream")

        async with websockets.connect(
            url, additional_headers=self._get_ws_headers()
        ) as websocket:
            async for message in websocket:
                try:
                    event = json.loads(message)
                    if callback:
                        callback(event)
                    yield event
                except json.JSONDecodeError:
                    continue

    async def connect_log_stream(
        self,
        level: Optional[str] = None,
        logger: Optional[str] = None,
    ) -> WebSocketClientProtocol:
        """
        Connect to log stream WebSocket.

        Args:
            level: Optional log level filter
            logger: Optional logger name filter

        Returns:
            WebSocket connection
        """
        url = self._get_ws_url("/logs/stream")
        params = []
        if level:
            params.append(f"level={level}")
        if logger:
            params.append(f"logger={logger}")
        if params:
            url += "?" + "&".join(params)

        return await websockets.connect(url, additional_headers=self._get_ws_headers())

    async def connect_event_stream(self) -> WebSocketClientProtocol:
        """
        Connect to event stream WebSocket.

        Returns:
            WebSocket connection
        """
        url = self._get_ws_url("/events/stream")
        return await websockets.connect(url, additional_headers=self._get_ws_headers())
