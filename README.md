# DMX LAN Console

[![Latest Release](https://img.shields.io/github/v/release/mccartyp/dmx-lan-console)](https://github.com/mccartyp/dmx-lan-console/releases/latest)
[![Download DEB](https://img.shields.io/badge/download-.deb-blue)](https://github.com/mccartyp/dmx-lan-console/releases/latest)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads())
[![License](https://img.shields.io/github/license/mccartyp/dmx-lan-console)](LICENSE)

Interactive CLI console for managing multi-protocol smart lighting devices (Govee, LIFX, etc.) via the [DMX LAN Bridge](https://github.com/mccartyp/govee-artnet-lan-bridge).

## Overview

`dmx-lan-console` is a standalone command-line tool that provides an interactive shell interface for controlling and monitoring smart lighting devices through the DMX LAN Bridge REST API. It's designed as a thin client that can connect to local or remote bridge instances and supports multiple protocols including Govee, LIFX, and more.

## Features

### Core Capabilities
- **Interactive Shell**: Full-featured command shell with tab completion, history, and rich formatting
- **Multi-Protocol Support**: Manage Govee, LIFX, and other smart lighting devices from a single interface
- **Device Management**: List, configure, enable/disable, and control devices across all supported protocols
- **Protocol Filtering**: Filter devices by protocol ([cyan]🔵[/] Govee, [magenta]🟣[/] LIFX)
- **DMX Mapping**: Create and manage ArtNet to device mappings
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

#### Option 1: Install from .deb Package (Recommended for Ubuntu/Debian)

**Quick download:** Visit the [Latest Release](https://github.com/mccartyp/dmx-lan-console/releases/latest) page and download the `.deb` file.

**Or use command line:**
```bash
# Download the latest .deb package (check releases page for exact filename)
wget $(curl -s https://api.github.com/repos/mccartyp/dmx-lan-console/releases/latest | grep "browser_download_url.*\.deb" | cut -d '"' -f 4)

# Install the downloaded package
sudo dpkg -i dmx-lan-console_*.deb

# If you see dependency errors, install Python packages via pip
pip3 install httpx websockets pyyaml rich prompt-toolkit
sudo dpkg -i --force-depends dmx-lan-console_*.deb
```

**Tested on:**
- ✅ Ubuntu 22.04 LTS (via pip fallback)
- ✅ Ubuntu 24.04 LTS (via pip fallback)
- ✅ Debian 13 (Trixie)

#### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/mccartyp/dmx-lan-console.git
cd dmx-lan-console

# Install
pip install .

# Or install in development mode
pip install -e .
```

See [INSTALLATION.md](docs/INSTALLATION.md) for detailed installation instructions and troubleshooting.

### Basic Usage

```bash
# Start interactive shell (connects to localhost:8000 by default)
dmx-lan-console

# Connect to remote bridge
dmx-lan-console --server-url http://192.168.1.100:8000

# Use API key authentication
dmx-lan-console --api-key YOUR_API_KEY

# Or use environment variable (also supports legacy GOVEE_ARTNET_API_KEY)
export ARTNET_LAN_API_KEY=your-api-key
dmx-lan-console

# Run single command without shell
dmx-lan-console devices list --output table
```

### First Steps

Once in the shell:

```
dmx-bridge> monitor dashboard               # View comprehensive system dashboard
dmx-bridge> monitor devices                 # List all devices with detailed status
dmx-bridge> devices list                    # List all discovered devices
dmx-bridge> devices list --protocol govee   # List only Govee devices
dmx-bridge> devices list --protocol lifx    # List only LIFX devices
dmx-bridge> mappings create --device-id AA:BB:CC:DD:EE:FF:11:22 \
                             --universe 1 --template RGB --start-channel 1
dmx-bridge> logs events                     # View real-time event stream
dmx-bridge> logs tail                       # Stream application logs in real-time
dmx-bridge> watch dashboard                 # Live updating dashboard (updates every 5s)
dmx-bridge> help                            # Show all available commands
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

**Universe Default:** Mappings and views default to universe 1. sACN (E1.31) universes are 1–63999. Art-Net supports universe 0. Universe 0 is Art-Net-only in this application; universes 1+ are mergeable across protocols.

**Note:** Event notifications appear automatically in the background while you work. Look for colored bubble indicators (🔵 🟢 🔴 ⚙️) in the console output!

## Configuration

Configuration is stored at `~/.dmx_lan_console/config.yaml`:

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
- [DMX LAN Bridge](https://github.com/mccartyp/govee-artnet-lan-bridge) - Server component

## Requirements

- Python 3.10 or higher
- DMX LAN Bridge server running
- Network connectivity to bridge server

## Architecture

```
┌─────────────────────────┐
│  dmx-lan-console     │  ← This package (CLI client)
│  (Interactive Shell)    │
└────────────┬────────────┘
             │ HTTP/WebSocket
             │ (REST API)
┌────────────▼────────────┐
│ artnet-lan-bridge       │  ← Bridge server (multi-protocol)
│   (API Server)          │
└────────────┬────────────┘
             │ Multi-Protocol Support
             │ (Govee, LIFX, etc.)
             │ ArtNet (UDP)
┌────────────▼────────────┐
│   Smart Light Devices   │
│  Govee │ LIFX │ Others  │
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
