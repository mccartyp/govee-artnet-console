"""Command handlers for the DMX LAN Console shell.

This package contains command handler classes that implement various
shell commands organized by domain:
- devices: Device management commands
- mappings: Channel mapping commands
- monitoring: Logging and monitoring commands
- config: Configuration and session management commands
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import ArtNetShell


class CommandHandler:
    """Base class for command handlers.

    Provides access to shell state and common utilities.
    """

    def __init__(self, shell: ArtNetShell):
        """
        Initialize the command handler.

        Args:
            shell: Reference to the ArtNetShell instance
        """
        self.shell = shell

    # Convenience properties for accessing shell state
    @property
    def client(self):
        """Get the HTTP client."""
        return self.shell.client

    @property
    def config(self):
        """Get the client configuration."""
        return self.shell.config

    @property
    def cache(self):
        """Get the response cache."""
        return self.shell.cache

    @property
    def console(self):
        """Get the Rich console."""
        return self.shell.console

    @property
    def output_buffer(self):
        """Get the output buffer."""
        return self.shell.output_buffer


__all__ = ['CommandHandler']
