# UIAutomation

iOS Native Apps UI Automation Framework using Appium and Python.

## Overview

This framework provides automated testing capabilities for native iOS system apps. It uses the Page Object Model (POM) pattern for maintainable and scalable test automation. Currently supports Settings and Calendar apps, with more apps planned.

## Prerequisites

### System Requirements

- macOS (required for iOS testing)
- Xcode with Command Line Tools
- Node.js (for Appium)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install Appium

```bash
# Install Appium globally
npm install -g appium

# Install XCUITest driver
appium driver install xcuitest
```

### iOS Simulator Setup

1. Open Xcode
2. Go to **Xcode > Preferences > Components**
3. Download the iOS Simulator runtime you want to test on
4. Create a simulator: **Window > Devices and Simulators > Simulators > +**

## Installation

### Using uv (Recommended)

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

# Or with dev dependencies
uv sync --all-extras
```

### Using pip (Alternative)

```bash
cd UIAutomation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Project Structure

```
UIAutomation/
├── src/
│   ├── drivers/
│   │   ├── __init__.py
│   │   └── ios_driver.py          # iOS driver configuration
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── base_page.py           # Base page object class
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── settings_home.py   # Settings home page
│   │   │   ├── wifi_settings.py   # Wi-Fi settings page
│   │   │   ├── display_settings.py # Display & Brightness page
│   │   │   └── general_settings.py # General settings page
│   │   └── calendar/
│   │       ├── __init__.py
│   │       ├── calendar_home.py   # Calendar main view
│   │       ├── calendar_onboarding.py # Onboarding flow
│   │       ├── calendars_list.py  # Calendars list view
│   │       └── new_event.py       # New event creation
│   └── utils/
│       ├── __init__.py
│       ├── app_launcher.py        # App launching utilities
│       ├── element_helpers.py     # Element interaction helpers
│       └── wait_helpers.py        # Custom wait utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_settings.py           # Settings app tests
│   └── test_calendar.py           # Calendar app tests
├── pyproject.toml                 # Project config & dependencies
└── README.md
```

## Running Tests

### Zero-Setup Smoke Run

```bash
uv run pytest tests/test_settings.py::TestSettingsNavigation::test_settings_app_launches
```

Framework now does local setup automatically for simulator runs:

- boots preferred simulator if target simulator is shut down
- opens Simulator app on target device
- starts local Appium server if `http://localhost:4723` is not running
- writes Appium logs to `artifacts/appium.log`

### Run All Tests

```bash
# Using uv
uv run pytest

# Or if venv is activated
pytest
```

### Run Specific Test File

```bash
uv run pytest tests/test_settings.py
```

### Run Tests by Marker

```bash
# Run smoke tests
uv run pytest -m smoke

# Run Settings app tests
uv run pytest -m settings

# Run slow tests
uv run pytest -m slow
```

### Run with Custom Device

```bash
uv run pytest --device-name "iPhone 17 Pro" --platform-version "26.4.1"
```

### Run with HTML Report

```bash
uv run pytest --html=report.html --self-contained-html
```

### Run in Parallel

```bash
uv run pytest -n 2  # Run with 2 parallel workers
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--device-name` | Best local simulator | iOS device/simulator name |
| `--platform-version` | Best local simulator runtime | iOS version |
| `--appium-server` | http://localhost:4723 | Appium server URL |
| `--udid` | None | Device UDID (required for physical devices) |
| `--team-id` | None | Apple Developer Team ID (required for physical devices) |

Preferred simulator order for local runs:

1. `iPhone 17 Pro` on `iOS 26.4.1`
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
uv run pytest \
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

## Writing Tests

### Basic Test Example

```python
import pytest
from src.pages.settings import SettingsHomePage

@pytest.mark.settings
def test_navigate_to_wifi(settings_app: SettingsHomePage):
    """Test navigation to Wi-Fi settings."""
    wifi_page = settings_app.go_to_wifi()
    assert wifi_page.is_on_wifi_page()
```

### Using Page Objects

```python
from src.pages.settings import SettingsHomePage, WifiSettingsPage

def test_wifi_toggle(settings_app: SettingsHomePage):
    # Navigate to Wi-Fi
    wifi_page = settings_app.go_to_wifi()
    
    # Toggle Wi-Fi
    initial_state = wifi_page.is_wifi_enabled()
    wifi_page.toggle_wifi()
    
    # Verify state changed
    assert wifi_page.is_wifi_enabled() != initial_state
```

### Creating New Page Objects

```python
from src.pages.base_page import BasePage

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

# Get element attributes
from src.utils.element_helpers import ElementHelpers
helpers = ElementHelpers(driver)
attrs = helpers.get_element_attributes(element)
print(attrs)
```

## Development

### Code Formatting

```bash
# Format code with black
uv run black src tests

# Sort imports with isort
uv run isort src tests

# Lint with ruff
uv run ruff check src tests

# Type checking with mypy
uv run mypy src
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
