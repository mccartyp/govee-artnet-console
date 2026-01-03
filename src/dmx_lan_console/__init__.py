"""DMX LAN Console - Interactive CLI for managing multi-protocol smart lighting devices.

This package provides a standalone CLI tool for controlling and monitoring
smart lighting devices (Govee, LIFX, etc.) via the DMX LAN Bridge REST API.
"""

__version__ = "2.0.0"
__author__ = "mccartyp"

from .cli import ClientConfig, main

__all__ = ["ClientConfig", "main", "__version__"]
