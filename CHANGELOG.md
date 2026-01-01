# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-01-01

### Added
- GitHub Actions workflow for automated .deb package builds on pushes and tags
- Multi-distro testing matrix for .deb installation (Ubuntu 22.04, 24.04, Debian 13)
- Automated .deb artifact upload to GitHub releases for version tags
- Comprehensive installation verification and debugging in CI/CD pipeline
- Smart dependency installation with apt-first, pip-fallback strategy
- Installation badges and comprehensive .deb installation instructions in README
- Support for both modern and legacy pip versions (with/without --break-system-packages)

### Fixed
- Ubuntu 22.04 and 24.04 .deb installation issues with missing/outdated Python dependencies
- False positive detection when apt-get removes package due to unmet dependencies
- Pip compatibility across different Ubuntu versions (22.04 with old pip, 24.04 with new pip)
- Version synchronization between pyproject.toml and Makefile (both now at 1.0.2)
- Validation pipeline errors in GitHub Actions (SIGPIPE from dpkg-deb | head)
- Permission errors in CI/CD by adding conditional sudo support based on runner type
- Step output tracking in GitHub Actions workflow for proper status propagation

### Changed
- Lowered httpx requirement from >=0.27.0 to >=0.22.0 for broader distro compatibility
- .deb packages now output to dist/ directory instead of project root
- Updated Makefile VERSION from 1.0.1 to 1.0.2
- CI/CD workflow now builds on ubuntu-22.04 for maximum compatibility
- Improved GitHub Actions workflow with detailed logging and status reporting
- README now uses dynamic release badges instead of hardcoded version links

### Technical Improvements
- Multi-stage dependency resolution: apt packages → pip upgrade → dpkg --force-depends
- Robust error handling for package installation failures across different distributions
- Comprehensive debugging output in CI/CD for troubleshooting installation issues
- Version extraction from git tags with dev suffix for non-release builds
- Proper detection of package removal by apt when dependencies cannot be satisfied

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

## [1.0.0] - 2025-12-30

Initial release.
