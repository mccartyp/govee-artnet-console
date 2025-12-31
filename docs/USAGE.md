# Govee ArtNet CLI Shell Guide

The Govee ArtNet CLI includes a powerful interactive shell mode that provides real-time monitoring, log viewing, and enhanced usability features for managing your bridge.

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
govee-artnet shell

# Or with custom server URL
govee-artnet --server-url http://192.168.1.100:8000 shell
```

### First Steps

```
govee> help            # Show available commands
govee> tips            # Show helpful tips
govee> status          # Check bridge connection status
govee> devices list    # List discovered devices
```

## Core Features

### 📊 Real-time Monitoring

Watch your system in action with comprehensive monitoring commands:

```bash
govee> monitor dashboard    # Comprehensive dashboard with health + devices + stats
govee> monitor devices      # Detailed device table with all fields
govee> monitor stats        # System statistics summary
govee> watch dashboard      # Live updating dashboard (auto-refresh every 5s)
govee> watch devices        # Live updating device monitor
```

**Monitor Dashboard** displays:
- **Statistics Summary Cards**: Total Devices, Online, Offline, Mappings count
- **System Health Panel**: Status of all subsystems (discovery, sender, artnet, api, poller)
- **Device Table**: Top 10 devices with Device ID, Status, IP, Model, Last Seen, and Mappings
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
govee> logs view                 # Show last 50 log lines (paginated)
govee> logs tail                 # Stream logs in real-time (WebSocket)
govee> logs search "discovered"  # Search logs for pattern
```

**Log filtering:**
```bash
govee> logs view --level ERROR        # Show only error-level logs
govee> logs tail --level ERROR        # Tail only error-level logs
govee> logs tail --logger discovery   # Show logs from discovery subsystem
```

### 🔔 Real-Time Event Streaming

Monitor system events as they happen with the event streaming feature:

```bash
govee> logs events                    # View real-time event stream
govee> logs events --type device      # Filter device events only
govee> logs events --type mapping     # Filter mapping events only
govee> logs events --type health      # Filter health events only
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
- **Persistent history** - Command history saved to `~/.govee_artnet_console/shell_history`
- **Reverse search** - Press Ctrl+R to search command history

### 🔖 Bookmarks

Save frequently used device IDs with friendly names:

```bash
govee> bookmark add kitchen "AA:BB:CC:DD:EE:FF"
govee> bookmark add bedroom "11:22:33:44:55:66"
govee> bookmark list

# Use bookmarks in commands
govee> devices enable @kitchen
govee> mappings create --device-id @bedroom --universe 0 --template RGB
```

**Bookmark commands:**
- `bookmark add <name> <value>` - Create a new bookmark
- `bookmark list` - Show all bookmarks
- `bookmark delete <name>` - Remove a bookmark
- `bookmark clear` - Remove all bookmarks

### 🏷️ Aliases

Create shortcuts for frequently used commands:

```bash
govee> alias dl "devices list"
govee> alias ds "devices"
govee> alias ml "mappings list"

# Use aliases
govee> dl           # Executes "devices list"
govee> ds enable @kitchen   # Executes "devices enable @kitchen"
```

**Alias commands:**
- `alias <name> "<command>"` - Create a new alias
- `alias list` - Show all aliases
- `alias delete <name>` - Remove an alias
- `alias clear` - Remove all aliases

## Shell Commands

### Connection Management

```bash
govee> connect              # Connect to the bridge server
govee> disconnect           # Disconnect from server
govee> status              # Show connection status
```

### Device Management

```bash
govee> devices list                           # List all devices (simplified view)
govee> devices list detailed                  # Show detailed device information
govee> devices list --state active            # Filter by state (active, disabled, offline)
govee> devices list --id AA:BB:CC             # Filter by device ID (MAC address)
govee> devices list --ip 192.168.1.100        # Filter by IP address
govee> devices list detailed --state offline  # Detailed view with filters
govee> devices enable <device_id>             # Enable a device
govee> devices disable <device_id>            # Disable a device
govee> devices set-name <device_id> "Name"    # Set device name
govee> devices set-capabilities <device_id> --brightness true --color true  # Set capabilities
govee> devices command <device_id> [options]  # Send control commands
```

#### Device Control Commands

Send control commands to devices directly from the shell:

```bash
# Turn device on/off
govee> devices command AA:BB:CC:DD:EE:FF --on
govee> devices command AA:BB:CC:DD:EE:FF --off

# Set brightness (0-255)
govee> devices command AA:BB:CC:DD:EE:FF --brightness 200

# Set RGB color (hex format)
govee> devices command AA:BB:CC:DD:EE:FF --color #FF00FF
govee> devices command AA:BB:CC:DD:EE:FF --color ff8800
govee> devices command AA:BB:CC:DD:EE:FF --color F0F    # Shorthand expands to FF00FF

# Set color temperature (0-255)
govee> devices command AA:BB:CC:DD:EE:FF --ct 128
govee> devices command AA:BB:CC:DD:EE:FF --kelvin 200  # Same as --ct

# Combine multiple commands
govee> devices command AA:BB:CC:DD:EE:FF --on --brightness 200 --color #FF00FF
govee> devices command AA:BB:CC:DD:EE:FF --color ff8800 --brightness 128

# Use bookmarks for convenience
govee> bookmark add kitchen "AA:BB:CC:DD:EE:FF"
govee> devices command @kitchen --on --color #00FF00
```

### Mapping Management

```bash
govee> mappings list                          # List all mappings
govee> mappings get <id>                      # Get mapping details
govee> mappings delete <id>                   # Delete a mapping
govee> mappings channel-map                   # Show channel map
```

### Monitoring Commands

#### Static Snapshots (Execute Once)

```bash
govee> monitor dashboard                      # Comprehensive dashboard
govee> monitor devices                        # Detailed device table
govee> monitor stats                          # System statistics summary
govee> logs view                              # View recent logs (paginated)
govee> logs events                            # Real-time event stream viewer
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
govee> watch dashboard                        # Live dashboard (updates every 5s)
govee> watch devices                          # Live device monitor
```

**Watch Mode Controls:**
- Press `+` to increase refresh interval
- Press `-` to decrease refresh interval
- Press `Esc` or `q` to exit watch mode

#### Event Streaming

```bash
govee> logs events                            # View all events in real-time
govee> logs events --type device              # Filter device events only
govee> logs events --type mapping             # Filter mapping events only
govee> logs events --type health              # Filter health events only
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
  Universe: 0
  Channel: 1-3
  Template: RGB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Background Event Notifications:**
While working in the shell, you'll see terse event notifications automatically:
```
govee> devices list
🔵 *** Device Discovered: AA:BB:CC:DD:EE:FF (Kitchen Light) at 192.168.1.100
🟢 *** Device Online: AA:BB:CC:DD:EE:FF (Kitchen Light)
Device ID              Status    IP              Model
AA:BB:CC:DD:EE:FF     🟢 Online  192.168.1.100  H6046
```

#### Log Viewing

```bash
govee> logs view                              # View recent logs (paginated)
govee> logs view --level ERROR                # Filter by log level
govee> logs view --logger discovery           # Filter by logger name
govee> logs tail                              # Stream logs in real-time
govee> logs tail --level ERROR --logger api   # Tail with filters
govee> logs search "discovered"               # Search logs for pattern
```

### Output Control

```bash
govee> output --format json    # Switch to JSON output
govee> output --format yaml    # Switch to YAML output
govee> output --format table   # Switch to table output (default)
```

### Shell Utilities

```bash
govee> help                    # Show all commands
govee> help <command>          # Show help for specific command
govee> version                 # Show shell version
govee> tips                    # Show helpful tips
govee> clear                   # Clear the screen
govee> exit                    # Exit the shell (or Ctrl+D)
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
$ cat > setup.govee <<EOF
connect
devices list
monitor dashboard
logs events --type device
EOF

# Run the batch file
govee-artnet-console batch load setup.govee
```

### 💾 Session Management

Save and restore shell sessions:

```bash
govee> session save my-setup              # Save current state
govee> session list                       # List saved sessions
govee> session load my-setup              # Restore a session
govee> session delete my-setup            # Delete a session
```

## Configuration

The shell configuration is stored at `~/.govee_artnet_console/config.yaml`:

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
export GOVEE_ARTNET_SERVER_URL=http://192.168.1.100:8000

# API key for authentication
export GOVEE_ARTNET_API_KEY=your-api-key-here

# Default output format
export GOVEE_ARTNET_OUTPUT_FORMAT=json  # json, yaml, or table
```

## Tips and Tricks

### Quick Device Discovery Workflow

```bash
govee> monitor dashboard              # Check system health and device count
govee> monitor devices                # List all devices with details
govee> logs events --type device      # Monitor device events in real-time
```

### Monitoring Multiple Screens

Use multiple terminal windows for comprehensive monitoring:

**Terminal 1**: Watch dashboard
```bash
govee> watch dashboard
```

**Terminal 2**: Monitor events
```bash
govee> logs events
```

**Terminal 3**: Interactive shell
```bash
govee> devices list
govee> mappings list
```

### Event Notification Best Practices

1. **Background Awareness**: Events notifications appear automatically while you work
2. **Filter by Type**: Use `logs events --type device` to focus on specific event types
3. **Console vs Stream**: Console notifications are terse; event stream viewer is detailed
4. **Jump to Latest**: Press `End` in event stream to jump to newest events

### Efficient Device Management

```bash
# Create bookmarks for frequently used devices
govee> bookmark add kitchen "AA:BB:CC:DD:EE:FF"
govee> bookmark add bedroom "11:22:33:44:55:66"

# Use bookmarks in commands
govee> devices command @kitchen --on --brightness 255
govee> mappings create --device-id @bedroom --universe 0 --template RGB

# Create aliases for common workflows
govee> alias status "monitor dashboard"
govee> alias events "logs events --type device"
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
