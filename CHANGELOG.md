# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-12-30

### Added
- Real-time monitoring dashboard command with device status visualization
- EventsController for WebSocket-based event streaming
- Watch mode with live updates for dashboard and events commands
- Keybindings support for dashboard and events (e.g., 'q' to quit, 'r' to refresh)
- Comprehensive smoke tests for dashboard and events functionality
- Mock server with event streaming support for testing
- GitHub Actions CI/CD workflow for automated testing
- FastAPI and uvicorn as development dependencies for test infrastructure
- Custom pytest markers and websocket warning filters

### Fixed
- Status colors not rendering correctly in monitor dashboard tables
- Dashboard border alignment and styling inconsistencies
- NoneType errors in dashboard display when handling missing data
- Timezone handling for `last_seen` timestamps in dashboard
- Mappings count calculation (now uses API field directly instead of manual calculation)
- Dashboard column renamed from 'Mappings' to 'Mapped' with accurate device count
- `asyncio.timeout` compatibility for Python 3.10
- pytest configuration and module import issues
- pytest failures by adding proper conftest.py with mock server fixtures
- F824 flake8 syntax errors throughout codebase

### Changed
- Enhanced documentation with comprehensive dashboard and event streaming usage guide
- Updated shell autocomplete with new dashboard and events commands
- CI/CD pipeline now uses Poetry for dependency management
- GitHub Actions workflow updated to use `poetry run` for flake8 and pytest
- Dashboard rendering now uses Rich Text objects with inline styling for consistent output
- Status columns use `no_wrap=True` for better table formatting

### Technical Improvements
- Improved table rendering using `force_terminal` and direct buffer manipulation
- Better error handling for dashboard display edge cases
- More robust timezone conversions for device status timestamps
- Enhanced test infrastructure with comprehensive mocking capabilities

## [1.0.0] - 2025-12-31

Initial release.
