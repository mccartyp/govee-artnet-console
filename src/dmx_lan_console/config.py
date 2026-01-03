"""Configuration management for dmx-lan-console."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# Default configuration directory
DEFAULT_CONFIG_DIR = Path.home() / ".dmx_lan_console"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_HISTORY_FILE = DEFAULT_CONFIG_DIR / "shell_history"

# Protocol display configuration
PROTOCOL_COLORS = {
    "govee": "cyan",
    "lifx": "magenta",
    "unknown": "dim white",
}

PROTOCOL_EMOJIS = {
    "govee": "🔵",  # Blue circle
    "lifx": "🟣",   # Purple circle
    "unknown": "⚪", # White circle
}


def format_protocol(protocol: str) -> str:
    """Format protocol name with colored emoji indicator.

    Uses Rich markup to ensure consistent emoji rendering across terminals.

    Args:
        protocol: Protocol name (govee, lifx, etc.)

    Returns:
        Rich-formatted string with colored emoji and protocol name

    Examples:
        >>> format_protocol("govee")
        '[cyan]🔵[/] Govee'
        >>> format_protocol("lifx")
        '[magenta]🟣[/] LIFX'
    """
    protocol_lower = (protocol or "unknown").lower()
    emoji = PROTOCOL_EMOJIS.get(protocol_lower, PROTOCOL_EMOJIS["unknown"])
    color = PROTOCOL_COLORS.get(protocol_lower, PROTOCOL_COLORS["unknown"])

    # Return colored emoji + protocol name (capitalized)
    return f"[{color}]{emoji}[/] {protocol.title() if protocol else 'Unknown'}"


@dataclass
class ServerProfile:
    """Server profile configuration."""

    name: str
    url: str
    api_key: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {"name": self.name, "url": self.url}
        if self.api_key:
            data["api_key"] = self.api_key
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerProfile:
        """Create from dictionary."""
        return cls(
            name=data.get("name", "default"),
            url=data["url"],
            api_key=data.get("api_key"),
        )


@dataclass
class ShellPreferences:
    """Shell UI preferences."""

    history_size: int = 1000
    auto_refresh_interval: float = 2.0
    default_output_format: str = "table"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "history_size": self.history_size,
            "auto_refresh_interval": self.auto_refresh_interval,
            "default_output_format": self.default_output_format,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShellPreferences:
        """Create from dictionary."""
        return cls(
            history_size=data.get("history_size", 1000),
            auto_refresh_interval=data.get("auto_refresh_interval", 2.0),
            default_output_format=data.get("default_output_format", "table"),
        )


@dataclass
class ConsoleConfig:
    """Main configuration for dmx-lan-console."""

    servers: dict[str, ServerProfile] = field(default_factory=dict)
    active_server: str = "default"
    shell: ShellPreferences = field(default_factory=ShellPreferences)
    bookmarks: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    def get_active_server(self) -> Optional[ServerProfile]:
        """Get the currently active server profile."""
        return self.servers.get(self.active_server)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "servers": {name: profile.to_dict() for name, profile in self.servers.items()},
            "active_server": self.active_server,
            "shell": self.shell.to_dict(),
            "bookmarks": self.bookmarks,
            "aliases": self.aliases,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConsoleConfig:
        """Create from dictionary."""
        servers = {
            name: ServerProfile.from_dict(profile_data)
            for name, profile_data in data.get("servers", {}).items()
        }
        shell = ShellPreferences.from_dict(data.get("shell", {}))

        return cls(
            servers=servers,
            active_server=data.get("active_server", "default"),
            shell=shell,
            bookmarks=data.get("bookmarks", {}),
            aliases=data.get("aliases", {}),
        )

    @classmethod
    def load(cls, config_file: Path = DEFAULT_CONFIG_FILE) -> ConsoleConfig:
        """Load configuration from file."""
        if not config_file.exists():
            return cls.create_default()

        try:
            with open(config_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls.from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}")
            return cls.create_default()

    def save(self, config_file: Path = DEFAULT_CONFIG_FILE) -> None:
        """Save configuration to file."""
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False, default_flow_style=False)

    @classmethod
    def create_default(cls) -> ConsoleConfig:
        """Create default configuration."""
        default_server = ServerProfile(
            name="Local Bridge",
            url="http://127.0.0.1:8000",
            api_key=None,
        )

        return cls(
            servers={"default": default_server},
            active_server="default",
            shell=ShellPreferences(),
            bookmarks={},
            aliases={},
        )

    def get_api_key_for_server(self, server_name: str) -> Optional[str]:
        """Get API key for a server, checking environment variable first."""
        # Check environment variable first
        env_key = os.environ.get("DMX_LAN_API_KEY")
        if env_key:
            return env_key

        # Fall back to configured API key for the server
        server = self.servers.get(server_name)
        return server.api_key if server else None
