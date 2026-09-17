# UIAutomation

iOS Native Apps UI Automation Framework using Appium and Python.

## Overview

This framework provides automated testing capabilities for native iOS system apps. It uses the Page Object Model (POM) pattern for maintainable and scalable test automation. Currently supports Settings and Calendar apps, with more apps planned.

## Prerequisites

### System Requirements

- macOS (required for iOS testing)
- Xcode 27 or newer with Command Line Tools and Device Hub
- Node.js (for Appium)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

### Install Appium

```bash
# Install Appium globally
npm install -g appium

# Install XCUITest driver
appium driver install xcuitest
```

### iOS Simulator Setup

1. Open Xcode 27 or newer
2. Download the iOS simulator runtime in Xcode Settings
3. Open **Xcode > Open Developer Tool > Device Hub**
4. Create or select your simulator in Device Hub

## Installation

### Using uv

[uv](https://docs.astral.sh/uv/) is an extremely fast Python package manager. Install it first if you haven't:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then set up the project:

```bash
cd UIAutomation

# Sync dependencies (creates venv automatically)
uv sync

# Development tools are included by default
```

## Project Structure

```
UIAutomation/
├── src/
│   └── uiautomation/
│       ├── __init__.py
│       ├── drivers/               # Appium sessions and configuration
│       ├── pages/                 # Base page, Settings, and Calendar
│       └── utils/                 # App lifecycle, simulator setup, artifacts
├── tests/
│   ├── unit/                      # Device-free framework tests
│   └── integration/               # Settings and Calendar journeys
├── scripts/
│   └── inspect_locators.py        # Locator discovery helper
├── conftest.py                   # Shared fixtures for tests and scripts
├── pyproject.toml                # Package config and dependencies
└── README.md
```

## Running Tests

Default runs execute device-free unit tests. Device tests require `--run-integration`.

```bash
uv run pytest                         # Fast unit suite; no device needed
uv run pytest --run-integration -m smoke  # Representative simulator smoke journeys
uv run pytest --run-integration -m journey --headless-simulator  # Navigation checks
uv run pytest --run-integration tests/integration  # Device regression suite
uv run pytest --run-integration --run-diagnostics -m diagnostic
```

A single driver session is reused. App fixtures terminate apps before launch and
register cleanup before setup so failures still trigger termination. This does not
erase app data or guarantee every system app forgets its navigation state.
Wi-Fi mutations restore their starting state. Simulator termination and privacy
reset use `simctl` once per session; onboarding itself remains a UI flow. A booted
simulator is reused; use `--restart-simulator` when recovering a stuck runtime.
Use `--headless-simulator` to skip opening Device Hub. By default, tests open
Device Hub from the Xcode selected by `DEVELOPER_DIR` or `xcode-select`.
The framework manages the window and sets Appium’s `isHeadless` capability to
prevent Appium from trying to launch the removed Simulator.app.
Tests marked `real_device(reason="...")` skip on simulators before any app or
driver fixtures run. `journey` covers General/About, New Event/Cancel, and day/month
navigation. Partial device names or runtime options filter the available inventory
before ranking; mismatches list available targets.

External setup commands have finite timeouts: 30 seconds for discovery, resets,
and Appium preflight; 120 seconds for simulator boot completion; 600 seconds for
an optional WDA prebuild. Pytest's own timeout still applies; allow a larger
`--timeout` for first-time builds when needed.

Permission-reset failures stop setup. Settings readiness polls one UI snapshot per
attempt, requiring a visible list and two distinct home rows with no visible alert.
Local Appium installation checks run only when starting a managed server; an
already-running server supplies its own drivers.

Every failure phase gets a unique directory under `artifacts/<run-id>/`, with
failure metadata and, when available, screenshot, page XML, and local Appium log.
No screenshot fixture is required. Unavailable captures are recorded in metadata.
Use `--artifacts-dir PATH` to relocate output. External Appium servers must supply
logs separately. Parallel execution is supported for unit tests only; `--run-integration`
rejects `-n` before worker startup.

CI runs unit tests, Ruff lint/format checks, and Pyright on Linux. Run simulator
smoke tests locally on macOS; physical devices cover hardware-dependent behavior.

### Zero-Setup Smoke Run

```bash
uv run pytest --run-integration -m smoke
```

Framework now does local setup automatically for simulator runs:

- boots preferred simulator if target simulator is shut down
- opens Device Hub on the target simulator
- starts local Appium server if `http://localhost:4723` is not running
- terminates Settings/Calendar and resets simulator privacy prompts before each fresh session
- writes Appium logs to `artifacts/<run-id>/appium.log`

To skip session-level permission resets for debugging (test fixtures still terminate apps):

```bash
uv run pytest --run-integration -m smoke --skip-simulator-state-reset --no-reset
```

### Run Default Unit Tests

```bash
# Using uv
uv run pytest

# Or if venv is activated
pytest
```

### Run Specific Test File

```bash
uv run pytest --run-integration tests/integration/test_settings.py
```

### Run Tests by Marker

```bash
# Run smoke tests
uv run pytest --run-integration -m smoke

# Run Settings app tests
uv run pytest --run-integration -m settings

# Run slow tests
uv run pytest --run-integration -m slow
```

### Run with Custom Device

```bash
uv run pytest --run-integration --device-name "iPhone 17 Pro" --platform-version "26.4.1"
```

### Run with HTML Report

```bash
uv run pytest --html=report.html --self-contained-html
```

### Run in Parallel

```bash
uv run pytest tests/unit -n 2  # Run with 2 parallel workers
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--run-integration` | false | Enable device tests (serial execution) |
| `--run-diagnostics` | false | Include environment-dependent observations |
| `--headless-simulator` | false | Boot without opening Device Hub |
| `--restart-simulator` | false | Restart runtime during state reset for recovery |
| `--artifacts-dir` | artifacts | Root for unique run artifacts |
| `--device-name` | Best local simulator | iOS device/simulator name |
| `--platform-version` | Best local simulator runtime | iOS version |
| `--appium-server` | http://localhost:4723 | Appium server URL |
| `--no-reset` | false | Preserve Appium app/device state |
| `--skip-simulator-state-reset` | false | Preserve simulator app launches and privacy prompts |
| `--udid` | None | Device UDID (required for physical devices) |
| `--team-id` | None | Apple Developer Team ID (required for physical devices) |

Preferred simulator order for local runs:

1. `iPhone 17 Pro` on `iOS 26.4`
2. `iPhone 16 Pro` on `iOS 18.5`
3. `iPhone 17 Pro` on `iOS 26.2`
4. `iPhone 17 Pro` on `iOS 26.0`
5. `iPhone 15` on `iOS 17.0`

## Physical Device Testing

To run tests on a physical iPhone/iPad instead of the simulator:

### 1. Get Your Device UDID

```bash
# With device plugged in via USB
xcrun xctrace list devices
```

Or find it in **Finder** > Select your device > Click the device info under the name.

### 2. Get Your Apple Team ID

1. Open **Xcode** > **Preferences** > **Accounts**
2. Select your Apple ID
3. Your Team ID is shown (10-character string like `ABC123XYZ9`)

Or find it at [developer.apple.com/account](https://developer.apple.com/account) > Membership.

### 3. Trust Your Computer

On your device: **Settings** > **General** > **Device Management** > Trust the developer certificate.

### 4. Run Tests on Physical Device

```bash
uv run pytest --run-integration \
  --device-name "Your iPhone Name" \
  --platform-version "17.2" \
  --udid "00001234-000A1234B1234001" \
  --team-id "ABC123XYZ9"
```

### First Run Notes

- The first run will build and install **WebDriverAgent** on your device
- You may need to manually trust the WDA app on your device:
  **Settings** > **General** > **VPN & Device Management** > Trust the developer app
- Subsequent runs will be faster

## Supported System Apps

| App | Bundle ID | Status |
|-----|-----------|--------|
| Settings | com.apple.Preferences | Implemented |
| Calendar | com.apple.mobilecal | Implemented |
| Safari | com.apple.mobilesafari | Planned |
| Contacts | com.apple.MobileAddressBook | Planned |
| Photos | com.apple.Photos | Planned |

## Python Package

Runtime dependencies are Appium's Python client and Selenium. Pytest, its plugins,
Ruff, and Pyright belong to the development group, installed by `uv sync`.
`uv sync --no-dev` installs only runtime dependencies.

Runtime code lives in `src/uiautomation/`; import it as `uiautomation`, for example
`from uiautomation.pages.settings import SettingsHomePage`. Existing consumers
must replace `src.*` imports with `uiautomation.*`.

Import utilities from their defining modules, for example
`from uiautomation.utils.app_launcher import AppLauncher`; utility re-exports were
removed. Use `page.find_element((page.By.ACCESSIBILITY_ID, "identifier"))` instead
of the removed `find_element_by_*` wrappers. The unused `screenshots_dir` fixture
was removed; automatic failure artifacts and `page.take_screenshot(path)` remain.

Unit tests are grouped by component (driver, simulator, Appium service, page
objects, artifacts, and pytest support). About navigation has one canonical
`journey` test.

Run `uv sync` after updating the checkout to refresh the editable installation.
The wheel includes only the runtime package; tests and locator scripts remain
checkout utilities. Build distributions with `uv build`. CI installs the package
without editable mode to verify imports against the built wheel.

## Writing Tests

### Basic Test Example

```python
import pytest
from uiautomation.pages.settings import SettingsHomePage

@pytest.mark.settings
def test_navigate_to_wifi(settings_app: SettingsHomePage):
    """Test navigation to Wi-Fi settings."""
    wifi_page = settings_app.go_to_wifi()
    assert wifi_page.is_on_wifi_page()
```

### Using Page Objects

```python
from uiautomation.pages.settings import WifiSettingsPage

def test_wifi_toggle(restored_wifi: WifiSettingsPage):
    # Fixture restores the starting radio state even when the assertion fails.
    initial_state = restored_wifi.is_wifi_enabled()
    restored_wifi.toggle_wifi()
    assert restored_wifi.is_wifi_enabled() != initial_state
```

### Creating New Page Objects

```python
from uiautomation.pages.base_page import BasePage

class MyAppPage(BasePage):
    # Define locators
    SOME_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "ButtonName")
    SOME_FIELD = (BasePage.By.IOS_PREDICATE, "type == 'XCUIElementTypeTextField'")
    
    def tap_button(self):
        self.click(self.SOME_BUTTON)
    
    def enter_text(self, text: str):
        self.send_keys(self.SOME_FIELD, text)
```

## Locator Strategies

| Strategy | Use Case | Example |
|----------|----------|---------|
| `ACCESSIBILITY_ID` | Best for stable elements | `"Settings"` |
| `IOS_PREDICATE` | Complex queries | `"type == 'XCUIElementTypeButton' AND name == 'Done'"` |
| `IOS_CLASS_CHAIN` | Hierarchical queries | `"**/XCUIElementTypeTable/XCUIElementTypeCell"` |
| `XPATH` | Fallback (slower) | `"//XCUIElementTypeButton[@name='Done']"` |

## Troubleshooting

### Common Issues

1. **Appium can't find simulator**
   ```bash
   # List available simulators
   xcrun simctl list devices
   ```

2. **WebDriverAgent build fails**
   ```bash
   # Navigate to WDA directory and open in Xcode
   cd ~/.appium/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent
   open WebDriverAgent.xcodeproj
   # Build the WebDriverAgentRunner scheme
   ```

3. **Element not found**
   - Use Appium Inspector to verify locators
   - Increase timeout values
   - Check if element is visible/enabled

### Debugging Tips

```python
# Print page source for debugging
print(page.get_page_source())

# Take screenshot
page.take_screenshot("debug_screenshot.png")
```

For locator discovery, run the explicit helper script:

```bash
uv run pytest --run-integration scripts/inspect_locators.py -v
uv run pytest --run-integration scripts/inspect_locators.py -v -k wifi
uv run pytest --run-integration scripts/inspect_locators.py -v -k calendar
```

It writes captured XML to `debug_output/` at the project root.

## Development

### Code Formatting

```bash
# Format code with Ruff
uv run ruff format .

# Fix lint and import issues
uv run ruff check --fix .

# Lint with ruff
uv run ruff check src tests

# Type checking with Pyright
uv run pyright
```

### Adding Dependencies

```bash
# Add a runtime dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>
```

## License

MIT License
