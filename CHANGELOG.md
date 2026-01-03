# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-03

**BREAKING CHANGES**: This release includes major breaking changes with the rename from `govee-artnet-console` to `dmx-lan-console` and the introduction of multi-protocol support.

### Added
- **Multi-Protocol Support**: Full support for multiple smart lighting protocols (Govee, LIFX, etc.)
  - Protocol filtering in device listings (`--protocol govee`, `--protocol lifx`)
  - Protocol-aware device management and mapping creation
  - Protocol breakdown in monitoring dashboard
  - Color-coded protocol indicators (🔵 Govee, 🟣 LIFX)
- **Protocol Autocomplete**: Tab completion now includes protocol names for devices and mappings commands
- **Unmapped Device State**: New device state indicator for devices without DMX mappings
  - Devices now show as "Online", "Offline", "Stale", or "Unmapped"
  - Wider Device ID column in displays to accommodate protocol information
- **Enhanced Monitoring Dashboard**: Protocol breakdown panel showing device counts per protocol
- **Improved Field Display**: Mapping creation and listing now display field types for better clarity

### Changed
- **BREAKING**: Project renamed from `govee-artnet-console` to `dmx-lan-console`
- **BREAKING**: Python package renamed from `govee_artnet_console` to `dmx_lan_console`
- **BREAKING**: Executable renamed from `govee-artnet-console` to `dmx-lan-console`
- **BREAKING**: Configuration directory moved from `~/.govee_artnet_console` to `~/.dmx_lan_console`
- **BREAKING**: Shell prompt changed from `artnet-bridge>` to `dmx-bridge>`
- **BREAKING**: Environment variable prefix changed from `GOVEE_ARTNET_*` to `ARTNET_LAN_*` (legacy variables still supported)
- **Default Universe**: Changed from 0 to 1 for E1.31 (sACN) compatibility
  - Universe 0 remains Art-Net-only
  - Universes 1+ are mergeable across protocols (Art-Net and E1.31)
- **Device State Logic**: Updated to use `elif` for device states to prevent multiple state assignments
- **Channel Listing Output**: Now shows all mapping fields including protocol information
- **Mapping Event Display**: Improved display of mapping creation events with field type information
- **Documentation**: Comprehensive updates to reflect multi-protocol architecture and new project name

### Fixed
- **Channel Listing Output**: Fixed channel listing to properly display all fields
- **Default Universe**: Fixed default universe value for sACN compatibility
- **Nested Mapping Data**: Properly handle nested mapping objects in `mapping_created` events
- **dpkg Removal Warnings**: Eliminated Python bytecode file warnings during Debian package removal
- **Device State Display**: Device state now correctly shows only one state per device

### Migration Guide
If upgrading from v1.x:

1. **Configuration Migration**:
   ```bash
   # Backup old config
   cp -r ~/.govee_artnet_console ~/.govee_artnet_console.backup

   # Rename to new location
   mv ~/.govee_artnet_console ~/.dmx_lan_console
   ```

2. **Environment Variables**:
   - Update `GOVEE_ARTNET_API_KEY` to `ARTNET_LAN_API_KEY` (old variable still works)
   - Update `GOVEE_ARTNET_SERVER_URL` to `ARTNET_LAN_SERVER_URL`

3. **Package Name**:
   - Uninstall: `pip uninstall govee-artnet-console`
   - Install: `pip install dmx-lan-console` or use the new `.deb` package

4. **Executable Name**:
   - Old: `govee-artnet-console`
   - New: `dmx-lan-console`

5. **Default Universe**:
   - Mappings now default to universe 1 instead of 0
   - Update any automation/scripts that relied on universe 0 default

### Technical Improvements
- Multi-protocol device discovery and management architecture
- Protocol-aware mapping creation and validation
- Enhanced event streaming with protocol information
- Improved monitoring dashboard with protocol breakdown
- Better device state management with unmapped state detection

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
