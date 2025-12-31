"""Controllers for real-time shell features.

This module contains controllers for real-time features:
- ConnectionState: WebSocket connection state enum
- LogTailController: Real-time log streaming via WebSocket
- WatchController: Periodic refresh of watch targets
- LogViewController: Paginated log viewing with filtering and search
"""

from __future__ import annotations

import asyncio
import json
import shutil
import textwrap
from collections import deque
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

import websockets
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from ..shell.core import GoveeShell


class ConnectionState(Enum):
    """WebSocket connection states for log tailing."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class LogTailController:
    """
    Controller for real-time log tailing via WebSocket.

    Features:
    - Async WebSocket connection management
    - Automatic reconnection with exponential backoff
    - Filter management (level, logger)
    - Batched UI updates for performance
    - Memory-limited buffer (last 500k chars)
    - Follow-tail mode with manual scroll detection
    """

    # Performance tuning
    MAX_BUFFER_CHARS = 500_000  # ~500KB of log text
    BATCH_INTERVAL = 0.1  # 100ms batching interval
    MAX_RECONNECT_DELAY = 10.0  # Max backoff delay

    def __init__(self, app: Application, log_buffer: Buffer, server_url: str):
        """
        Initialize the log tail controller.

        Args:
            app: The prompt_toolkit Application instance
            log_buffer: Buffer to append log lines to
            server_url: Base HTTP server URL (will be converted to WebSocket)
        """
        self.app = app
        self.log_buffer = log_buffer
        self.server_url = server_url

        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_task: Optional[asyncio.Task] = None
        self.batch_task: Optional[asyncio.Task] = None

        # Filter state
        self.level_filter: Optional[str] = None
        self.logger_filter: Optional[str] = None

        # Follow-tail mode (auto-scroll to newest)
        self.follow_tail = True

        # Pending log lines for batched updates
        self._pending_lines: deque[str] = deque()
        self._lock = asyncio.Lock()

        # Reconnection state
        self._reconnect_delay = 1.0
        self._should_reconnect = True

    @property
    def is_active(self) -> bool:
        """Check if log tailing is currently active."""
        return self.ws_task is not None and not self.ws_task.done()

    @property
    def ws_url(self) -> str:
        """Get the WebSocket URL for log streaming."""
        url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{url}/logs/stream"

    async def start(self, level: Optional[str] = None, logger: Optional[str] = None) -> None:
        """
        Start log tailing with optional filters.

        Args:
            level: Log level filter (e.g., "INFO", "ERROR")
            logger: Logger name filter (e.g., "govee.discovery")
        """
        if self.is_active:
            return

        self.level_filter = level
        self.logger_filter = logger
        self._should_reconnect = True
        self._reconnect_delay = 1.0

        # Start WebSocket connection task
        self.ws_task = asyncio.create_task(self._ws_loop())

        # Start UI batch update task
        self.batch_task = asyncio.create_task(self._batch_update_loop())

    async def stop(self) -> None:
        """Stop log tailing and close WebSocket connection."""
        self._should_reconnect = False

        # Cancel tasks
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        if self.batch_task and not self.batch_task.done():
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self.state = ConnectionState.DISCONNECTED
        self.ws_task = None
        self.batch_task = None

    async def set_filters(self, level: Optional[str] = None, logger: Optional[str] = None) -> None:
        """
        Update filters and send to server.

        Args:
            level: Log level filter (None to clear)
            logger: Logger name filter (None to clear)
        """
        self.level_filter = level
        self.logger_filter = logger

        # Send filter update to WebSocket if connected
        if self.websocket and self.state == ConnectionState.CONNECTED:
            try:
                filters = {}
                if level:
                    filters["level"] = level
                if logger:
                    filters["logger"] = logger

                await self.websocket.send(json.dumps(filters))
            except Exception:
                pass  # Will reconnect if needed

    async def clear_filters(self) -> None:
        """Clear all filters."""
        await self.set_filters(level=None, logger=None)

    def append_log_line(self, line: str) -> None:
        """
        Append a log line to the pending queue for batched UI update.

        Args:
            line: Formatted log line to append
        """
        self._pending_lines.append(line)

    def toggle_follow_tail(self) -> bool:
        """
        Toggle follow-tail mode.

        Returns:
            New follow_tail state
        """
        self.follow_tail = not self.follow_tail
        if self.follow_tail:
            # Jump to bottom
            self.log_buffer.cursor_position = len(self.log_buffer.text)
        return self.follow_tail

    def enable_follow_tail(self) -> None:
        """Enable follow-tail mode and jump to bottom."""
        self.follow_tail = True
        self.log_buffer.cursor_position = len(self.log_buffer.text)

    async def _ws_loop(self) -> None:
        """Main WebSocket connection loop with reconnection."""
        while self._should_reconnect:
            try:
                self.state = ConnectionState.CONNECTING
                self.app.invalidate()

                # Connect to WebSocket
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                ) as websocket:
                    self.websocket = websocket
                    self.state = ConnectionState.CONNECTED
                    self._reconnect_delay = 1.0  # Reset backoff on successful connect
                    self.app.invalidate()

                    # Send initial filters if set
                    if self.level_filter or self.logger_filter:
                        filters = {}
                        if self.level_filter:
                            filters["level"] = self.level_filter
                        if self.logger_filter:
                            filters["logger"] = self.logger_filter
                        await websocket.send(json.dumps(filters))

                    # Receive and process log messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Skip ping messages
                            if data.get("type") == "ping":
                                continue

                            # Format log entry
                            timestamp = data.get("timestamp", "")
                            level = data.get("level", "INFO")
                            logger_name = data.get("logger", "")
                            message_text = data.get("message", "")
                            extra = data.get("extra", {})

                            # Format with colors (ANSI codes)
                            # Timestamp: dim white
                            # Level: color-coded
                            # Logger: cyan
                            # Message: default
                            level_colors = {
                                "DEBUG": "\033[36m",    # Cyan
                                "INFO": "\033[32m",     # Green
                                "WARNING": "\033[33m",  # Yellow
                                "ERROR": "\033[31m",    # Red
                                "CRITICAL": "\033[1;31m",  # Bold red
                            }
                            level_color = level_colors.get(level, "\033[37m")
                            reset = "\033[0m"
                            dim = "\033[2m"
                            cyan = "\033[36m"
                            magenta = "\033[35m"

                            formatted_line = (
                                f"{dim}{timestamp}{reset} "
                                f"{level_color}{level:<8}{reset} "
                                f"{cyan}{logger_name}{reset}: "
                                f"{message_text}\n"
                            )

                            # Add extras on a second line with visual connection
                            if extra and isinstance(extra, dict):
                                # Format extras as key=value pairs
                                extra_items = [f"{k}={v}" for k, v in extra.items()]
                                extra_text = " ".join(extra_items)

                                # Get terminal width for wrapping
                                terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns

                                # Prefix for extra lines: "  ╰─► " (6 visible chars)
                                prefix = f"{dim}  ╰─► {reset}"
                                # Continuation prefix for wrapped lines: "     " (5 spaces for alignment)
                                continuation_prefix = f"{dim}     {reset}"

                                # Calculate available width for text (account for prefix and some margin)
                                prefix_width = 6  # "  ╰─► "
                                available_width = max(40, terminal_width - prefix_width - 2)  # -2 for safety margin

                                # Wrap the extra text
                                wrapped_lines = textwrap.wrap(
                                    extra_text,
                                    width=available_width,
                                    break_long_words=True,
                                    break_on_hyphens=False
                                )

                                # Add wrapped lines with proper indentation
                                for i, line in enumerate(wrapped_lines):
                                    if i == 0:
                                        # First line uses the arrow prefix
                                        formatted_line += f"{prefix}{magenta}{line}{reset}\n"
                                    else:
                                        # Continuation lines use aligned spacing
                                        formatted_line += f"{continuation_prefix}{magenta}{line}{reset}\n"

                            self.append_log_line(formatted_line)

                        except json.JSONDecodeError:
                            continue
                        except Exception as exc:
                            # Log parsing errors shouldn't crash the loop
                            self.append_log_line(f"\033[31mError parsing log: {exc}\033[0m\n")

            except asyncio.CancelledError:
                break
            except Exception as exc:
                # Connection failed, set state and reconnect with backoff
                if self._should_reconnect:
                    self.state = ConnectionState.RECONNECTING
                    self.websocket = None
                    self.app.invalidate()

                    # Exponential backoff: 1s -> 2s -> 4s -> 8s -> 10s (max)
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY)
                else:
                    break

        self.state = ConnectionState.DISCONNECTED
        self.websocket = None
        self.app.invalidate()

    async def _batch_update_loop(self) -> None:
        """Batch UI updates every BATCH_INTERVAL to reduce redraw frequency."""
        try:
            while True:
                await asyncio.sleep(self.BATCH_INTERVAL)

                if self._pending_lines:
                    async with self._lock:
                        # Collect all pending lines
                        lines_to_add = "".join(self._pending_lines)
                        self._pending_lines.clear()

                    # Append to buffer
                    if lines_to_add:
                        # Get current buffer text
                        current_text = self.log_buffer.text
                        new_text = current_text + lines_to_add

                        # Trim buffer if exceeding max size
                        if len(new_text) > self.MAX_BUFFER_CHARS:
                            # Keep only the last MAX_BUFFER_CHARS characters
                            # Try to cut at a newline boundary
                            trim_point = len(new_text) - self.MAX_BUFFER_CHARS
                            newline_pos = new_text.find('\n', trim_point)
                            if newline_pos != -1:
                                new_text = new_text[newline_pos + 1:]
                            else:
                                new_text = new_text[trim_point:]

                        # Update buffer
                        # Calculate cursor position, avoiding empty line at bottom if text ends with newline
                        if self.follow_tail:
                            cursor_pos = len(new_text)
                            if new_text and new_text.endswith('\n'):
                                cursor_pos = max(0, len(new_text) - 1)
                        else:
                            cursor_pos = self.log_buffer.cursor_position

                        self.log_buffer.set_document(
                            Document(text=new_text, cursor_position=cursor_pos),
                            bypass_readonly=True
                        )

                        # Invalidate UI
                        self.app.invalidate()

        except asyncio.CancelledError:
            pass


class WatchController:
    """
    Controller for periodic watch updates with overlay window.

    Features:
    - Periodic refresh of watch targets (devices, mappings, dashboard, logs)
    - Clear and redraw overlay window at each refresh
    - Configurable refresh interval
    - Support for multiple watch targets
    """

    # Default refresh interval
    DEFAULT_REFRESH_INTERVAL = 5.0  # 5 seconds

    def __init__(self, app: Application, watch_buffer: Buffer, shell: GoveeShell):
        """
        Initialize the watch controller.

        Args:
            app: The prompt_toolkit Application instance
            watch_buffer: Buffer to display watch output
            shell: Reference to GoveeShell instance for executing commands
        """
        self.app = app
        self.watch_buffer = watch_buffer
        self.shell = shell

        # Watch state
        self.watch_target: Optional[str] = None
        self.refresh_interval = self.DEFAULT_REFRESH_INTERVAL
        self.watch_task: Optional[asyncio.Task] = None
        self._should_watch = False

    @property
    def is_active(self) -> bool:
        """Check if watch is currently active."""
        return self.watch_task is not None and not self.watch_task.done()

    async def start(self, target: str, interval: float = 5.0) -> None:
        """
        Start watching a target with periodic refreshes.

        Args:
            target: Watch target (devices, mappings, dashboard, logs)
            interval: Refresh interval in seconds
        """
        if self.is_active:
            return

        self.watch_target = target
        self.refresh_interval = interval
        self._should_watch = True

        # Start watch loop task
        self.watch_task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop watching and cancel the watch loop."""
        self._should_watch = False

        # Cancel task
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass

        self.watch_task = None
        self.watch_target = None

    def set_interval(self, interval: float) -> None:
        """
        Update the refresh interval.

        Args:
            interval: New refresh interval in seconds
        """
        self.refresh_interval = max(0.5, interval)  # Minimum 0.5s to prevent hammering

    async def _watch_loop(self) -> None:
        """Main watch loop - periodically refresh the watch target."""
        try:
            while self._should_watch:
                # Clear the watch buffer before refresh
                self.watch_buffer.set_document(Document(""), bypass_readonly=True)

                # Capture output for this refresh cycle
                output = ""

                # Add timestamp header
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                output += f"\033[1;36m╔═══════════════════════════════════════════════════════════╗\033[0m\n"
                output += f"\033[1;36m║  Watch Mode - {self.watch_target.upper():<43} ║\033[0m\n"
                output += f"\033[1;36m║  Refreshed at {timestamp:<43} ║\033[0m\n"
                output += f"\033[1;36m╚═══════════════════════════════════════════════════════════╝\033[0m\n\n"

                # Execute the watch command and capture output
                try:
                    # Save current output buffer position
                    old_output = self.shell.output_buffer.text

                    # Execute command based on target
                    if self.watch_target == "devices":
                        self.shell.device_handler._show_devices_simple()
                    elif self.watch_target == "mappings":
                        self.shell.mapping_handler._show_mappings_list()
                    elif self.watch_target == "logs":
                        self.shell.do_logs("")
                    elif self.watch_target == "dashboard":
                        self.shell.monitoring_handler._monitor_dashboard()

                    # Capture new output added to output buffer
                    new_output = self.shell.output_buffer.text
                    if len(new_output) > len(old_output):
                        # Extract only the new content
                        command_output = new_output[len(old_output):]
                        output += command_output

                        # Reset output buffer to old content (since we're showing it in watch window)
                        self.shell.output_buffer.set_document(
                            Document(text=old_output),
                            bypass_readonly=True
                        )

                except Exception as exc:
                    output += f"\033[31mError executing watch command: {exc}\033[0m\n"

                # Update watch buffer with new content
                self.watch_buffer.set_document(
                    Document(text=output, cursor_position=0),
                    bypass_readonly=True
                )

                # Invalidate UI to trigger redraw
                self.app.invalidate()

                # Wait for next refresh
                await asyncio.sleep(self.refresh_interval)

        except asyncio.CancelledError:
            pass


class LogViewController:
    """
    Controller for paginated log viewing with filtering and search.

    Features:
    - Paginated log display with navigation (PgUp/PgDn, Home/End)
    - Level filtering (DEBUG, INFO, WARNING, ERROR, CRITICAL, ALL)
    - Logger name filtering (prefix match)
    - Search mode with pattern matching and regex support
    - Auto-refresh every 5 seconds
    - Follow mode to track newest logs
    - Modal input overlays for filters and search
    """

    # Auto-refresh interval
    REFRESH_INTERVAL = 5.0  # 5 seconds

    def __init__(self, app: Application, log_view_buffer: Buffer, shell: GoveeShell):
        """
        Initialize the log view controller.

        Args:
            app: The prompt_toolkit Application instance
            log_view_buffer: Buffer to display log view output
            shell: Reference to GoveeShell instance for API calls
        """
        self.app = app
        self.log_view_buffer = log_view_buffer
        self.shell = shell

        # Pagination state
        self.current_page = 0
        self.total_pages = 0
        self.logs_per_page = 50  # Will be recalculated based on terminal height
        self.total_logs = 0
        self.current_logs: list[dict] = []

        # Filter state
        self.level_filter: Optional[str] = "INFO"  # Default: INFO (excludes DEBUG)
        self.logger_filter: Optional[str] = None

        # Search state
        self.search_pattern: Optional[str] = None
        self.search_regex: bool = False

        # Follow mode
        self.follow_mode: bool = False

        # Error state
        self.error_message: Optional[str] = None

        # Auto-refresh task
        self.refresh_task: Optional[asyncio.Task] = None
        self._should_refresh = False

        # Modal state
        self.in_modal = False
        self.modal_type: Optional[str] = None  # 'filter', 'search', 'help'
        self.modal_input: str = ""  # Current modal input text
        self.modal_cursor_pos: int = 0  # Cursor position in modal input

    @property
    def is_active(self) -> bool:
        """Check if log view is currently active."""
        return self.refresh_task is not None and not self.refresh_task.done()

    @property
    def current_offset(self) -> int:
        """Calculate current offset based on page number."""
        return self.current_page * self.logs_per_page

    @property
    def is_last_page(self) -> bool:
        """Check if currently on the last page."""
        return self.total_pages > 0 and self.current_page == self.total_pages - 1

    def calculate_logs_per_page(self) -> int:
        """Calculate how many logs fit per page based on terminal height.

        Accounts for line wrapping by assuming each log entry may span
        multiple visual rows (average 2 rows per log entry).
        """
        import shutil
        terminal_height = shutil.get_terminal_size(fallback=(80, 24)).lines
        # Reserve: toolbar (3) + prompt (1) + separator (1) + table header (3) = 8 lines
        available_lines = max(10, terminal_height - 8)
        # Assume average 2 visual rows per log entry due to wrapping
        # This ensures we don't overflow the screen
        return max(5, available_lines // 2)

    async def start(
        self,
        level: Optional[str] = "INFO",
        logger: Optional[str] = None,
        search_pattern: Optional[str] = None,
        search_regex: bool = False,
    ) -> None:
        """
        Start log view mode.

        Args:
            level: Initial level filter (INFO, WARNING, ERROR, CRITICAL, or None for ALL)
            logger: Logger name filter (prefix match)
            search_pattern: Search pattern (for search mode)
            search_regex: Whether search pattern is regex
        """
        if self.is_active:
            return

        # Set initial filters
        self.level_filter = level
        self.logger_filter = logger
        self.search_pattern = search_pattern
        self.search_regex = search_regex

        # Calculate logs per page
        self.logs_per_page = self.calculate_logs_per_page()

        # Initial load - show loading message
        self._show_loading()

        # Fetch initial logs
        await self._fetch_logs()

        # Start on last page
        if self.total_pages > 0:
            self.current_page = self.total_pages - 1

        # Render initial view
        await self._render()

        # Start auto-refresh
        self._should_refresh = True
        self.refresh_task = asyncio.create_task(self._refresh_loop())

    async def stop(self) -> None:
        """Stop log view mode and cleanup."""
        self._should_refresh = False

        # Cancel refresh task
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass

        self.refresh_task = None

    def cycle_level_filter(self) -> None:
        """Cycle through level filters: INFO → WARNING → ERROR → CRITICAL → ALL → INFO."""
        levels = ["INFO", "WARNING", "ERROR", "CRITICAL", None]  # None = ALL
        try:
            current_idx = levels.index(self.level_filter)
            next_idx = (current_idx + 1) % len(levels)
            self.level_filter = levels[next_idx]
        except ValueError:
            self.level_filter = "INFO"

        # Reset to first page when filter changes
        self.current_page = 0

    def set_logger_filter(self, logger: Optional[str]) -> None:
        """
        Set logger filter.

        Args:
            logger: Logger name prefix or None to clear
        """
        self.logger_filter = logger.strip() if logger and logger.strip() else None
        # Reset to first page when filter changes
        self.current_page = 0

    def set_search_pattern(self, pattern: Optional[str], regex: bool = False) -> None:
        """
        Set search pattern.

        Args:
            pattern: Search pattern or None to clear
            regex: Whether pattern is regex
        """
        self.search_pattern = pattern.strip() if pattern and pattern.strip() else None
        self.search_regex = regex
        # Reset to first page when search changes
        self.current_page = 0

    def toggle_follow_mode(self) -> None:
        """Toggle follow mode on/off."""
        self.follow_mode = not self.follow_mode
        if self.follow_mode and self.total_pages > 0:
            # Jump to last page when enabling follow
            self.current_page = self.total_pages - 1

    def navigate_page(self, direction: str) -> None:
        """
        Navigate to a different page.

        Args:
            direction: 'next', 'prev', 'first', 'last'
        """
        old_page = self.current_page

        if direction == "next":
            self.current_page = min(self.current_page + 1, max(0, self.total_pages - 1))
        elif direction == "prev":
            self.current_page = max(0, self.current_page - 1)
        elif direction == "first":
            self.current_page = 0
        elif direction == "last":
            self.current_page = max(0, self.total_pages - 1)

        # Disable follow mode if navigating away from last page
        if self.follow_mode and not self.is_last_page:
            self.follow_mode = False

    async def refresh(self) -> None:
        """Manually refresh current page."""
        await self._fetch_logs()
        await self._render()

    def show_filter_modal(self) -> None:
        """Show modal dialog for logger filter input."""
        self.in_modal = True
        self.modal_type = "filter"
        self.modal_input = self.logger_filter or ""
        self.modal_cursor_pos = len(self.modal_input)

    def show_search_modal(self) -> None:
        """Show modal dialog for search pattern input."""
        self.in_modal = True
        self.modal_type = "search"
        self.modal_input = self.search_pattern or ""
        self.modal_cursor_pos = len(self.modal_input)

    def show_help_modal(self) -> None:
        """Show help modal with keybindings."""
        self.in_modal = True
        self.modal_type = "help"

    def close_modal(self, accept: bool = False) -> None:
        """
        Close the current modal.

        Args:
            accept: If True, apply the modal input; if False, cancel
        """
        if not self.in_modal:
            return

        if accept:
            if self.modal_type == "filter":
                self.set_logger_filter(self.modal_input if self.modal_input else None)
            elif self.modal_type == "search":
                # For search modal, also ask about regex mode
                # For now, keep current regex setting
                self.set_search_pattern(self.modal_input if self.modal_input else None, self.search_regex)

        self.in_modal = False
        self.modal_type = None
        self.modal_input = ""
        self.modal_cursor_pos = 0

    def modal_add_char(self, char: str) -> None:
        """Add character to modal input at cursor position."""
        self.modal_input = (
            self.modal_input[:self.modal_cursor_pos] +
            char +
            self.modal_input[self.modal_cursor_pos:]
        )
        self.modal_cursor_pos += 1

    def modal_backspace(self) -> None:
        """Delete character before cursor in modal input."""
        if self.modal_cursor_pos > 0:
            self.modal_input = (
                self.modal_input[:self.modal_cursor_pos - 1] +
                self.modal_input[self.modal_cursor_pos:]
            )
            self.modal_cursor_pos -= 1

    def modal_move_cursor(self, direction: str) -> None:
        """Move cursor in modal input."""
        if direction == "left":
            self.modal_cursor_pos = max(0, self.modal_cursor_pos - 1)
        elif direction == "right":
            self.modal_cursor_pos = min(len(self.modal_input), self.modal_cursor_pos + 1)
        elif direction == "home":
            self.modal_cursor_pos = 0
        elif direction == "end":
            self.modal_cursor_pos = len(self.modal_input)

    def _show_loading(self) -> None:
        """Show loading message."""
        loading_msg = "\033[1;36m╔═══════════════════════════════════════════════════════════╗\033[0m\n"
        loading_msg += "\033[1;36m║                     Logs View Mode                        ║\033[0m\n"
        loading_msg += "\033[1;36m╚═══════════════════════════════════════════════════════════╝\033[0m\n"
        loading_msg += "\033[2mLoading logs...\033[0m\n"

        self.log_view_buffer.set_document(
            Document(text=loading_msg, cursor_position=0),
            bypass_readonly=True
        )
        self.app.invalidate()

    async def _fetch_logs(self) -> None:
        """Fetch logs from API based on current filters and pagination."""
        if not self.shell.client:
            self.error_message = "Not connected"
            return

        try:
            # Build API parameters
            params = {
                "lines": self.logs_per_page,
                "offset": self.current_offset,
            }

            # Add filters
            if self.level_filter:
                params["level"] = self.level_filter
            if self.logger_filter:
                params["logger"] = self.logger_filter

            # Determine endpoint
            if self.search_pattern:
                # Use search endpoint
                endpoint = "/logs/search"
                params = {
                    "pattern": self.search_pattern,
                    "regex": self.search_regex,
                    "lines": self.logs_per_page,
                }
                # Note: search endpoint doesn't support offset, level, logger in current API
                # We'll need to filter client-side or enhance API later
            else:
                # Use regular logs endpoint
                endpoint = "/logs"

            # Make API call
            response = self.shell.client.get(endpoint, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            # Update state
            if self.search_pattern:
                # Search endpoint returns count, not total
                self.total_logs = data.get("count", 0)
                self.current_logs = data.get("logs", [])
                # For search, we get all results at once, no pagination
                self.total_pages = 1
            else:
                # Regular endpoint returns total
                self.total_logs = data.get("total", 0)
                self.current_logs = data.get("logs", [])
                # Calculate total pages
                self.total_pages = (self.total_logs + self.logs_per_page - 1) // self.logs_per_page if self.total_logs > 0 else 0

            # Clear error on success
            self.error_message = None

        except Exception as exc:
            self.error_message = str(exc)
            self.current_logs = []
            self.total_pages = 0

    async def _render(self) -> None:
        """Render current page of logs to buffer."""
        output = ""

        # Show logs
        if not self.current_logs:
            if self.error_message:
                output += f"\033[31mError loading logs: {self.error_message}\033[0m\n"
            else:
                output += "\033[2mNo logs found matching current filters\033[0m\n"
        else:
            # Render logs in table format
            output += self._render_logs_table()

        # Add modal overlay if in modal mode
        if self.in_modal:
            output += self._render_modal()

        # Update buffer
        self.log_view_buffer.set_document(
            Document(text=output, cursor_position=0),
            bypass_readonly=True
        )
        self.app.invalidate()

    def _render_logs_table(self) -> str:
        """Render logs in ASCII table format with extra fields and line wrapping."""
        import shutil
        import textwrap

        # Standard fields that are always present
        STANDARD_FIELDS = {"timestamp", "level", "logger", "message"}

        # Collect all extra fields from all logs on this page
        extra_field_names = set()
        for log_entry in self.current_logs:
            for key in log_entry.keys():
                if key not in STANDARD_FIELDS:
                    extra_field_names.add(key)

        extra_field_names = sorted(extra_field_names)  # Sort for consistent ordering

        # Get terminal width
        terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns

        # Calculate column widths dynamically
        # Fixed widths for timestamp, level
        timestamp_width = 15  # "Jan 15 14:35:42"
        level_width = 8

        # Account for borders and padding:
        # Each column has "│ " before and " " after (3 chars per column)
        # Plus opening and closing borders (2 chars total)
        border_overhead = 3 * 4 + 2  # 4 columns minimum (timestamp, level, logger, message)
        if extra_field_names:
            border_overhead += 3 * len(extra_field_names)

        # Available width for content
        available_width = max(40, terminal_width - border_overhead)

        # Allocate remaining width proportionally
        logger_width = max(15, int(available_width * 0.20))
        message_width = max(20, int(available_width * 0.20))

        # Extra field gets remaining space or 40% if multiple extra fields
        if extra_field_names:
            extra_field_width = max(15, int(available_width * 0.40))
        else:
            extra_field_width = 0

        # Helper function to wrap text
        def wrap_text(text: str, width: int) -> list[str]:
            """Wrap text to fit within width, returning list of lines."""
            if not text:
                return [""]
            # Use textwrap to handle word boundaries
            wrapped = textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)
            return wrapped if wrapped else [""]

        # Helper function to strip ANSI codes for length calculation
        def strip_ansi(text: str) -> str:
            """Remove ANSI color codes from text."""
            import re
            return re.sub(r'\033\[[0-9;]+m', '', text)

        # Build table header
        output = ""
        output += "\033[1;36m"  # Bold cyan
        output += "┌─" + "─" * timestamp_width + "─┬"
        output += "─" + "─" * level_width + "─┬"
        output += "─" + "─" * logger_width + "─┬"
        output += "─" + "─" * message_width + "─"

        # Add extra field columns
        for _ in extra_field_names:
            output += "┬─" + "─" * extra_field_width + "─"

        output += "┐\033[0m\n"

        # Header row
        output += "\033[1;36m│\033[0m "
        output += f"\033[1mTimestamp\033[0m{' ' * (timestamp_width - 9)}"
        output += " \033[1;36m│\033[0m "
        output += f"\033[1mLevel\033[0m{' ' * (level_width - 5)}"
        output += " \033[1;36m│\033[0m "
        output += f"\033[1mLogger\033[0m{' ' * (logger_width - 6)}"
        output += " \033[1;36m│\033[0m "
        output += f"\033[1mMessage\033[0m{' ' * (message_width - 7)}"
        output += " "

        for field_name in extra_field_names:
            title = field_name.title()
            output += "\033[1;36m│\033[0m "
            output += f"\033[1m{title}\033[0m"
            # Pad to width
            output += " " * (extra_field_width - len(title))
            output += " "

        output += "\033[1;36m│\033[0m\n"

        # Separator
        output += "\033[1;36m├─"
        output += "─" * timestamp_width + "─┼"
        output += "─" + "─" * level_width + "─┼"
        output += "─" + "─" * logger_width + "─┼"
        output += "─" + "─" * message_width + "─"

        for _ in extra_field_names:
            output += "┼─" + "─" * extra_field_width + "─"

        output += "┤\033[0m\n"

        # Calculate available lines for rendering
        # Get terminal height
        terminal_height = shutil.get_terminal_size(fallback=(80, 24)).lines
        # Reserve: toolbar (3) + prompt (1) + separator (1) + table header (3) + bottom border (1) = 9 lines
        max_content_lines = max(10, terminal_height - 9)

        # Track lines rendered
        lines_rendered = 0

        # Data rows
        for log_entry in self.current_logs:
            # Format timestamp: ISO to "Jan 15 14:35:42"
            timestamp = log_entry.get("timestamp", "")
            formatted_time = self._format_timestamp(timestamp)

            level = log_entry.get("level", "INFO")
            logger_name = log_entry.get("logger", "")
            message = log_entry.get("message", "")

            # Wrap fields that might be long
            time_lines = [formatted_time[:timestamp_width].ljust(timestamp_width)]
            level_lines = [level[:level_width].ljust(level_width)]
            logger_lines = wrap_text(logger_name, logger_width)
            message_lines = wrap_text(message, message_width)

            # Wrap extra fields
            extra_lines_dict = {}
            for field_name in extra_field_names:
                field_value = str(log_entry.get(field_name, ""))
                extra_lines_dict[field_name] = wrap_text(field_value, extra_field_width)

            # Calculate max lines needed for this row
            max_lines = max(
                len(logger_lines),
                len(message_lines),
                max([len(lines) for lines in extra_lines_dict.values()]) if extra_lines_dict else 1,
                1
            )

            # Check if we have enough space to render this entry
            # If adding this entry would exceed available lines, stop rendering entries
            if lines_rendered + max_lines > max_content_lines:
                break

            # Pad all columns to same height
            while len(time_lines) < max_lines:
                time_lines.append(" " * timestamp_width)
            while len(level_lines) < max_lines:
                level_lines.append(" " * level_width)
            while len(logger_lines) < max_lines:
                logger_lines.append(" " * logger_width)
            while len(message_lines) < max_lines:
                message_lines.append(" " * message_width)
            for field_name in extra_field_names:
                while len(extra_lines_dict[field_name]) < max_lines:
                    extra_lines_dict[field_name].append(" " * extra_field_width)

            # Color code by level
            level_colors = {
                "DEBUG": "\033[36m",      # Cyan
                "INFO": "\033[32m",       # Green
                "WARNING": "\033[33m",    # Yellow
                "ERROR": "\033[31m",      # Red
                "CRITICAL": "\033[1;31m", # Bold red
            }
            level_color = level_colors.get(level, "\033[37m")
            reset = "\033[0m"
            dim = "\033[2m"
            cyan = "\033[36m"

            # Render all lines for this log entry
            for line_idx in range(max_lines):
                output += "\033[1;36m│\033[0m "

                # Timestamp (only colored on first line)
                time_text = time_lines[line_idx]
                if line_idx == 0:
                    output += f"{dim}{time_text}{reset}"
                else:
                    output += time_text
                output += " \033[1;36m│\033[0m "

                # Level (only colored on first line)
                level_text = level_lines[line_idx]
                if line_idx == 0:
                    output += f"{level_color}{level_text}{reset}"
                else:
                    output += level_text
                output += " \033[1;36m│\033[0m "

                # Logger (only colored on first line)
                logger_text = logger_lines[line_idx]
                # Ensure proper width
                logger_text = logger_text[:logger_width].ljust(logger_width)
                if line_idx == 0:
                    output += f"{cyan}{logger_text}{reset}"
                else:
                    output += logger_text
                output += " \033[1;36m│\033[0m "

                # Message
                message_text = message_lines[line_idx]
                # Ensure proper width
                message_text = message_text[:message_width].ljust(message_width)
                output += message_text
                output += " "

                # Extra fields
                for field_name in extra_field_names:
                    extra_text = extra_lines_dict[field_name][line_idx]
                    # Ensure proper width
                    extra_text = extra_text[:extra_field_width].ljust(extra_field_width)
                    output += "\033[1;36m│\033[0m "
                    output += extra_text
                    output += " "

                output += "\033[1;36m│\033[0m\n"

            # Update line counter
            lines_rendered += max_lines

        # Bottom border
        output += "\033[1;36m└─"
        output += "─" * timestamp_width + "─┴"
        output += "─" + "─" * level_width + "─┴"
        output += "─" + "─" * logger_width + "─┴"
        output += "─" + "─" * message_width + "─"

        for _ in extra_field_names:
            output += "┴─" + "─" * extra_field_width + "─"

        output += "┘\033[0m\n"

        return output

    def _render_modal(self) -> str:
        """Render modal dialog overlay."""
        modal_output = "\n\n"

        if self.modal_type == "filter":
            modal_output += "\033[1;36m╔═══════════════════════════════════════════════════════════╗\033[0m\n"
            modal_output += "\033[1;36m║                    Logger Filter                          ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[0m║ Enter logger name prefix (e.g., govee.api)                ║\033[0m\n"
            modal_output += "\033[0m║ Leave empty to clear filter                               ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += f"\033[0m║ {self.modal_input:<57} ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[2m║ Enter: Accept  │  Esc: Cancel                             ║\033[0m\n"
            modal_output += "\033[1;36m╚═══════════════════════════════════════════════════════════╝\033[0m\n"

        elif self.modal_type == "search":
            modal_output += "\033[1;36m╔═══════════════════════════════════════════════════════════╗\033[0m\n"
            modal_output += "\033[1;36m║                    Search Pattern                         ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[0m║ Enter search pattern                                      ║\033[0m\n"
            modal_output += "\033[0m║ Leave empty to clear search                               ║\033[0m\n"
            regex_status = "ON" if self.search_regex else "OFF"
            modal_output += f"\033[0m║ Regex mode: {regex_status:<44} ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += f"\033[0m║ {self.modal_input:<57} ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[2m║ Enter: Accept  │  Esc: Cancel  │  Ctrl+R: Toggle Regex   ║\033[0m\n"
            modal_output += "\033[1;36m╚═══════════════════════════════════════════════════════════╝\033[0m\n"

        elif self.modal_type == "help":
            modal_output += "\033[1;36m╔═══════════════════════════════════════════════════════════╗\033[0m\n"
            modal_output += "\033[1;36m║                 Logs View - Help                          ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[1;33m║ Navigation:                                               ║\033[0m\n"
            modal_output += "\033[0m║   PgUp/PgDn       Previous/Next page                      ║\033[0m\n"
            modal_output += "\033[0m║   Home/End        First/Last page                         ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[1;33m║ Filters:                                                  ║\033[0m\n"
            modal_output += "\033[0m║   l               Cycle log level filter                  ║\033[0m\n"
            modal_output += "\033[0m║                   (INFO→WARNING→ERROR→CRITICAL→ALL)       ║\033[0m\n"
            modal_output += "\033[0m║   f               Set logger filter (prefix match)        ║\033[0m\n"
            modal_output += "\033[0m║   /               Edit search pattern                     ║\033[0m\n"
            modal_output += "\033[0m║   c               Clear logger filter                     ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[1;33m║ Actions:                                                  ║\033[0m\n"
            modal_output += "\033[0m║   r               Manual refresh current page             ║\033[0m\n"
            modal_output += "\033[0m║   Space           Toggle follow mode (auto-jump to last)  ║\033[0m\n"
            modal_output += "\033[0m║   ?               Show this help                          ║\033[0m\n"
            modal_output += "\033[0m║   q/Esc           Exit logs view                          ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[1;33m║ Info:                                                     ║\033[0m\n"
            modal_output += "\033[0m║   Auto-refresh:   Every 5 seconds                         ║\033[0m\n"
            modal_output += "\033[0m║   Follow mode:    OFF by default, toggle with Space       ║\033[0m\n"
            modal_output += "\033[0m║   Level filter:   Additive (ERROR shows ERROR+CRITICAL)   ║\033[0m\n"
            modal_output += "\033[1;36m╠═══════════════════════════════════════════════════════════╣\033[0m\n"
            modal_output += "\033[2m║ Press any key to close                                    ║\033[0m\n"
            modal_output += "\033[1;36m╚═══════════════════════════════════════════════════════════╝\033[0m\n"

        return modal_output

    def _format_timestamp(self, iso_timestamp: str) -> str:
        """
        Format ISO timestamp to 'Jan 15 14:35:42'.

        Args:
            iso_timestamp: ISO format timestamp like '2025-01-15T14:35:42.123Z'

        Returns:
            Formatted timestamp string
        """
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            # Format as "Jan 15 14:35:42"
            return dt.strftime("%b %d %H:%M:%S")
        except Exception:
            # Fallback to original if parsing fails
            return iso_timestamp[:19] if len(iso_timestamp) >= 19 else iso_timestamp

    async def _refresh_loop(self) -> None:
        """Auto-refresh loop - refresh every REFRESH_INTERVAL seconds."""
        try:
            while self._should_refresh:
                await asyncio.sleep(self.REFRESH_INTERVAL)

                # Save current state
                old_total_pages = self.total_pages
                old_page = self.current_page

                # Fetch updated logs
                await self._fetch_logs()

                # Handle follow mode
                if self.follow_mode and self.total_pages > 0:
                    # Jump to last page
                    self.current_page = self.total_pages - 1
                elif old_page >= self.total_pages and self.total_pages > 0:
                    # Current page no longer exists, go to last page
                    self.current_page = self.total_pages - 1

                # Re-render
                await self._render()

        except asyncio.CancelledError:
            pass
