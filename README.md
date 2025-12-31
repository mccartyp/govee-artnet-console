# Govee ArtNet Console

Interactive CLI console for managing Govee devices via the [Govee ArtNet LAN Bridge](https://github.com/mccartyp/govee-artnet-lan-bridge).

## Overview

`govee-artnet-console` is a standalone command-line tool that provides an interactive shell interface for controlling and monitoring Govee smart lighting devices through the Govee ArtNet LAN Bridge REST API. It's designed as a thin client that can connect to local or remote bridge instances.

## Features

### Core Capabilities
- **Interactive Shell**: Full-featured command shell with tab completion, history, and rich formatting
- **Device Management**: List, configure, enable/disable, and control Govee devices
- **DMX Mapping**: Create and manage ArtNet to Govee device mappings
- **Real-time Monitoring**: Comprehensive dashboards with health monitoring, device status, and statistics
- **Event Streaming**: WebSocket-based real-time event notifications with background alerts
- **Log Streaming**: Real-time log viewing with filtering and search capabilities
- **Multi-Server Support**: Connect to multiple bridge instances with per-server configuration

### Monitoring Dashboard Features
- **📊 Comprehensive Dashboard**: System overview with health, devices, and statistics in one view
  - Statistics summary cards (Total Devices, Online, Offline, Mappings)
  - System health monitoring (discovery, sender, artnet, api, poller subsystems)
  - Device table with real-time status (🟢 Online, 🔴 Offline, ⚪ Stale)
  - Relative time formatting ("2m ago", "5h ago")

- **🔔 Real-Time Event Notifications**: Background WebSocket event stream
  - Device events: discovered, online, offline, updated
  - Mapping events: created, updated, deleted
  - Health events: subsystem status changes
  - Console notifications with colored bubbles (🔵 🟢 🔴 ⚙️)
  - Detailed event stream viewer with filtering

- **👁️ Watch Mode**: Live updating dashboards with configurable refresh intervals
  - `watch dashboard` - Auto-updating comprehensive view
  - `watch devices` - Real-time device status monitoring
  - Keyboard controls for speed adjustment (+/-)

### Advanced Features
- **WebSocket Support**: Dual WebSocket connections for logs and events
- **Authentication**: API key and Bearer token support for secure connections
- **Multiple Output Formats**: JSON, YAML, and formatted tables
- **Bookmarks & Aliases**: Save device IDs and command shortcuts
- **Command History**: Persistent history with reverse search (Ctrl+R)
- **Pagination**: Automatic output pagination for long listings

## Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/mccartyp/govee-artnet-console.git
cd govee-artnet-console
pip install .

# Or install in development mode
pip install -e .
```

See [INSTALLATION.md](docs/INSTALLATION.md) for detailed installation instructions including Debian packages.

### Basic Usage

```bash
# Start interactive shell (connects to localhost:8000 by default)
govee-artnet-console

# Connect to remote bridge
govee-artnet-console --server-url http://192.168.1.100:8000

# Use API key authentication
govee-artnet-console --api-key YOUR_API_KEY

# Or use environment variable
export GOVEE_ARTNET_API_KEY=your-api-key
govee-artnet-console

# Run single command without shell
govee-artnet-console devices list --output table
```

### First Steps

Once in the shell:

```
govee> monitor dashboard               # View comprehensive system dashboard
govee> monitor devices                 # List all devices with detailed status
govee> devices list                    # List all discovered devices
govee> mappings create --device-id AA:BB:CC:DD:EE:FF:11:22 \
                        --universe 0 --template RGB --start-channel 1
govee> logs events                     # View real-time event stream
govee> logs tail                       # Stream application logs in real-time
govee> watch dashboard                 # Live updating dashboard (updates every 5s)
govee> help                            # Show all available commands
```

### Dashboard & Monitoring Commands

```bash
# Static snapshots (execute once)
monitor dashboard                      # Comprehensive dashboard with health + devices
monitor devices                        # Detailed device table with all fields
monitor stats                          # System statistics

# Live updating views (auto-refresh)
watch dashboard                        # Live dashboard (Esc/q to exit, +/- to adjust speed)
watch devices                          # Live device monitor

# Event streaming
logs events                            # Real-time event notifications (device, mapping, health)
logs events --type device              # Filter by event type (device|mapping|health)
```

**Note:** Event notifications appear automatically in the background while you work. Look for colored bubble indicators (🔵 🟢 🔴 ⚙️) in the console output!

## Configuration

Configuration is stored at `~/.govee_artnet_console/config.yaml`:

```yaml
# Server profiles
servers:
  default:
    url: http://localhost:8000
    name: "Local Bridge"
    api_key: null

  remote:
    url: http://192.168.1.100:8000
    name: "Living Room Bridge"
    api_key: "your-api-key-here"

# Active server
active_server: default

# Shell preferences
shell:
  history_size: 1000
  auto_refresh_interval: 2
  default_output_format: table

# Device bookmarks
bookmarks:
  bedroom: "AA:BB:CC:DD:EE:FF:11:22"
  living_room: "11:22:33:44:55:66:77:88"

# Command aliases
aliases:
  ls: "devices list"
  status: "monitor dashboard"
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed installation instructions
- [Usage Guide](docs/USAGE.md) - Complete command reference and examples
- [Govee ArtNet Bridge](https://github.com/mccartyp/govee-artnet-lan-bridge) - Server component

## Requirements

- Python 3.10 or higher
- Govee ArtNet LAN Bridge server running
- Network connectivity to bridge server

## Architecture

```
┌─────────────────────────┐
│  govee-artnet-console   │  ← This package (CLI client)
│  (Interactive Shell)    │
└────────────┬────────────┘
             │ HTTP/WebSocket
             │ (REST API)
┌────────────▼────────────┐
│ govee-artnet-lan-bridge │  ← Bridge server
│   (API Server)          │
└────────────┬────────────┘
             │ Govee LAN Protocol
             │ ArtNet (UDP)
┌────────────▼────────────┐
│   Govee Smart Devices   │
│ (Lights, Strips, etc.)  │
└─────────────────────────┘
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/test_client.py

# Start mock server for integration tests
python tests/mock_server.py &

# Run integration tests
pytest tests/ -m integration
```

### Building Debian Package

```bash
# Build .deb package
make deb

# Install locally
make install

# Clean build artifacts
make clean
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Author

Patrick McCarty (mccartyp@gmail.com)

## Related Projects

- [govee-artnet-lan-bridge](https://github.com/mccartyp/govee-artnet-lan-bridge) - Bridge server for ArtNet to Govee LAN protocol
