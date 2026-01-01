"""Monitoring and logging command handlers."""

from __future__ import annotations

import asyncio
import shlex
from typing import Any

from rich import box
from rich.table import Table
from rich.text import Text

from ...cli import _handle_response, _print_output
from ..ui_components import FIELD_DESCRIPTIONS
from . import CommandHandler


class MonitoringCommandHandler(CommandHandler):
    """Handler for monitoring, logging, and channel commands."""

    def do_channels(self, arg: str) -> None:
        """
        Channel commands: list channels for one or more universes.
        Usage: channels list [universe...]    # Default universe is 0
        Examples:
            channels list              # Show channels for universe 0
            channels list 1            # Show channels for universe 1
            channels list 0 1 2        # Show channels for universes 0, 1, and 2
        """
        if not self.client:
            self.shell._append_output("[red]Not connected. Use 'connect' first.[/]" + "\n")
            return

        # Handle help aliases: channels --help, channels ?
        if arg.strip() in ("--help", "?"):
            self.shell.do_help("channels")
            return

        args = shlex.split(arg)
        if not args:
            self.shell._append_output("[yellow]Usage: channels list [universe...][/]" + "\n")
            return

        command = args[0]

        try:
            if command == "list":
                # Parse universe arguments (default to [0])
                universes = [0]
                if len(args) > 1:
                    # Parse one or more universe numbers
                    try:
                        universes = [int(u) for u in args[1:]]
                    except ValueError as e:
                        self.shell._append_output(f"[red]Invalid universe number: {e}[/]\n")
                        return

                self._show_channels_list(universes)
            else:
                self.shell._append_output(f"[red]Unknown command: channels {arg}[/]" + "\n")
                self.shell._append_output("[yellow]Try: channels list [universe...][/]" + "\n")
        except Exception as exc:
            self.shell._handle_error(exc, "channels")

    def _show_channels_list(self, universes: list[int] = None) -> None:
        """Show Artnet channels for the specified universe(s).

        Args:
            universes: List of ArtNet universe numbers (default [0])
        """
        if universes is None:
            universes = [0]

        try:
            # Fetch mappings and devices without caching for fresh IP data
            mappings_response = self.shell._cached_get("/mappings", use_cache=False)
            mappings = _handle_response(mappings_response)

            devices_response = self.shell._cached_get("/devices", use_cache=False)
            devices = _handle_response(devices_response)

            # Create device lookup by ID
            device_lookup = {d["id"]: d for d in devices} if devices else {}

            # Filter mappings for the specified universes
            universe_mappings = [m for m in mappings if m.get("universe") in universes]

            if not universe_mappings:
                universes_str = ", ".join(str(u) for u in universes)
                self.shell._append_output(f"[yellow]No mappings found for universe(s) {universes_str}[/]\n")
                return

            # Build channel map with universe information
            # channel_map: {(universe, channel_num): (device_id, function, mapping_id)}
            channel_map = {}

            # Channel function names for common templates
            TEMPLATE_FUNCTIONS = {
                "rgb": ["Red", "Green", "Blue"],
                "rgbw": ["Red", "Green", "Blue", "White"],
                "rgbww": ["Red", "Green", "Blue", "Warm White", "Cool White"],
                "brightness": ["Dimmer"],
                "dimmer": ["Dimmer"],
                "cct": ["Color Temp", "Dimmer"],
                "rgbcct": ["Red", "Green", "Blue", "Color Temp", "Dimmer"],
            }

            for mapping in universe_mappings:
                device_id = mapping.get("device_id", "N/A")
                mapping_id = mapping.get("id", "N/A")
                universe = mapping.get("universe", 0)
                start_channel = mapping.get("channel", 1)
                channel_length = mapping.get("length", 1)
                fields_list = mapping.get("fields", [])

                # Determine channel functions from the fields list
                # Try to match against known templates, otherwise use the field names directly
                fields_key = "".join(fields_list).lower() if fields_list else ""
                functions = TEMPLATE_FUNCTIONS.get(fields_key, [])

                # If no template match, derive functions from individual field names
                if not functions and fields_list:
                    # Map individual fields to display names
                    field_display = {
                        "r": "Red", "g": "Green", "b": "Blue", "w": "White",
                        "brightness": "Dimmer", "temperature": "Color Temp", "ct": "Color Temp"
                    }
                    functions = [field_display.get(f, f.capitalize()) for f in fields_list]
                elif not functions:
                    # Fallback for unknown mappings
                    functions = [f"Ch{i+1}" for i in range(channel_length)]

                # Populate channel map
                for i in range(channel_length):
                    channel_num = start_channel + i
                    if 1 <= channel_num <= 512:
                        function = functions[i] if i < len(functions) else f"Ch{i+1}"
                        # Store with (universe, channel) as key, (device_id, function, mapping_id) as value
                        channel_map[(universe, channel_num)] = (device_id, function, mapping_id)

            if not channel_map:
                universes_str = ", ".join(str(u) for u in universes)
                self.shell._append_output(f"[yellow]No channels populated for universe(s) {universes_str}[/]\n")
                return

            # Create table with unicode borders
            universes_str = ", ".join(str(u) for u in sorted(universes))
            table = Table(
                title=Text(f"Artnet Channels - Universe {universes_str}", justify="center"),
                show_header=True,
                header_style="bold cyan",
                box=box.ROUNDED
            )
            table.add_column("Universe", style="dim", width=8, justify="right")
            table.add_column("Channel", style="cyan", width=8, justify="right")
            table.add_column("Device ID", style="yellow", width=23)
            table.add_column("IP Address", style="green", width=15)
            table.add_column("Name", style="blue", width=30)
            table.add_column("Function", style="magenta", width=15)
            table.add_column("Mapping ID", style="blue", width=12, justify="right")

            # Add rows for populated channels (sorted by universe, then channel number)
            for (universe, channel_num) in sorted(channel_map.keys()):
                device_id, function, mapping_id = channel_map[(universe, channel_num)]

                # Look up IP address and name dynamically from fresh device data
                device = device_lookup.get(device_id, {})
                device_ip = device.get("ip", "N/A")
                device_name = device.get("name", "")
                name_display = device_name if device_name else "[dim]-[/]"

                # Apply color coding to functions
                if "Red" in function:
                    function_style = "[red]" + function + "[/]"
                elif "Green" in function:
                    function_style = "[green]" + function + "[/]"
                elif "Blue" in function:
                    function_style = "[blue]" + function + "[/]"
                elif "White" in function or "Brightness" in function or "Dimmer" in function:
                    function_style = "[white]" + function + "[/]"
                elif "Temp" in function or "CCT" in function:
                    function_style = "[yellow]" + function + "[/]"
                else:
                    function_style = function

                table.add_row(
                    str(universe),
                    str(channel_num),
                    device_id[:23],
                    device_ip,
                    name_display,
                    function_style,
                    str(mapping_id)
                )

            self.shell._append_output(table)

            # Calculate summary statistics
            total_channels = len(channel_map)
            channel_nums = [ch for (u, ch) in channel_map.keys()]
            min_channel = min(channel_nums) if channel_nums else 0
            max_channel = max(channel_nums) if channel_nums else 0

            self.shell._append_output(f"\n[dim]Total: {total_channels} populated channel(s)[/]\n")
            self.shell._append_output(f"[dim]Channel range: {min_channel} - {max_channel}[/]\n")

        except Exception as exc:
            self.shell._append_output(f"[red]Error fetching channels: {exc}[/]\n")

    def do_logs(self, arg: str) -> None:
        """
        View logs and events from the bridge.
        Usage: logs view [--level LEVEL] [--logger LOGGER]
               logs tail [--level LEVEL] [--logger LOGGER]
               logs events [--type TYPE]
               logs search PATTERN [--regex] [--level LEVEL] [--logger LOGGER]
        Examples:
            logs view
            logs view --level ERROR
            logs view --logger govee.discovery
            logs view --level ERROR --logger govee.api
            logs tail
            logs tail --level ERROR
            logs events
            logs events --type device
            logs events --type mapping
            logs search "device discovered"
            logs search "error.*timeout" --regex
            logs search "error" --level ERROR --logger govee.api
        """
        if not self.client:
            self.shell._append_output("[red]Not connected. Use 'connect' first.[/]" + "\n")
            return

        # Handle help aliases: logs --help, logs ?
        if arg.strip() in ("--help", "?"):
            self.shell.do_help("logs")
            return

        args = shlex.split(arg)

        try:
            # Check if this is a tail command
            if args and args[0] == "tail":
                self._logs_tail(args[1:])
                return

            # Check if this is a view command
            if args and args[0] == "view":
                self._logs_view(args[1:])
                return

            # Check if this is an events command
            if args and args[0] == "events":
                self._logs_events(args[1:])
                return

            # Check if this is a search command
            if args and args[0] == "search":
                self._logs_search(args[1:])
                return

            # Default: show usage
            self.shell._append_output("[yellow]Usage: logs view|tail|events|search[/]" + "\n")
            self.shell._append_output("[dim]Try 'logs view' for paginated log viewer[/]" + "\n")
            self.shell._append_output("[dim]Try 'logs tail' for real-time log streaming[/]" + "\n")
            self.shell._append_output("[dim]Try 'logs events' for real-time event notifications[/]" + "\n")
            self.shell._append_output("[dim]Try 'logs search PATTERN' for searching logs[/]" + "\n")

        except Exception as exc:
            self.shell._handle_error(exc, "logs")

    def _logs_view(self, args: list[str]) -> None:
        """
        View logs in paginated view mode.

        Args:
            args: Command arguments (filters)
        """
        # Parse filters
        level_filter = "INFO"  # Default to INFO (excludes DEBUG)
        logger_filter = None

        i = 0
        while i < len(args):
            if args[i] == "--level" and i + 1 < len(args):
                level_filter = args[i + 1].upper()
                i += 1
            elif args[i] == "--logger" and i + 1 < len(args):
                logger_filter = args[i + 1]
                i += 1
            i += 1

        # Enter log view mode (async)
        asyncio.create_task(self.shell._enter_log_view_mode(level=level_filter, logger=logger_filter))

    def _logs_search(self, args: list[str]) -> None:
        """
        Search logs and display in view mode.

        Args:
            args: Command arguments (pattern and filters)
        """
        if len(args) < 1:
            self.shell._append_output("[yellow]Usage: logs search PATTERN [--regex] [--level LEVEL] [--logger LOGGER][/]" + "\n")
            return

        pattern = args[0]
        regex = False
        level_filter = "INFO"  # Default to INFO
        logger_filter = None

        # Parse optional flags
        i = 1
        while i < len(args):
            if args[i] == "--regex":
                regex = True
            elif args[i] == "--level" and i + 1 < len(args):
                level_filter = args[i + 1].upper()
                i += 1
            elif args[i] == "--logger" and i + 1 < len(args):
                logger_filter = args[i + 1]
                i += 1
            i += 1

        # Enter log view mode with search (async)
        asyncio.create_task(
            self.shell._enter_log_view_mode(
                level=level_filter,
                logger=logger_filter,
                search_pattern=pattern,
                search_regex=regex,
            )
        )

    def _logs_tail(self, args: list[str]) -> None:
        """
        Tail logs in real-time using WebSocket.

        Args:
            args: Command arguments (filters)
        """
        # Parse filters
        level_filter = None
        logger_filter = None

        i = 0
        while i < len(args):
            if args[i] == "--level" and i + 1 < len(args):
                level_filter = args[i + 1]
                i += 1
            elif args[i] == "--logger" and i + 1 < len(args):
                logger_filter = args[i + 1]
                i += 1
            i += 1

        # Enter log tail mode (async)
        asyncio.create_task(self.shell._enter_log_tail_mode(level=level_filter, logger=logger_filter))

    def _logs_events(self, args: list[str]) -> None:
        """
        View real-time event stream.

        Args:
            args: Command arguments (filters)
        """
        # Parse filter
        event_type_filter = None

        i = 0
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                event_type_filter = args[i + 1].lower()
                # Validate event type
                if event_type_filter not in ("device", "mapping", "health"):
                    self.shell._append_output(f"[yellow]Invalid event type: {event_type_filter}[/]\n")
                    self.shell._append_output("[dim]Valid types: device, mapping, health[/]\n")
                    return
                i += 1
            i += 1

        # Enter events mode (async)
        asyncio.create_task(self.shell._enter_events_mode(event_type=event_type_filter))

    def do_monitor(self, arg: str) -> None:
        """
        Real-time monitoring commands.
        Usage: monitor dashboard - Show comprehensive dashboard with health and devices
               monitor devices   - Show detailed device table
               monitor stats     - Show system statistics
        """
        if not self.client:
            self.shell._append_output("[red]Not connected. Use 'connect' first.[/]" + "\n")
            return

        # Handle help aliases: monitor --help, monitor ?
        if arg.strip() in ("--help", "?"):
            self.shell.do_help("monitor")
            return

        args = shlex.split(arg)
        if not args:
            self.shell._append_output("[yellow]Usage: monitor dashboard|devices|stats[/]" + "\n")
            return

        command = args[0]

        try:
            if command == "dashboard":
                self._monitor_dashboard()
            elif command == "devices":
                self._monitor_devices()
            elif command == "stats":
                self._monitor_stats()
            else:
                self.shell._append_output(f"[red]Unknown monitor command: {command}[/]" + "\n")
                self.shell._append_output("[yellow]Try: monitor dashboard, monitor devices, monitor stats[/]" + "\n")
        except Exception as exc:
            self.shell._handle_error(exc, "monitor")

    def _monitor_dashboard(self) -> None:
        """Display comprehensive dashboard with health, devices, and statistics."""
        try:
            # Fetch data in parallel
            self.shell._append_output("[bold cyan]Fetching dashboard data...[/]\n")
            health_data = _handle_response(self.client.get("/health"))
            devices_data = _handle_response(self.client.get("/devices"))
            mappings_data = _handle_response(self.client.get("/mappings"))

            # Handle None responses
            if health_data is None:
                health_data = {}
            if devices_data is None:
                devices_data = []
            if mappings_data is None:
                mappings_data = []

            # Calculate statistics
            total_devices = len(devices_data) if isinstance(devices_data, list) else 0
            online_devices = sum(1 for d in devices_data if not d.get("offline")) if isinstance(devices_data, list) else 0
            offline_devices = sum(1 for d in devices_data if d.get("offline")) if isinstance(devices_data, list) else 0
            total_mappings = len(mappings_data) if isinstance(mappings_data, list) else 0

            # Create header (total width 66 chars)
            self.shell._append_output("\n")
            self.shell._append_output("[bold cyan]┌─ Govee ArtNet Bridge Dashboard " + "─" * 31 + "┐[/]\n")

            # Statistics Summary Cards using ANSI box drawing
            stats_line = "│  "
            stats_line += f"[cyan]┌─────────┐[/]  [green]┌─────────┐[/]  [red]┌─────────┐[/]  [blue]┌─────────┐[/]"
            stats_line += " " * 20 + "│"
            self.shell._append_output(stats_line + "\n")

            stats_line = "│  "
            stats_line += f"[cyan]│ Devices │[/]  [green]│ Online  │[/]  [red]│ Offline │[/]  [blue]│ Map'ngs │[/]"
            stats_line += " " * 20 + "│"
            self.shell._append_output(stats_line + "\n")

            stats_line = "│  "
            stats_line += f"[cyan]│   {total_devices:3d}   │[/]  [green]│   {online_devices:3d}   │[/]  [red]│   {offline_devices:3d}   │[/]  [blue]│   {total_mappings:3d}   │[/]"
            stats_line += " " * 20 + "│"
            self.shell._append_output(stats_line + "\n")

            stats_line = "│  "
            stats_line += f"[cyan]└─────────┘[/]  [green]└─────────┘[/]  [red]└─────────┘[/]  [blue]└─────────┘[/]"
            stats_line += " " * 20 + "│"
            self.shell._append_output(stats_line + "\n")

            self.shell._append_output("[bold cyan]├" + "─" * 64 + "┤[/]\n")

            # System Health Section
            subsystems = health_data.get("subsystems", {})
            if subsystems:
                self.shell._append_output("│ [bold]System Health[/]" + " " * 49 + "│\n")

                # Display subsystems in a compact grid format
                subsystem_names = list(subsystems.keys())
                for i in range(0, len(subsystem_names), 2):
                    line = "│  "

                    # First subsystem in pair
                    name = subsystem_names[i]
                    data = subsystems[name]
                    status = data.get("status", "unknown").lower()

                    if status == "ok":
                        icon = "[green]●[/]"
                        style = "green"
                    elif status == "degraded":
                        icon = "[yellow]●[/]"
                        style = "yellow"
                    elif status == "suppressed":
                        icon = "[red]●[/]"
                        style = "red"
                    elif status == "recovering":
                        icon = "[cyan]●[/]"
                        style = "cyan"
                    else:
                        icon = "[white]●[/]"
                        style = "white"

                    line += f"{icon} [{style}]{name.capitalize():12s} {status.upper():10s}[/]"

                    # Second subsystem in pair (if exists)
                    if i + 1 < len(subsystem_names):
                        name = subsystem_names[i + 1]
                        data = subsystems[name]
                        status = data.get("status", "unknown").lower()

                        if status == "ok":
                            icon = "[green]●[/]"
                            style = "green"
                        elif status == "degraded":
                            icon = "[yellow]●[/]"
                            style = "yellow"
                        elif status == "suppressed":
                            icon = "[red]●[/]"
                            style = "red"
                        elif status == "recovering":
                            icon = "[cyan]●[/]"
                            style = "cyan"
                        else:
                            icon = "[white]●[/]"
                            style = "white"

                        line += f"  {icon} [{style}]{name.capitalize():12s} {status.upper():10s}[/]"
                        # Padding for 2 subsystems (using colored symbol ● which is 1 char wide)
                        line += " " * 10 + "│"
                    else:
                        # Padding for 1 subsystem only
                        line += " " * 37 + "│"

                    self.shell._append_output(line + "\n")

                self.shell._append_output("[bold cyan]├" + "─" * 64 + "┤[/]\n")

            # Device Table
            if isinstance(devices_data, list) and devices_data:
                self.shell._append_output("│ [bold]Devices[/]" + " " * 55 + "│\n")

                # Create devices table with Rich
                devices_table = Table(
                    show_header=True,
                    header_style="bold magenta",
                    box=box.SIMPLE,
                    padding=(0, 1),
                )
                devices_table.add_column("ID", style="cyan", no_wrap=True, width=17)
                devices_table.add_column("Status", justify="center", width=6)
                devices_table.add_column("IP", style="dim", width=15)
                devices_table.add_column("Model", style="yellow", width=6)
                devices_table.add_column("Name", style="green", width=20)
                devices_table.add_column("Last Seen", style="dim", width=10)
                devices_table.add_column("Maps", justify="right", width=4)

                # Sort devices: online first, then by ID
                sorted_devices = sorted(devices_data, key=lambda d: (d.get("offline", False), d.get("id", "")))

                # Show up to 10 devices
                for device in sorted_devices[:10]:
                    device_id = device.get("id", "unknown") or "unknown"
                    offline = device.get("offline", False)
                    stale = device.get("stale", False)
                    ip = device.get("ip") or ""
                    model = device.get("model_number") or ""
                    name = device.get("description") or ""
                    last_seen = device.get("last_seen") or ""
                    mapping_count = device.get("mapping_count", 0) or 0

                    # Status indicator
                    if offline:
                        status = "[red]● Off[/]"
                    elif stale:
                        status = "[dim]● Stale[/]"
                    else:
                        status = "[green]● On[/]"

                    # Format last seen as relative time
                    last_seen_str = ""
                    if last_seen:
                        try:
                            from datetime import datetime, timezone
                            dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                            delta = now - dt
                            if delta.total_seconds() < 60:
                                last_seen_str = f"{int(delta.total_seconds())}s ago"
                            elif delta.total_seconds() < 3600:
                                last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                            elif delta.total_seconds() < 86400:
                                last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                            else:
                                last_seen_str = f"{int(delta.total_seconds() / 86400)}d ago"
                        except Exception:
                            last_seen_str = "unknown"

                    # Truncate long names
                    if len(name) > 20:
                        name = name[:17] + "..."

                    # Truncate device ID for display
                    display_id = device_id
                    if len(display_id) > 17:
                        display_id = display_id[:14] + "..."

                    devices_table.add_row(
                        display_id,
                        status,
                        ip or "-",
                        model or "-",
                        name or "-",
                        last_seen_str or "-",
                        str(mapping_count),
                    )

                if len(sorted_devices) > 10:
                    devices_table.add_row(
                        f"[dim]... and {len(sorted_devices) - 10} more[/]",
                        "", "", "", "", "", ""
                    )

                self.shell._append_output(devices_table)
                self.shell._append_output("\n")

            self.shell._append_output("[bold cyan]└" + "─" * 64 + "┘[/]\n")
            self.shell._append_output("\n")

        except Exception as exc:
            self.shell._append_output(f"[bold red]Error fetching dashboard:[/] {exc}\n")

    def _monitor_devices(self) -> None:
        """Display detailed device table with all discovered devices."""
        try:
            self.shell._append_output("[bold cyan]Fetching device data...[/]\n")
            devices_data = _handle_response(self.client.get("/devices"))

            if not isinstance(devices_data, list):
                self.shell._append_output("[yellow]No devices found.[/]\n")
                return

            if not devices_data:
                self.shell._append_output("[yellow]No devices discovered yet.[/]\n")
                return

            # Create header
            self.shell._append_output("\n")
            self.shell._append_output("[bold cyan]" + "═" * 80 + "[/]\n")
            self.shell._append_output("[bold cyan]Devices Monitor[/]\n")
            self.shell._append_output("[bold cyan]" + "═" * 80 + "[/]\n\n")

            # Create detailed devices table
            devices_table = Table(
                show_header=True,
                header_style="bold magenta",
                box=box.ROUNDED,
                padding=(0, 1),
            )
            devices_table.add_column("Device ID", style="cyan", no_wrap=True)
            devices_table.add_column("Status", justify="center", width=8)
            devices_table.add_column("IP Address", style="dim")
            devices_table.add_column("Model", style="yellow", width=7)
            devices_table.add_column("Name", style="green")
            devices_table.add_column("Last Seen", style="dim", width=12)
            devices_table.add_column("Mappings", justify="right", width=8)

            # Sort devices: online first, then by ID
            sorted_devices = sorted(devices_data, key=lambda d: (d.get("offline", False), d.get("id", "")))

            for device in sorted_devices:
                device_id = device.get("id", "unknown") or "unknown"
                offline = device.get("offline", False)
                stale = device.get("stale", False)
                ip = device.get("ip") or ""
                model = device.get("model_number") or ""
                name = device.get("description") or ""
                last_seen = device.get("last_seen") or ""
                mapping_count = device.get("mapping_count", 0) or 0

                # Status indicator with colored symbol
                if offline:
                    status = "[red]● Offline[/]"
                elif stale:
                    status = "[dim]● Stale[/]"
                else:
                    status = "[green]● Online[/]"

                # Format last seen as relative time
                last_seen_str = ""
                if last_seen:
                    try:
                        from datetime import datetime, timezone
                        dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        delta = now - dt
                        if delta.total_seconds() < 60:
                            last_seen_str = f"{int(delta.total_seconds())}s ago"
                        elif delta.total_seconds() < 3600:
                            last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                        elif delta.total_seconds() < 86400:
                            last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                        else:
                            last_seen_str = f"{int(delta.total_seconds() / 86400)}d ago"
                    except Exception:
                        last_seen_str = "unknown"

                devices_table.add_row(
                    device_id,
                    status,
                    ip or "-",
                    model or "-",
                    name or "-",
                    last_seen_str or "-",
                    str(mapping_count),
                )

            self.shell._append_output(devices_table)
            self.shell._append_output("\n")

            # Summary
            total = len(sorted_devices)
            online = sum(1 for d in sorted_devices if not d.get("offline"))
            offline_count = sum(1 for d in sorted_devices if d.get("offline"))

            self.shell._append_output(f"[dim]Total: {total} devices | ")
            self.shell._append_output(f"[green]{online} online[/] | ")
            self.shell._append_output(f"[red]{offline_count} offline[/]\n\n")

        except Exception as exc:
            self.shell._append_output(f"[bold red]Error fetching devices:[/] {exc}\n")

    def _monitor_stats(self) -> None:
        """Display system statistics."""
        self.shell._append_output("[cyan]Fetching statistics...[/]" + "\n")
        try:
            status_data = _handle_response(self.client.get("/status"))
            self.shell._capture_api_output(_print_output, status_data, self.config.output)
        except Exception as exc:
            self.shell._append_output(f"[red]Error fetching stats: {exc}[/]" + "\n")
