# Installation Guide

This guide covers various methods for installing `artnet-lan-console`.

## Prerequisites

### System Requirements
- **Operating System**: Linux (Debian 13.2 or compatible), macOS, or Windows with WSL
- **Python**: Version 3.10 or higher
- **Bridge Server**: ArtNet LAN Bridge must be running and accessible

### Check Python Version

```bash
python3 --version
# Should show Python 3.10.x or higher
```

## Installation Methods

### Method 1: Install from Source (Recommended for Development)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mccartyp/artnet-lan-console.git
   cd artnet-lan-console
   ```

2. **Install with pip**:
   ```bash
   pip3 install .
   ```

   Or for development mode (editable install):
   ```bash
   pip3 install -e .
   ```

3. **Verify installation**:
   ```bash
   artnet-lan-console --help
   ```

### Method 2: Install from Debian Package (System-Wide)

For Debian 13.2 and compatible systems:

1. **Download the .deb package**:
   ```bash
   # Build from source
   git clone https://github.com/mccartyp/artnet-lan-console.git
   cd artnet-lan-console
   make deb
   ```

2. **Install the package**:
   ```bash
   sudo dpkg -i artnet-lan-console_2.0.0_all.deb
   ```

3. **Install dependencies** (if needed):
   ```bash
   sudo apt-get install -f
   ```

4. **Verify installation**:
   ```bash
   artnet-lan-console --version
   ```

### Method 3: Install to /usr/local (No Package Manager)

For manual installation without creating a Debian package:

1. **Clone and build**:
   ```bash
   git clone https://github.com/mccartyp/artnet-lan-console.git
   cd artnet-lan-console
   ```

2. **Install to /usr/local**:
   ```bash
   sudo make install
   ```

   This installs:
   - Binary: `/usr/local/bin/artnet-lan-console`
   - Python package: `/usr/local/lib/python3.x/site-packages/`

3. **Verify installation**:
   ```bash
   artnet-lan-console --help
   ```

### Method 4: User-Local Installation (No Root Access)

If you don't have root access:

```bash
# Install to ~/.local
pip3 install --user .

# Ensure ~/.local/bin is in your PATH
export PATH="$HOME/.local/bin:$PATH"

# Add to your ~/.bashrc or ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

## Python Dependencies

The following packages will be installed automatically:

- **httpx** (>=0.27.0) - HTTP client for API requests
- **websockets** (>=12.0) - WebSocket support for real-time features
- **pyyaml** (>=6.0.0) - Configuration file parsing
- **rich** (>=13.0.0) - Terminal formatting and tables
- **prompt-toolkit** (>=3.0.0) - Interactive shell features

### Manual Dependency Installation

If automatic installation fails:

```bash
pip3 install httpx websockets pyyaml rich prompt-toolkit
```

## Post-Installation Configuration

### 1. Create Configuration Directory

```bash
mkdir -p ~/.artnet_lan_console
```

### 2. Create Configuration File

Create `~/.artnet_lan_console/config.yaml`:

```yaml
servers:
  default:
    url: http://127.0.0.1:8000
    name: "Local Bridge"
    api_key: null  # Set if your bridge requires authentication

active_server: default

shell:
  history_size: 1000
  auto_refresh_interval: 2.0
  default_output_format: table

bookmarks: {}
aliases: {}
```

### 3. Set Environment Variables (Optional)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Bridge server URL (if not using localhost)
export ARTNET_LAN_SERVER_URL=http://192.168.1.100:8000

# API key for authentication (legacy GOVEE_ARTNET_API_KEY also supported)
export ARTNET_LAN_API_KEY=your-api-key-here

# Default output format
export ARTNET_LAN_OUTPUT=table
```

## Verifying Installation

### Test Basic Functionality

```bash
# Show version
artnet-lan-console --version

# Show help
artnet-lan-console --help

# Test connection to bridge (requires bridge running)
artnet-lan-console health
```

### Test Interactive Shell

```bash
# Start shell
artnet-lan-console

# In shell, try:
dmx-bridge> help
dmx-bridge> connect
dmx-bridge> devices list
dmx-bridge> exit
```

## Troubleshooting

### Command Not Found

If `artnet-lan-console` is not found:

1. **Check installation location**:
   ```bash
   which artnet-lan-console
   pip3 show artnet-lan-console
   ```

2. **Add to PATH** (if installed with `--user`):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. **Run directly**:
   ```bash
   python3 -m artnet_lan_console
   ```

### Import Errors

If you see `ModuleNotFoundError`:

1. **Reinstall dependencies**:
   ```bash
   pip3 install --force-reinstall httpx websockets pyyaml rich prompt-toolkit
   ```

2. **Check Python version**:
   ```bash
   python3 --version  # Must be 3.10+
   ```

3. **Try in virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install .
   ```

### Connection Errors

If you can't connect to the bridge:

1. **Verify bridge is running**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"ok"}
   ```

2. **Check firewall**:
   ```bash
   sudo ufw allow 8000/tcp  # Ubuntu/Debian
   ```

3. **Test with explicit URL**:
   ```bash
   artnet-lan-console --server-url http://localhost:8000 health
   ```

### Permission Errors

If you see permission errors during installation:

1. **Use `--user` flag**:
   ```bash
   pip3 install --user .
   ```

2. **Or use virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install .
   ```

## Uninstallation

### From pip

```bash
pip3 uninstall artnet-lan-console
```

### From Debian package

```bash
sudo apt-get remove artnet-lan-console
```

### Manual uninstall

```bash
sudo rm /usr/local/bin/artnet-lan-console
sudo rm -rf /usr/local/lib/python3.*/site-packages/artnet_lan_console*
```

### Remove configuration

```bash
rm -rf ~/.artnet_lan_console
```

## Upgrading

### From source

```bash
cd artnet-lan-console
git pull
pip3 install --upgrade .
```

### From Debian package

```bash
# Build new package
make deb

# Install (will upgrade)
sudo dpkg -i artnet-lan-console_*.deb
```

## System-Specific Notes

### Debian/Ubuntu

- Debian packages are built for Debian 13.2 (Trixie)
- Should work on Ubuntu 22.04+ and other Debian derivatives
- Uses system Python packages where available

### macOS

```bash
# Install Python 3.10+ if needed
brew install python@3.10

# Install console
pip3.10 install .
```

### Windows (WSL)

Use the Linux installation method inside Windows Subsystem for Linux.

## Next Steps

After installation, see the [Usage Guide](USAGE.md) for command reference and examples.
