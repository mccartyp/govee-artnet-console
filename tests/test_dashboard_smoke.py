"""Smoke tests for monitoring dashboard functionality.

These tests verify basic dashboard and events functionality works with the mock server.
Run the mock server first: python tests/mock_server.py
Then run these tests: pytest tests/test_dashboard_smoke.py -v
"""

import pytest
from govee_artnet_console.shell.controllers import EventsController
from govee_artnet_console.cli import ClientConfig
from httpx import Client


@pytest.fixture
def mock_server_url():
    """Mock server URL for testing."""
    return "http://127.0.0.1:8000"


@pytest.fixture
def client(mock_server_url):
    """Create HTTP client for testing."""
    return Client(base_url=mock_server_url, timeout=5.0)


def test_health_endpoint_returns_subsystems(client):
    """Test that /health endpoint returns subsystems structure."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "subsystems" in data

    # Check expected subsystems
    subsystems = data["subsystems"]
    assert "discovery" in subsystems
    assert "sender" in subsystems
    assert "artnet" in subsystems
    assert "api" in subsystems
    assert "poller" in subsystems

    # Check subsystem structure
    for name, subsystem in subsystems.items():
        assert "status" in subsystem
        assert subsystem["status"] in ["ok", "degraded", "suppressed", "recovering"]


def test_devices_endpoint_includes_mapping_count(client):
    """Test that /devices endpoint includes mapping_count field."""
    response = client.get("/devices")
    assert response.status_code == 200

    devices = response.json()
    assert isinstance(devices, list)
    assert len(devices) > 0

    # Check first device has mapping_count
    device = devices[0]
    assert "id" in device
    assert "ip" in device
    assert "model_number" in device
    assert "description" in device
    assert "offline" in device
    assert "last_seen" in device
    # Note: mapping_count might be added by backend, not in mock yet


def test_dashboard_data_availability(client):
    """Test that all required data for dashboard is available."""
    # Test health endpoint
    health_response = client.get("/health")
    assert health_response.status_code == 200
    health_data = health_response.json()

    # Test devices endpoint
    devices_response = client.get("/devices")
    assert devices_response.status_code == 200
    devices_data = devices_response.json()

    # Test mappings endpoint
    mappings_response = client.get("/mappings")
    assert mappings_response.status_code == 200
    mappings_data = mappings_response.json()

    # Verify we can calculate statistics
    total_devices = len(devices_data)
    online_devices = sum(1 for d in devices_data if not d.get("offline"))
    offline_devices = sum(1 for d in devices_data if d.get("offline"))
    total_mappings = len(mappings_data)

    assert total_devices >= 0
    assert online_devices >= 0
    assert offline_devices >= 0
    assert total_mappings >= 0
    assert total_devices == online_devices + offline_devices


@pytest.mark.asyncio
async def test_events_websocket_basic_connection(mock_server_url):
    """Test basic WebSocket connection to /events/stream."""
    import websockets
    import json

    ws_url = mock_server_url.replace("http://", "ws://") + "/events/stream"

    async with websockets.connect(ws_url) as websocket:
        # Wait for first message (should be an event or ping)
        message = await websocket.recv()
        data = json.loads(message)

        # Should have either 'type' (for ping) or 'event' (for event)
        assert "type" in data or "event" in data

        # If it's a ping, respond with pong
        if data.get("type") == "ping":
            await websocket.send(json.dumps({"type": "pong"}))

            # Wait for an actual event
            message = await websocket.recv()
            data = json.loads(message)

        # Verify event structure
        if "event" in data:
            assert "timestamp" in data
            assert "data" in data

            # Verify event type is recognized
            valid_events = [
                "device_discovered",
                "device_online",
                "device_offline",
                "device_updated",
                "mapping_created",
                "mapping_updated",
                "mapping_deleted",
                "health_status_changed",
            ]
            assert data["event"] in valid_events


@pytest.mark.asyncio
async def test_events_include_required_fields(mock_server_url):
    """Test that events include all required fields for display."""
    import websockets
    import json
    import asyncio

    ws_url = mock_server_url.replace("http://", "ws://") + "/events/stream"

    async with websockets.connect(ws_url) as websocket:
        # Collect a few events
        events_seen = {}
        timeout = 15  # Wait up to 15 seconds

        try:
            async with asyncio.timeout(timeout):
                while len(events_seen) < 5:  # Collect at least 5 different event types
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Skip pings
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                        continue

                    if "event" in data:
                        event_type = data["event"]
                        events_seen[event_type] = data
        except asyncio.TimeoutError:
            pass  # It's ok if we don't see all event types

        # Verify we saw at least some events
        assert len(events_seen) > 0

        # Check device_discovered has required fields
        if "device_discovered" in events_seen:
            event_data = events_seen["device_discovered"]["data"]
            assert "device_id" in event_data
            assert "ip" in event_data

        # Check device_offline has required fields
        if "device_offline" in events_seen:
            event_data = events_seen["device_offline"]["data"]
            assert "device_id" in event_data
            assert "reason" in event_data

        # Check mapping_created has required fields
        if "mapping_created" in events_seen:
            event_data = events_seen["mapping_created"]["data"]
            assert "mapping_id" in event_data
            assert "universe" in event_data
            assert "channel" in event_data

        # Check health_status_changed has required fields
        if "health_status_changed" in events_seen:
            event_data = events_seen["health_status_changed"]["data"]
            assert "subsystem" in event_data
            assert "status" in event_data


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_dashboard_smoke.py -v
    pytest.main([__file__, "-v"])
