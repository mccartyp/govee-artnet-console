# DMX LAN Console Guide

The DMX LAN Console includes a powerful interactive shell mode that provides real-time monitoring, log viewing, and enhanced usability features for managing your multi-protocol smart lighting devices via the DMX LAN Bridge.

## Table of Contents

- [Getting Started](#getting-started)
- [Core Features](#core-features)
- [Shell Commands](#shell-commands)
- [Advanced Features](#advanced-features)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Tips and Tricks](#tips-and-tricks)

## Getting Started

### Launching the Shell

```bash
# Start interactive shell
dmx-lan-console

# Or with custom server URL
dmx-lan-console --server-url http://192.168.1.100:8000
```

### First Steps

```
dmx-bridge> help                    # Show available commands
dmx-bridge> tips                    # Show helpful tips
dmx-bridge> status                  # Check bridge connection status
dmx-bridge> devices list            # List all discovered devices
dmx-bridge> devices list --protocol govee   # List only Govee devices
dmx-bridge> devices list --protocol lifx    # List only LIFX devices
```

## Core Features

### 📊 Real-time Monitoring

Watch your system in action with comprehensive monitoring commands:

```bash
dmx-bridge> monitor dashboard    # Comprehensive dashboard with health + devices + stats
dmx-bridge> monitor devices      # Detailed device table with all fields
dmx-bridge> monitor stats        # System statistics summary
dmx-bridge> watch dashboard      # Live updating dashboard (auto-refresh every 5s)
dmx-bridge> watch devices        # Live updating device monitor
```

**Monitor Dashboard** displays:
- **Statistics Summary Cards**: Total Devices, Online, Offline, Mappings count
- **Protocol Breakdown**: Device counts per protocol (🔵 Govee, 🟣 LIFX, etc.)
- **System Health Panel**: Status of all subsystems (discovery, sender, artnet, api, poller)
- **Device Table**: Top 10 devices with Device ID, Protocol, Status, IP, Model, Last Seen, and Mappings
- Relative time formatting (e.g., "2m ago", "5h ago")
- ANSI box drawing for clean, aligned borders

**Monitor Devices** shows:
- Full device listing with all fields
- Device ID, Status, IP, Model, Description, Last Seen, Mappings
- Sorted by online status then device ID
- Summary statistics at the bottom

### 📝 Log Viewing & Streaming

View and search logs without leaving the shell:

```bash
dmx-bridge> logs view                 # Show last 50 log lines (paginated)
dmx-bridge> logs tail                 # Stream logs in real-time (WebSocket)
dmx-bridge> logs search "discovered"  # Search logs for pattern
```

**Log filtering:**
```bash
dmx-bridge> logs view --level ERROR        # Show only error-level logs
dmx-bridge> logs tail --level ERROR        # Tail only error-level logs
dmx-bridge> logs tail --logger discovery   # Show logs from discovery subsystem
```

### 🔔 Real-Time Event Streaming

Monitor system events as they happen with the event streaming feature:

```bash
dmx-bridge> logs events                    # View real-time event stream
dmx-bridge> logs events --type device      # Filter device events only
dmx-bridge> logs events --type mapping     # Filter mapping events only
dmx-bridge> logs events --type health      # Filter health events only
```

**Event Types:**
- **Device Events**: `device_discovered`, `device_online`, `device_offline`, `device_updated`
- **Mapping Events**: `mapping_created`, `mapping_updated`, `mapping_deleted`
- **Health Events**: `health_status_changed`

**Event Notifications:**
Events are displayed in two ways:
1. **Console Notifications** (background, terse format):
   - Appear automatically while you work
   - Colored bubble indicators: 🔵 (discovered), 🟢 (online/created), 🔴 (offline/deleted), ⚙️ (health)
   - Example: `🔵 *** Device Discovered: AA:BB:CC:DD:EE:FF (Kitchen Light) at 192.168.1.100`
   - Only shown when not executing commands

2. **Event Stream Viewer** (detailed format):
   - Accessed via `logs events` command
   - Verbose multi-line format with timestamps
   - Shows all event data fields
   - Keyboard controls: End (jump to bottom), f (filter), Esc/q (exit)

**Event Stream Controls:**
- Press `End` to jump to bottom and enable auto-scroll
- Press `f` to view current filter status
- Press `Esc` or `q` to exit event stream mode

### ⌨️ Command History & Autocomplete

- **Tab completion** - Press Tab to autocomplete commands
- **History navigation** - Use ↑/↓ arrows to navigate command history
- **Persistent history** - Command history saved to `~/.dmx_lan_console/shell_history`
- **Reverse search** - Press Ctrl+R to search command history

### 🔖 Bookmarks

Save frequently used device IDs with friendly names:

```bash
dmx-bridge> bookmark add kitchen "AA:BB:CC:DD:EE:FF"
dmx-bridge> bookmark add bedroom "11:22:33:44:55:66"
dmx-bridge> bookmark list

# Use bookmarks in commands
dmx-bridge> devices enable @kitchen
dmx-bridge> mappings create --device-id @bedroom --universe 1 --template RGB
```

**Bookmark commands:**
- `bookmark add <name> <value>` - Create a new bookmark
- `bookmark list` - Show all bookmarks
- `bookmark delete <name>` - Remove a bookmark
- `bookmark clear` - Remove all bookmarks

### 🏷️ Aliases

Create shortcuts for frequently used commands:

```bash
dmx-bridge> alias dl "devices list"
dmx-bridge> alias ds "devices"
dmx-bridge> alias ml "mappings list"

# Use aliases
dmx-bridge> dl           # Executes "devices list"
dmx-bridge> ds enable @kitchen   # Executes "devices enable @kitchen"
```

**Alias commands:**
- `alias <name> "<command>"` - Create a new alias
- `alias list` - Show all aliases
- `alias delete <name>` - Remove an alias
- `alias clear` - Remove all aliases

## Shell Commands

### Connection Management

```bash
dmx-bridge> connect              # Connect to the bridge server
dmx-bridge> disconnect           # Disconnect from server
dmx-bridge> status              # Show connection status
```

### Device Management

```bash
dmx-bridge> devices list                           # List all devices (simplified view)
dmx-bridge> devices list detailed                  # Show detailed device information
dmx-bridge> devices list --state active            # Filter by state (active, disabled, offline)
dmx-bridge> devices list --id AA:BB:CC             # Filter by device ID (MAC address)
dmx-bridge> devices list --ip 192.168.1.100        # Filter by IP address
dmx-bridge> devices list detailed --state offline  # Detailed view with filters
dmx-bridge> devices enable <device_id>             # Enable a device
dmx-bridge> devices disable <device_id>            # Disable a device
dmx-bridge> devices set-name <device_id> "Name"    # Set device name
dmx-bridge> devices set-capabilities <device_id> --brightness true --color true  # Set capabilities
dmx-bridge> devices command <device_id> [options]  # Send control commands
```

#### Device Control Commands

Send control commands to devices directly from the shell:

```bash
# Turn device on/off
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --on
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --off

# Set brightness (0-255)
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --brightness 200

# Set RGB color (hex format)
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --color #FF00FF
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --color ff8800
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --color F0F    # Shorthand expands to FF00FF

# Set color temperature (0-255)
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --ct 128
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --kelvin 200  # Same as --ct

# Combine multiple commands
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --on --brightness 200 --color #FF00FF
dmx-bridge> devices command AA:BB:CC:DD:EE:FF --color ff8800 --brightness 128

# Use bookmarks for convenience
dmx-bridge> bookmark add kitchen "AA:BB:CC:DD:EE:FF"
dmx-bridge> devices command @kitchen --on --color #00FF00
```

### Mapping Management

```bash
dmx-bridge> mappings list                          # List all mappings
dmx-bridge> mappings get <id>                      # Get mapping details
dmx-bridge> mappings delete <id>                   # Delete a mapping
dmx-bridge> mappings channel-map                   # Show channel map
```

### Monitoring Commands

#### Static Snapshots (Execute Once)

```bash
dmx-bridge> monitor dashboard                      # Comprehensive dashboard
dmx-bridge> monitor devices                        # Detailed device table
dmx-bridge> monitor stats                          # System statistics summary
dmx-bridge> logs view                              # View recent logs (paginated)
dmx-bridge> logs events                            # Real-time event stream viewer
```

**Monitor Dashboard Example Output:**
```
┌──────────────────────────────────────────────────────────────┐
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │   12    │  │   10    │  │    2    │  │    8    │         │
│  │ Devices │  │ Online  │  │ Offline │  │Mappings │         │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘         │
│                                                               │
│  System Health                                                │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │ discovery   │ │ sender      │                            │
│  │ ✓ ok        │ │ ✓ ok        │                            │
│  └─────────────┘ └─────────────┘                            │
│                                                               │
│  Devices (Top 10)                                             │
│  Device ID              Status  IP              Model  Last   │
│  AA:BB:CC:DD:EE:FF     🟢 Online 192.168.1.100  H6046  2m ago │
│  11:22:33:44:55:66     🔴 Offline 192.168.1.101 H6159  1h ago │
└──────────────────────────────────────────────────────────────┘
```

**Monitor Devices Example Output:**
```
Device ID              Status    IP              Model  Description    Last Seen           Mappings
AA:BB:CC:DD:EE:FF     🟢 Online  192.168.1.100  H6046  Kitchen Light  2024-01-15 14:30:22      3
11:22:33:44:55:66     🟢 Online  192.168.1.101  H6159  Bedroom Strip  2024-01-15 14:29:45      2
22:33:44:55:66:77     🔴 Offline 192.168.1.102  H6046  Living Room    2024-01-15 13:15:10      0

Summary: 12 total devices | 10 online | 2 offline | 8 mappings
```

#### Live Updating Views (Auto-Refresh)

```bash
dmx-bridge> watch dashboard                        # Live dashboard (updates every 5s)
dmx-bridge> watch devices                          # Live device monitor
```

**Watch Mode Controls:**
- Press `+` to increase refresh interval
- Press `-` to decrease refresh interval
- Press `Esc` or `q` to exit watch mode

#### Event Streaming

```bash
dmx-bridge> logs events                            # View all events in real-time
dmx-bridge> logs events --type device              # Filter device events only
dmx-bridge> logs events --type mapping             # Filter mapping events only
dmx-bridge> logs events --type health              # Filter health events only
```

**Event Stream Example Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2024-01-15 14:30:22] device_discovered
  Device ID: AA:BB:CC:DD:EE:FF
  IP: 192.168.1.100
  Model: H6046
  Description: Kitchen Light
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2024-01-15 14:30:25] device_online
  Device ID: AA:BB:CC:DD:EE:FF
  Reason: Device responded to ping
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2024-01-15 14:30:30] mapping_created
  Mapping ID: 123
  Device ID: AA:BB:CC:DD:EE:FF (Kitchen Light)
  Universe: 1
  Channel: 1-3
  Template: RGB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Universe Default Information:**
- Default universe for mappings and views is **universe 1**
- sACN (E1.31) universes: 1–63999
- Art-Net supports universe 0
- Universe 0 is Art-Net-only in this application; universes 1+ are mergeable across protocols

**Background Event Notifications:**
While working in the shell, you'll see terse event notifications automatically:
```
dmx-bridge> devices list
🔵 *** Device Discovered: AA:BB:CC:DD:EE:FF (Kitchen Light) at 192.168.1.100
🟢 *** Device Online: AA:BB:CC:DD:EE:FF (Kitchen Light)
Device ID              Status    IP              Model
AA:BB:CC:DD:EE:FF     🟢 Online  192.168.1.100  H6046
```

#### Log Viewing

```bash
dmx-bridge> logs view                              # View recent logs (paginated)
dmx-bridge> logs view --level ERROR                # Filter by log level
dmx-bridge> logs view --logger discovery           # Filter by logger name
dmx-bridge> logs tail                              # Stream logs in real-time
dmx-bridge> logs tail --level ERROR --logger api   # Tail with filters
dmx-bridge> logs search "discovered"               # Search logs for pattern
```

### Output Control

```bash
dmx-bridge> output --format json    # Switch to JSON output
dmx-bridge> output --format yaml    # Switch to YAML output
dmx-bridge> output --format table   # Switch to table output (default)
```

### Shell Utilities

```bash
dmx-bridge> help                    # Show all commands
dmx-bridge> help <command>          # Show help for specific command
dmx-bridge> version                 # Show shell version
dmx-bridge> tips                    # Show helpful tips
dmx-bridge> clear                   # Clear the screen
dmx-bridge> exit                    # Exit the shell (or Ctrl+D)
```

## Advanced Features

### 🔌 WebSocket Connections & Status

The shell maintains two persistent WebSocket connections for real-time updates:

1. **Events WebSocket** (`/events/stream`): Real-time event notifications
2. **Logs WebSocket** (`/logs/stream`): Real-time log streaming (when using `logs tail`)

**Toolbar Status Indicators:**

The bottom toolbar shows connection status for both the API and Events WebSocket:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
● API Connected | Events: ● Connected │ Devices: Active 10 | ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Health: ✓ ok │ Server: http://localhost:8000 │ Updated: 2s ago
```

**Connection States:**
- `● Connected` (green) - WebSocket connected and receiving events
- `◐ Reconnecting` (yellow) - Attempting to reconnect after disconnect
- `○ Connecting` (dim) - Initial connection in progress
- `○ Disconnected` (dim) - Not connected

**Automatic Reconnection:**
The Events WebSocket automatically reconnects using exponential backoff:
- Initial retry: 1 second delay
- Subsequent retries: 2s → 4s → 8s → 10s (max)
- Connection state shown in toolbar
- Background notifications continue after reconnection

**Ping/Pong Keepalive:**
WebSocket connections use ping/pong messages every 30 seconds to maintain connectivity and detect disconnections quickly.

### 🎬 Batch Execution

Execute multiple commands from a file:

```bash
# Create a script file
$ cat > setup.artnet <<EOF
connect
devices list
monitor dashboard
logs events --type device
EOF

# Run the batch file
dmx-lan-console batch load setup.artnet
```

### 💾 Session Management

Save and restore shell sessions:

```bash
dmx-bridge> session save my-setup              # Save current state
dmx-bridge> session list                       # List saved sessions
dmx-bridge> session load my-setup              # Restore a session
dmx-bridge> session delete my-setup            # Delete a session
```

## Configuration

The shell configuration is stored at `~/.dmx_lan_console/config.yaml`:

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
  events: "logs events"
```

## Environment Variables

Set these environment variables to configure the shell:

```bash
# Server URL
export ARTNET_LAN_SERVER_URL=http://192.168.1.100:8000

# API key for authentication (legacy GOVEE_ARTNET_API_KEY also supported)
export ARTNET_LAN_API_KEY=your-api-key-here

# Default output format
export ARTNET_LAN_OUTPUT_FORMAT=json  # json, yaml, or table
```

## Tips and Tricks

### Quick Device Discovery Workflow

```bash
dmx-bridge> monitor dashboard              # Check system health and device count
dmx-bridge> monitor devices                # List all devices with details
dmx-bridge> logs events --type device      # Monitor device events in real-time
```

### Monitoring Multiple Screens

Use multiple terminal windows for comprehensive monitoring:

**Terminal 1**: Watch dashboard
```bash
dmx-bridge> watch dashboard
```

**Terminal 2**: Monitor events
```bash
dmx-bridge> logs events
```

**Terminal 3**: Interactive shell
```bash
dmx-bridge> devices list
dmx-bridge> mappings list
```

### Event Notification Best Practices

1. **Background Awareness**: Events notifications appear automatically while you work
2. **Filter by Type**: Use `logs events --type device` to focus on specific event types
3. **Console vs Stream**: Console notifications are terse; event stream viewer is detailed
4. **Jump to Latest**: Press `End` in event stream to jump to newest events

### Efficient Device Management

```bash
# Create bookmarks for frequently used devices
dmx-bridge> bookmark add kitchen "AA:BB:CC:DD:EE:FF"
dmx-bridge> bookmark add bedroom "11:22:33:44:55:66"

# Use bookmarks in commands
dmx-bridge> devices command @kitchen --on --brightness 255
dmx-bridge> mappings create --device-id @bedroom --universe 1 --template RGB

# Create aliases for common workflows
dmx-bridge> alias status "monitor dashboard"
dmx-bridge> alias events "logs events --type device"
```

### WebSocket Connection Issues

If you experience WebSocket connection problems:

1. **Check Toolbar**: Look at the Events status in the bottom toolbar
2. **Reconnection**: The shell automatically reconnects with exponential backoff
3. **Manual Reconnect**: Exit and restart the shell to force reconnection
4. **Firewall**: Ensure WebSocket connections (ports) are not blocked
5. **Bridge Health**: Check bridge status with `monitor dashboard`

### Dashboard Refresh Tips

- Use `monitor dashboard` for one-time snapshots (doesn't block shell)
- Use `watch dashboard` for continuous monitoring (blocks shell input)
- Press `+` or `-` in watch mode to adjust refresh interval
- Press `Esc` or `q` to exit watch mode

### Performance Considerations

- Event notifications are batched (100ms interval) for performance
- Dashboard queries are cached (5s interval) to reduce API load
- Large device lists may be paginated in some views
- Use filters (`--type`, `--state`) to reduce output
