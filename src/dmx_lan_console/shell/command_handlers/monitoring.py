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
        Usage: channels list [universe...]    # Default universe is 1
        Examples:
            channels list              # Show channels for universe 1
            channels list 0            # Show channels for universe 0 (Art-Net only)
            channels list 1 2 3        # Show channels for universes 1, 2, and 3
        Note: sACN (E1.31) universes are 1–63999. Art-Net supports universe 0.
              Universe 0 is Art-Net-only in this application; universes 1+ are mergeable across protocols.
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
                # Parse universe arguments (default to [1])
                universes = [1]
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
            universes: List of ArtNet universe numbers (default [1])
        """
        if universes is None:
            universes = [1]

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
            table.add_column("Device ID", style="yellow", width=20)
            table.add_column("Protocol", style="white", width=12)
            table.add_column("IP Address", style="green", width=15)
            table.add_column("Name", style="blue", width=25)
            table.add_column("Function", style="magenta", width=12)
            table.add_column("Mapping ID", style="blue", width=10, justify="right")

            # Import protocol formatter
            from ...config import format_protocol

            # Add rows for populated channels (sorted by universe, then channel number)
            for (universe, channel_num) in sorted(channel_map.keys()):
                device_id, function, mapping_id = channel_map[(universe, channel_num)]

                # Look up IP address, name, and protocol dynamically from fresh device data
                device = device_lookup.get(device_id, {})
                device_ip = device.get("ip", "N/A")
                device_name = device.get("name", "")
                device_protocol = device.get("protocol", "govee")
                name_display = device_name if device_name else "[dim]-[/]"
                protocol_display = format_protocol(device_protocol)

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
                    device_id[:20],
                    protocol_display,
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
            status_data = _handle_response(self.client.get("/status"))
            devices_data = _handle_response(self.client.get("/devices"))
            mappings_data = _handle_response(self.client.get("/mappings"))

            # Handle None responses
            if health_data is None:
                health_data = {}
            if status_data is None:
                status_data = {}
            if devices_data is None:
                devices_data = []
            if mappings_data is None:
                mappings_data = []

            # Calculate statistics
            total_devices = len(devices_data) if isinstance(devices_data, list) else 0
            online_devices = sum(1 for d in devices_data if not d.get("offline")) if isinstance(devices_data, list) else 0
            offline_devices = sum(1 for d in devices_data if d.get("offline")) if isinstance(devices_data, list) else 0
            total_mapped = sum(1 for d in devices_data if d.get("mapping_count", 0) > 0) if isinstance(devices_data, list) else 0

            # Calculate dynamic width based on devices table
            # Table columns: ID(17) + Status(6) + IP(15) + Model(6) + Name(20) + Last Seen(10) + Maps(4)
            # With padding (0,1) per column = 2 chars × 7 columns = 14
            # With separators and borders ≈ 8
            # Total ≈ 78 + 14 + 8 = 100 chars
            DASHBOARD_WIDTH = 100
            INNER_WIDTH = DASHBOARD_WIDTH - 2  # Subtract left and right borders

            # Create header
            self.shell._append_output("\n")
            header_text = "─ DMX LAN Console Dashboard "
            remaining = INNER_WIDTH - len(header_text)
            self.shell._append_output(f"[bold cyan]┌{header_text}{'─' * remaining}┐[/]\n")

            # Statistics Summary Cards using ANSI box drawing
            # Calculate padding for stats cards to center them
            # Make boxes 12 chars wide to fit "Devices" (7 chars) with padding
            stats_width = 4 * 12 + 3 * 2  # 4 boxes of 12 chars + 3 gaps of 2 spaces = 54 chars
            stats_padding = (INNER_WIDTH - stats_width) // 2

            stats_line = "[bold cyan]│[/]" + " " * stats_padding
            stats_line += f"[cyan]┌──────────┐[/]  [green]┌──────────┐[/]  [red]┌──────────┐[/]  [blue]┌──────────┐[/]"
            stats_line += " " * (INNER_WIDTH - stats_padding - stats_width) + "[bold cyan]│[/]"
            self.shell._append_output(stats_line + "\n")

            stats_line = "[bold cyan]│[/]" + " " * stats_padding
            stats_line += f"[cyan]│ Devices  │[/]  [green]│  Online  │[/]  [red]│ Offline  │[/]  [blue]│  Mapped  │[/]"
            stats_line += " " * (INNER_WIDTH - stats_padding - stats_width) + "[bold cyan]│[/]"
            self.shell._append_output(stats_line + "\n")

            stats_line = "[bold cyan]│[/]" + " " * stats_padding
            stats_line += f"[cyan]│   {total_devices:4d}   │[/]  [green]│   {online_devices:4d}   │[/]  [red]│   {offline_devices:4d}   │[/]  [blue]│   {total_mapped:4d}   │[/]"
            stats_line += " " * (INNER_WIDTH - stats_padding - stats_width) + "[bold cyan]│[/]"
            self.shell._append_output(stats_line + "\n")

            stats_line = "[bold cyan]│[/]" + " " * stats_padding
            stats_line += f"[cyan]└──────────┘[/]  [green]└──────────┘[/]  [red]└──────────┘[/]  [blue]└──────────┘[/]"
            stats_line += " " * (INNER_WIDTH - stats_padding - stats_width) + "[bold cyan]│[/]"
            self.shell._append_output(stats_line + "\n")

            self.shell._append_output(f"[bold cyan]├{'─' * INNER_WIDTH}┤[/]\n")

            # System Health Section
            subsystems = health_data.get("subsystems", {})
            if subsystems:
                health_title = "[bold]System Health[/]"
                # Calculate padding to fit within border
                title_padding = INNER_WIDTH - len("System Health") - 2
                self.shell._append_output(f"[bold cyan]│[/] {health_title}{' ' * title_padding} [bold cyan]│[/]\n")

                # Display subsystems in a compact grid format
                subsystem_names = list(subsystems.keys())
                for i in range(0, len(subsystem_names), 2):
                    line = "[bold cyan]│[/]  "
                    subsystem_content = ""

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

                    subsystem_content += f"{icon} [{style}]{name.capitalize():12s} {status.upper():10s}[/]"

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

                        subsystem_content += f"  {icon} [{style}]{name.capitalize():12s} {status.upper():10s}[/]"
                        # Two subsystems: ● Name(12) Status(10) + spacing + ● Name(12) Status(10) = 25 + 27 = 52 chars
                        content_width = 52
                    else:
                        # One subsystem: ● Name(12) Status(10) = 25 chars
                        content_width = 25

                    line += subsystem_content
                    # Calculate padding to fill to INNER_WIDTH
                    padding_needed = INNER_WIDTH - 2 - content_width  # -2 for "  " prefix (2 spaces after border)
                    line += " " * padding_needed + "[bold cyan]│[/]"

                    self.shell._append_output(line + "\n")

                self.shell._append_output(f"[bold cyan]├{'─' * INNER_WIDTH}┤[/]\n")

            # Protocol Stats Section
            protocols_stats = status_data.get("protocols", {})
            if protocols_stats:
                from ...config import format_protocol

                protocol_title = "[bold]Protocol Breakdown[/]"
                title_padding = INNER_WIDTH - len("Protocol Breakdown") - 2
                self.shell._append_output(f"[bold cyan]│[/] {protocol_title}{' ' * title_padding} [bold cyan]│[/]\n")
                self.shell._append_output("[bold cyan]│[/]" + " " * INNER_WIDTH + "[bold cyan]│[/]\n")

                # Create protocol stats table - compact format
                for protocol_name, stats in sorted(protocols_stats.items()):
                    proto_display = format_protocol(protocol_name)
                    total = stats.get("total", 0)
                    enabled = stats.get("enabled", 0)
                    offline = stats.get("offline", 0)

                    # Format: "  🔵 Govee: 5 total (4 enabled, 1 offline)"
                    content = f"  {proto_display}: {total} total ("
                    if enabled > 0:
                        content += f"[green]{enabled} enabled[/]"
                    else:
                        content += f"[dim]{enabled} enabled[/]"

                    if offline > 0:
                        content += f", [red]{offline} offline[/]"
                    else:
                        content += f", [dim]{offline} offline[/]"
                    content += ")"

                    # Calculate padding using rendered text width (markup stripped)
                    visible_length = Text.from_markup(content).cell_len
                    padding_needed = max(0, INNER_WIDTH - visible_length)

                    line = f"[bold cyan]│[/]{content}{' ' * padding_needed}[bold cyan]│[/]"
                    self.shell._append_output(line + "\n")

                self.shell._append_output("[bold cyan]│[/]" + " " * INNER_WIDTH + "[bold cyan]│[/]\n")
                self.shell._append_output(f"[bold cyan]├{'─' * INNER_WIDTH}┤[/]\n")

            # Device Table
            if isinstance(devices_data, list) and devices_data:
                devices_title = "[bold]Devices[/]"
                title_padding = INNER_WIDTH - len("Devices") - 2
                self.shell._append_output(f"[bold cyan]│[/] {devices_title}{' ' * title_padding} [bold cyan]│[/]\n")
                self.shell._append_output("[bold cyan]│[/]" + " " * INNER_WIDTH + "[bold cyan]│[/]\n")

                # Create devices table with Rich - no box, will be contained in dashboard borders
                devices_table = Table(
                    show_header=True,
                    header_style="bold magenta",
                    box=None,
                    padding=(0, 1),
                    width=INNER_WIDTH - 2,  # Fit within dashboard borders with left padding
                )
                devices_table.add_column("ID", style="cyan", no_wrap=True, width=17)
                devices_table.add_column("Status", justify="center", width=6, no_wrap=True, overflow="ignore")
                devices_table.add_column("IP", style="dim", no_wrap=True, width=15)
                devices_table.add_column("Model", style="yellow", no_wrap=True, width=6)
                devices_table.add_column("Name", style="green", no_wrap=True, width=20)
                devices_table.add_column("Last Seen", style="dim", no_wrap=True, width=10)
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

                    # Status indicator using Text objects (column styles work with force_terminal)
                    if offline:
                        status = Text("● Off", style="red")
                    elif stale:
                        status = Text("● Stale", style="dim")
                    else:
                        status = Text("● On", style="green")

                    # Format last seen as relative time
                    last_seen_str = "-"
                    if last_seen:
                        try:
                            from datetime import datetime, timezone
                            dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                            # Ensure dt is timezone-aware in UTC
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            else:
                                dt = dt.astimezone(timezone.utc)
                            # Get current time in UTC for accurate comparison
                            now = datetime.now(timezone.utc)
                            delta = now - dt
                            if delta.total_seconds() < 0:
                                # Timestamp is in the future (clock skew or timezone issue)
                                last_seen_str = "now"
                            elif delta.total_seconds() < 60:
                                last_seen_str = f"{int(delta.total_seconds())}s ago"
                            elif delta.total_seconds() < 3600:
                                last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                            elif delta.total_seconds() < 86400:
                                last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                            else:
                                last_seen_str = f"{int(delta.total_seconds() / 86400)}d ago"
                        except Exception:
                            # If parsing fails, show a dash instead of "unknown"
                            last_seen_str = "-"

                    # Truncate long names
                    if len(name) > 20:
                        name = name[:17] + "..."

                    # Truncate device ID for display
                    display_id = device_id
                    if len(display_id) > 17:
                        display_id = display_id[:14] + "..."

                    # Use plain values - column styles work with force_terminal rendering
                    devices_table.add_row(
                        display_id,
                        status,
                        ip or "-",
                        model or "-",
                        name or "-",
                        last_seen_str,
                        str(mapping_count),
                    )

                if len(sorted_devices) > 10:
                    devices_table.add_row(
                        f"[dim]... and {len(sorted_devices) - 10} more[/]",
                        "", "", "", "", "", ""
                    )

                # Render table to string and wrap with borders
                # Use force_terminal=True like help command for proper color rendering
                from io import StringIO
                from rich.console import Console
                from prompt_toolkit.document import Document
                import re

                string_io = StringIO()
                temp_console = Console(file=string_io, width=INNER_WIDTH - 2, legacy_windows=False, force_terminal=True)
                temp_console.print(devices_table)
                table_lines = string_io.getvalue().rstrip().split('\n')

                # Output each line wrapped in borders using direct buffer manipulation
                # (like help command, to avoid double-rendering through _append_output)
                for line in table_lines:
                    # Calculate visible width (remove ANSI codes to measure)
                    visible_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                    padding_needed = INNER_WIDTH - 2 - len(visible_line)
                    if padding_needed < 0:
                        padding_needed = 0

                    # Render borders with force_terminal
                    border_buf = StringIO()
                    border_console = Console(file=border_buf, force_terminal=True, width=self.shell.console.width, legacy_windows=False)
                    border_console.print(f"[bold cyan]│[/] ", end="")
                    left_border = border_buf.getvalue()

                    border_buf = StringIO()
                    border_console = Console(file=border_buf, force_terminal=True, width=self.shell.console.width, legacy_windows=False)
                    border_console.print(f"{' ' * padding_needed} [bold cyan]│[/]")
                    right_border = border_buf.getvalue()

                    # Combine and append directly to buffer
                    full_line = left_border + line + right_border
                    current_text = self.shell.output_buffer.text
                    new_text = current_text + full_line
                    cursor_pos = len(new_text) if self.shell.follow_tail else min(self.shell.output_buffer.cursor_position, len(new_text))
                    self.shell.output_buffer.set_document(
                        Document(text=new_text, cursor_position=cursor_pos),
                        bypass_readonly=True
                    )

                self.shell.app.invalidate()

                self.shell._append_output("[bold cyan]│[/]" + " " * INNER_WIDTH + "[bold cyan]│[/]\n")

            self.shell._append_output(f"[bold cyan]└{'─' * INNER_WIDTH}┘[/]\n")
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
                last_seen_str = "-"
                if last_seen:
                    try:
                        from datetime import datetime, timezone
                        dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        # Ensure dt is timezone-aware in UTC
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        # Get current time in UTC for accurate comparison
                        now = datetime.now(timezone.utc)
                        delta = now - dt
                        if delta.total_seconds() < 0:
                            # Timestamp is in the future (clock skew or timezone issue)
                            last_seen_str = "now"
                        elif delta.total_seconds() < 60:
                            last_seen_str = f"{int(delta.total_seconds())}s ago"
                        elif delta.total_seconds() < 3600:
                            last_seen_str = f"{int(delta.total_seconds() / 60)}m ago"
                        elif delta.total_seconds() < 86400:
                            last_seen_str = f"{int(delta.total_seconds() / 3600)}h ago"
                        else:
                            last_seen_str = f"{int(delta.total_seconds() / 86400)}d ago"
                    except Exception:
                        # If parsing fails, show a dash instead of "unknown"
                        last_seen_str = "-"

                devices_table.add_row(
                    device_id,
                    status,
                    ip or "-",
                    model or "-",
                    name or "-",
                    last_seen_str,
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
