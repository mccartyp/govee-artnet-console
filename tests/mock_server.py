"""Mock Govee ArtNet Bridge API server for testing."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Header, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# Mock data
FAKE_DEVICES = [
    {
        "id": "AA:BB:CC:DD:EE:FF:11:22",
        "ip": "192.168.1.100",
        "model_number": "H6160",
        "device_type": "led_strip",
        "description": "Living Room Strip",
        "enabled": True,
        "manual": False,
        "discovered": True,
        "configured": True,
        "offline": False,
        "stale": False,
        "capabilities": {
            "color": True,
            "brightness": True,
            "temperature": True,
        },
        "led_count": 300,
        "length_meters": 5.0,
        "segment_count": 1,
        "last_seen": "2025-12-30T10:00:00Z",
        "first_seen": "2025-12-29T08:00:00Z",
    },
    {
        "id": "11:22:33:44:55:66:77:88",
        "ip": "192.168.1.101",
        "model_number": "H6199",
        "device_type": "light_bar",
        "description": "Bedroom Light Bar",
        "enabled": True,
        "manual": False,
        "discovered": True,
        "configured": False,
        "offline": False,
        "stale": False,
        "capabilities": {
            "color": True,
            "brightness": True,
            "temperature": False,
        },
        "led_count": 50,
        "length_meters": 1.0,
        "segment_count": 5,
        "last_seen": "2025-12-30T10:00:00Z",
        "first_seen": "2025-12-30T09:00:00Z",
    },
    {
        "id": "99:88:77:66:55:44:33:22",
        "ip": "192.168.1.102",
        "model_number": "H6182",
        "device_type": "led_strip",
        "description": "Office Strip",
        "enabled": False,
        "manual": True,
        "discovered": False,
        "configured": True,
        "offline": True,
        "stale": True,
        "capabilities": {
            "color": True,
            "brightness": True,
            "temperature": True,
        },
        "led_count": 150,
        "length_meters": 2.5,
        "segment_count": 1,
        "last_seen": "2025-12-29T15:00:00Z",
        "first_seen": "2025-12-28T10:00:00Z",
    },
]

FAKE_MAPPINGS = [
    {
        "id": 1,
        "device_id": "AA:BB:CC:DD:EE:FF:11:22",
        "universe": 0,
        "channel": 1,
        "length": 3,
        "mapping_type": "range",
        "fields": ["r", "g", "b"],
    },
    {
        "id": 2,
        "device_id": "11:22:33:44:55:66:77:88",
        "universe": 0,
        "channel": 10,
        "length": 4,
        "mapping_type": "range",
        "fields": ["r", "g", "b", "w"],
    },
    {
        "id": 3,
        "device_id": "AA:BB:CC:DD:EE:FF:11:22",
        "universe": 1,
        "channel": 1,
        "length": 1,
        "mapping_type": "discrete",
        "field": "brightness",
    },
]

# Mock logs
FAKE_LOGS = [
    {
        "timestamp": "2025-12-30T10:00:00Z",
        "level": "INFO",
        "logger": "artnet",
        "message": "ArtNet packet received on universe 0",
    },
    {
        "timestamp": "2025-12-30T10:00:01Z",
        "level": "DEBUG",
        "logger": "devices",
        "message": "Device AA:BB:CC:DD:EE:FF:11:22 state updated",
    },
    {
        "timestamp": "2025-12-30T10:00:02Z",
        "level": "WARNING",
        "logger": "queue",
        "message": "Queue depth exceeding threshold: 150",
    },
    {
        "timestamp": "2025-12-30T10:00:03Z",
        "level": "ERROR",
        "logger": "sender",
        "message": "Failed to send command to device 99:88:77:66:55:44:33:22: timeout",
    },
]


# Pydantic models
class DeviceCreate(BaseModel):
    id: str
    ip: str
    model_number: Optional[str] = None
    device_type: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = True
    capabilities: Optional[dict[str, bool]] = None


class DeviceUpdate(BaseModel):
    ip: Optional[str] = None
    model_number: Optional[str] = None
    device_type: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    capabilities: Optional[dict[str, bool]] = None


class MappingCreate(BaseModel):
    device_id: str
    universe: int
    channel: Optional[int] = None
    start_channel: Optional[int] = None
    length: Optional[int] = 1
    mapping_type: Optional[str] = "range"
    template: Optional[str] = None
    field: Optional[str] = None
    allow_overlap: Optional[bool] = False


class MappingUpdate(BaseModel):
    device_id: Optional[str] = None
    universe: Optional[int] = None
    channel: Optional[int] = None
    length: Optional[int] = None
    mapping_type: Optional[str] = None
    field: Optional[str] = None
    allow_overlap: Optional[bool] = None


# Create FastAPI app
app = FastAPI(title="Mock Govee ArtNet Bridge API")

# Counter for generating mapping IDs
next_mapping_id = 4


# Authentication middleware (optional check)
def check_auth(x_api_key: Optional[str] = Header(None)):
    """Check API key if provided (mock - always allows)."""
    # In mock mode, we accept any API key or no API key
    pass


# Health and Status endpoints
@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/status")
def status():
    """Status and metrics endpoint."""
    return {
        "devices": {
            "total": len(FAKE_DEVICES),
            "online": sum(1 for d in FAKE_DEVICES if not d["offline"]),
            "enabled": sum(1 for d in FAKE_DEVICES if d["enabled"]),
        },
        "mappings": {"total": len(FAKE_MAPPINGS)},
        "artnet": {
            "packets_received": 1234,
            "last_packet_time": "2025-12-30T10:00:00Z",
        },
        "queue": {"depth": 5, "max_depth": 1000},
        "discovery": {"running": True, "last_scan": "2025-12-30T09:00:00Z"},
    }


# Device endpoints
@app.get("/devices")
def list_devices():
    """List all devices."""
    return FAKE_DEVICES


@app.get("/devices/{device_id}")
def get_device(device_id: str):
    """Get a specific device."""
    device = next((d for d in FAKE_DEVICES if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.post("/devices")
def create_device(device: DeviceCreate):
    """Create a manual device."""
    # Check if device already exists
    if any(d["id"] == device.id for d in FAKE_DEVICES):
        raise HTTPException(status_code=400, detail="Device already exists")

    new_device = {
        "id": device.id,
        "ip": device.ip,
        "model_number": device.model_number or "Unknown",
        "device_type": device.device_type or "unknown",
        "description": device.description or "",
        "enabled": device.enabled,
        "manual": True,
        "discovered": False,
        "configured": True,
        "offline": False,
        "stale": False,
        "capabilities": device.capabilities or {},
        "led_count": None,
        "length_meters": None,
        "segment_count": None,
        "last_seen": datetime.utcnow().isoformat() + "Z",
        "first_seen": datetime.utcnow().isoformat() + "Z",
    }
    FAKE_DEVICES.append(new_device)
    return new_device


@app.patch("/devices/{device_id}")
def update_device(device_id: str, updates: DeviceUpdate):
    """Update a device."""
    device = next((d for d in FAKE_DEVICES if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Apply updates
    if updates.ip is not None:
        device["ip"] = updates.ip
    if updates.model_number is not None:
        device["model_number"] = updates.model_number
    if updates.device_type is not None:
        device["device_type"] = updates.device_type
    if updates.description is not None:
        device["description"] = updates.description
    if updates.enabled is not None:
        device["enabled"] = updates.enabled
    if updates.capabilities is not None:
        device["capabilities"] = updates.capabilities

    return device


@app.post("/devices/{device_id}/test")
def test_device(device_id: str, payload: dict[str, Any]):
    """Send test payload to device."""
    device = next((d for d in FAKE_DEVICES if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"status": "queued", "device_id": device_id, "payload": payload.get("payload")}


@app.post("/devices/{device_id}/command")
def command_device(device_id: str, command: dict[str, Any]):
    """Send command to device."""
    device = next((d for d in FAKE_DEVICES if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"status": "queued", "device_id": device_id, "command": command}


# Mapping endpoints
@app.get("/mappings")
def list_mappings():
    """List all mappings."""
    return FAKE_MAPPINGS


@app.get("/mappings/{mapping_id}")
def get_mapping(mapping_id: int):
    """Get a specific mapping."""
    mapping = next((m for m in FAKE_MAPPINGS if m["id"] == mapping_id), None)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@app.post("/mappings")
def create_mapping(mapping: MappingCreate):
    """Create a new mapping."""
    global next_mapping_id

    # Expand template if provided
    if mapping.template:
        # Simple template expansion
        template_fields = {
            "rgb": ["r", "g", "b"],
            "rgbw": ["r", "g", "b", "w"],
            "brightness_rgb": ["brightness", "r", "g", "b"],
        }
        fields = template_fields.get(mapping.template, [])
        channel = mapping.start_channel or mapping.channel or 1
        length = len(fields)
    else:
        channel = mapping.channel or mapping.start_channel or 1
        length = mapping.length or 1
        fields = [mapping.field] if mapping.mapping_type == "discrete" else []

    new_mapping = {
        "id": next_mapping_id,
        "device_id": mapping.device_id,
        "universe": mapping.universe,
        "channel": channel,
        "length": length,
        "mapping_type": mapping.mapping_type,
    }

    if mapping.mapping_type == "discrete" and mapping.field:
        new_mapping["field"] = mapping.field
    elif fields:
        new_mapping["fields"] = fields

    FAKE_MAPPINGS.append(new_mapping)
    next_mapping_id += 1

    return new_mapping


@app.put("/mappings/{mapping_id}")
def update_mapping(mapping_id: int, updates: MappingUpdate):
    """Update a mapping."""
    mapping = next((m for m in FAKE_MAPPINGS if m["id"] == mapping_id), None)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    # Apply updates
    if updates.device_id is not None:
        mapping["device_id"] = updates.device_id
    if updates.universe is not None:
        mapping["universe"] = updates.universe
    if updates.channel is not None:
        mapping["channel"] = updates.channel
    if updates.length is not None:
        mapping["length"] = updates.length
    if updates.mapping_type is not None:
        mapping["mapping_type"] = updates.mapping_type
    if updates.field is not None:
        mapping["field"] = updates.field

    return mapping


@app.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: int):
    """Delete a mapping."""
    global FAKE_MAPPINGS
    mapping = next((m for m in FAKE_MAPPINGS if m["id"] == mapping_id), None)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    FAKE_MAPPINGS = [m for m in FAKE_MAPPINGS if m["id"] != mapping_id]
    return JSONResponse(status_code=204, content=None)


@app.get("/channel-map")
def get_channel_map():
    """Get channel map."""
    channel_map = {}
    for mapping in FAKE_MAPPINGS:
        universe = str(mapping["universe"])
        if universe not in channel_map:
            channel_map[universe] = []
        channel_map[universe].append({
            "device_id": mapping["device_id"],
            "channel": mapping["channel"],
            "length": mapping["length"],
            "mapping_id": mapping["id"],
        })
    return channel_map


# Log endpoints
@app.get("/logs")
def get_logs(level: Optional[str] = None, logger: Optional[str] = None, limit: Optional[int] = 50, offset: Optional[int] = 0):
    """Get logs with filtering."""
    logs = FAKE_LOGS

    if level:
        logs = [log for log in logs if log["level"] == level]
    if logger:
        logs = [log for log in logs if log["logger"] == logger]

    total = len(logs)
    logs = logs[offset : offset + limit]

    return {"logs": logs, "total": total, "limit": limit, "offset": offset}


@app.get("/logs/search")
def search_logs(pattern: str, case_sensitive: bool = False, limit: Optional[int] = 100):
    """Search logs."""
    import re

    flags = 0 if case_sensitive else re.IGNORECASE
    matches = []

    for log in FAKE_LOGS:
        if re.search(pattern, log["message"], flags):
            matches.append(log)
            if len(matches) >= limit:
                break

    return {"logs": matches, "total": len(matches), "pattern": pattern}


# System endpoints
@app.post("/reload")
def reload_config():
    """Reload configuration."""
    return {"status": "reloaded", "timestamp": datetime.utcnow().isoformat() + "Z"}


# WebSocket endpoints
@app.websocket("/logs/stream")
async def websocket_logs(websocket: WebSocket, level: Optional[str] = None, logger: Optional[str] = None):
    """Stream logs via WebSocket."""
    await websocket.accept()

    try:
        # Send initial logs
        for log in FAKE_LOGS:
            if level and log["level"] != level:
                continue
            if logger and log["logger"] != logger:
                continue
            await websocket.send_json(log)
            await asyncio.sleep(0.1)

        # Send periodic updates
        counter = 0
        while True:
            await asyncio.sleep(2)
            new_log = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "logger": "artnet",
                "message": f"Periodic update {counter}",
            }
            counter += 1
            await websocket.send_json(new_log)
    except Exception:
        pass


@app.websocket("/events/stream")
async def websocket_events(websocket: WebSocket):
    """Stream events via WebSocket."""
    await websocket.accept()

    try:
        # Send periodic events
        counter = 0
        while True:
            await asyncio.sleep(3)
            event = {
                "event": "device_updated",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "device_id": "AA:BB:CC:DD:EE:FF:11:22",
                    "field": "brightness",
                    "value": 128 + (counter % 128),
                },
            }
            counter += 1
            await websocket.send_json(event)
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
