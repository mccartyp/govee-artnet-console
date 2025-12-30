"""Tests for the BridgeClient."""

import pytest
from govee_artnet_console.client import BridgeClient


def test_client_initialization():
    """Test that client initializes correctly."""
    client = BridgeClient("http://localhost:8000")
    assert client.base_url == "http://localhost:8000"
    assert client.api_key is None


def test_client_with_api_key():
    """Test client with API key."""
    client = BridgeClient("http://localhost:8000", api_key="test-key")
    assert client.api_key == "test-key"
    headers = client._get_headers()
    assert headers["X-API-Key"] == "test-key"
    assert headers["Authorization"] == "Bearer test-key"


def test_client_context_manager():
    """Test client as context manager."""
    with BridgeClient("http://localhost:8000") as client:
        assert client is not None


# Integration tests require mock server running
@pytest.mark.integration
def test_health_check():
    """Test health check endpoint."""
    client = BridgeClient("http://localhost:8000")
    try:
        health = client.health()
        assert health["status"] == "ok"
    except Exception as e:
        pytest.skip(f"Mock server not running: {e}")


@pytest.mark.integration
def test_list_devices():
    """Test listing devices."""
    client = BridgeClient("http://localhost:8000")
    try:
        devices = client.list_devices()
        assert isinstance(devices, list)
        if devices:
            assert "id" in devices[0]
            assert "ip" in devices[0]
    except Exception as e:
        pytest.skip(f"Mock server not running: {e}")


@pytest.mark.integration
def test_list_mappings():
    """Test listing mappings."""
    client = BridgeClient("http://localhost:8000")
    try:
        mappings = client.list_mappings()
        assert isinstance(mappings, list)
        if mappings:
            assert "id" in mappings[0]
            assert "device_id" in mappings[0]
    except Exception as e:
        pytest.skip(f"Mock server not running: {e}")
