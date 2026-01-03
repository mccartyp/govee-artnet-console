.PHONY: help install uninstall deb clean test dev-install

PACKAGE_NAME = dmx-lan-console
VERSION = 2.0.0
PYTHON = python3
PIP = pip3

# Installation directories
PREFIX = /usr/local
BINDIR = $(PREFIX)/bin
LIBDIR = $(PREFIX)/lib/python3.11/site-packages

# Debian package directories
DEB_BUILD_DIR = packaging/debian
DEB_PKG_DIR = $(DEB_BUILD_DIR)/$(PACKAGE_NAME)
DEB_INSTALL_DIR = $(DEB_PKG_DIR)/usr
DEB_OUTPUT_DIR = dist

help:
	@echo "DMX LAN Console - Makefile targets:"
	@echo ""
	@echo "  install        Install to $(PREFIX) (requires root)"
	@echo "  uninstall      Remove from $(PREFIX) (requires root)"
	@echo "  deb            Build Debian package"
	@echo "  clean          Remove build artifacts"
	@echo "  test           Run tests"
	@echo "  dev-install    Install in development mode"
	@echo "  mock-server    Start mock server for testing"
	@echo ""

# Install to /usr/local
install:
	@echo "Installing $(PACKAGE_NAME) to $(PREFIX)..."
	@# Remove any existing broken symlinks
	@if [ -L "$(BINDIR)/$(PACKAGE_NAME)" ] && [ ! -e "$(BINDIR)/$(PACKAGE_NAME)" ]; then \
		rm -f "$(BINDIR)/$(PACKAGE_NAME)"; \
	fi
	@# Install Python package (use --prefix=/usr to install to /usr/local)
	@# pip will automatically install the console script to /usr/local/bin
	$(PIP) install --prefix=/usr .
	@echo "Installation complete!"
	@echo "Run: $(PACKAGE_NAME) --help"

# Uninstall from /usr/local
uninstall:
	@echo "Uninstalling $(PACKAGE_NAME) from $(PREFIX)..."
	$(PIP) uninstall -y $(PACKAGE_NAME) || true
	rm -f $(BINDIR)/$(PACKAGE_NAME)
	rm -rf $(LIBDIR)/dmx_lan_console*
	@echo "Uninstallation complete!"

# Build Debian package
deb: clean
	@echo "Building Debian package..."
	@mkdir -p $(DEB_PKG_DIR)/DEBIAN
	@mkdir -p $(DEB_INSTALL_DIR)/bin
	@mkdir -p $(DEB_INSTALL_DIR)/lib/python3/dist-packages
	@mkdir -p $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)

	@# Create control file
	@echo "Package: $(PACKAGE_NAME)" > $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Version: $(VERSION)" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Section: utils" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Priority: optional" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Architecture: all" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Depends: python3 (>= 3.10), python3-httpx (>= 0.22.0), python3-websockets (>= 12.0), python3-yaml (>= 6.0.0), python3-rich (>= 13.0.0), python3-prompt-toolkit (>= 3.0.0)" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Maintainer: mccartyp <mccartyp@gmail.com>" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo "Description: Interactive CLI console for DMX LAN Bridge" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo " Provides an interactive shell for managing multi-protocol smart lighting" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo " devices (Govee, LIFX, etc.) via the DMX LAN Bridge REST API. Features" >> $(DEB_PKG_DIR)/DEBIAN/control
	@echo " include device management, DMX mapping, real-time monitoring, and log streaming." >> $(DEB_PKG_DIR)/DEBIAN/control

	@# Copy maintainer scripts
	@cp packaging/debian-scripts/postrm $(DEB_PKG_DIR)/DEBIAN/postrm
	@chmod 755 $(DEB_PKG_DIR)/DEBIAN/postrm

	@# Copy source files
	@cp -r src/dmx_lan_console $(DEB_INSTALL_DIR)/lib/python3/dist-packages/

	@# Create executable wrapper
	@echo '#!/usr/bin/env python3' > $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)
	@echo 'import sys' >> $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)
	@echo 'from dmx_lan_console.cli import main' >> $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)
	@echo 'if __name__ == "__main__":' >> $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)
	@echo '    sys.exit(main())' >> $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)
	@chmod +x $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)

	@# Copy documentation
	@cp README.md $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/
	@cp LICENSE $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/
	@cp docs/INSTALLATION.md $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/
	@cp docs/USAGE.md $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/
	@gzip -9 -n -c docs/INSTALLATION.md > $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/INSTALLATION.md.gz

	@# Create copyright file
	@echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/" > $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@echo "Upstream-Name: $(PACKAGE_NAME)" >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@echo "Source: https://github.com/mccartyp/$(PACKAGE_NAME)" >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@echo "" >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@echo "Files: *" >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@echo "Copyright: 2025 mccartyp" >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@echo "License: MIT" >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright
	@cat LICENSE >> $(DEB_PKG_DIR)/usr/share/doc/$(PACKAGE_NAME)/copyright

	@# Set permissions
	@find $(DEB_PKG_DIR) -type d -exec chmod 755 {} \;
	@find $(DEB_PKG_DIR) -type f -exec chmod 644 {} \;
	@chmod 755 $(DEB_INSTALL_DIR)/bin/$(PACKAGE_NAME)
	@chmod 755 $(DEB_PKG_DIR)/DEBIAN
	@chmod 755 $(DEB_PKG_DIR)/DEBIAN/postrm

	@# Build package
	@mkdir -p $(DEB_OUTPUT_DIR)
	@dpkg-deb --build $(DEB_PKG_DIR) $(DEB_OUTPUT_DIR)
	@echo ""
	@echo "Debian package built successfully!"
	@ls -lh $(DEB_OUTPUT_DIR)/$(PACKAGE_NAME)_$(VERSION)_all.deb

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf $(DEB_BUILD_DIR)
	rm -rf $(DEB_OUTPUT_DIR)
	rm -f $(PACKAGE_NAME)_*.deb
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Clean complete!"

# Run tests
test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/test_client.py -v
	@echo "Tests complete!"

# Development install (editable)
dev-install:
	@echo "Installing in development mode..."
	$(PIP) install -e .
	@echo "Development installation complete!"

# Start mock server
mock-server:
	@echo "Starting mock server on http://localhost:8000..."
	@echo "Press Ctrl+C to stop"
	$(PYTHON) tests/mock_server.py
