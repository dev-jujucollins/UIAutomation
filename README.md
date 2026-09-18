# UIAutomation

Python/Appium framework for testing native iOS apps with XCUITest and page objects.
Runtime code lives in `src/uiautomation/`; tests use pytest.

## Current coverage

| App | Bundle ID | Automated coverage |
| --- | --- | --- |
| Settings | `com.apple.Preferences` | Home readiness, General/About, plus physical-device Wi-Fi, display, search, and radio cases |
| Calendar | `com.apple.mobilecal` | Onboarding, day/month navigation, event draft fields/cancel, and calendar lists |
| Messages | `com.apple.MobileSMS` | Home, compose/cancel, recipient text, plain/Unicode/multiline drafts, discard, and seeded-conversation navigation |
| Maps | `com.apple.Maps` | Location allow/deny, search editing, landmark details, Directions entry, and driving/walking route previews |

Messages tests do not send messages. Maps tests do not start navigation; route
previews use explicit coordinates through the native Maps URL handler. Manual
origin editing and real GPS behavior are outside current automated coverage.
Other apps listed in `SystemApps` have bundle identifiers, not implemented test suites.

Messages and Maps flows were exercised on an English iOS 27.0 iPhone 17 Pro
simulator. Locators and seed-data assumptions are runtime-specific; installed
older runtimes are not a guarantee that these app flows will pass.

## Requirements and installation

Device-free unit tests run without Xcode, Appium, or a simulator. They require
Python 3.10+ and [uv](https://docs.astral.sh/uv/).

iOS integration tests additionally require:

- macOS and selected Xcode 27 or newer with Command Line Tools and Device Hub
- An installed iOS runtime and an existing iPhone simulator, or a configured physical device
- Node.js, Appium, and the XCUITest driver
- Internet access for Maps search and route responses

From the checkout:

```bash
uv sync
```

This creates the virtual environment and installs runtime and development dependencies.
For local device testing, install Appium and its driver:

```bash
npm install -g appium
appium driver install xcuitest
```

Install simulator runtimes in Xcode Settings. Create simulators in Device Hub or
with `simctl`. The framework boots existing simulators; it does not create them
or download Xcode, runtimes, Appium, or drivers.

Existing iPhone simulators on iOS 27.0 work with any name. For optional isolation,
create these simulators **once**, after installing iOS 27.0:

```bash
xcrun simctl create "UIAutomation Maps" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-27-0

xcrun simctl create "UIAutomation Messages" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-27-0
```

Do not create duplicates if these names already exist. Check inventory with
`xcrun simctl list devices available`.

## Run tests

### Unit tests

Default pytest runs exclude integration tests and opt-in diagnostics:

```bash
uv run pytest
uv run pytest tests/unit -n 2
uv run pytest --html=report.html --self-contained-html
```

The HTML command above reports unit tests. Add integration selection and target
options when generating a device-test report.

### Smoke tests

`@pytest.mark.smoke` identifies quick checks. `--run-integration` enables device
execution; `-m smoke` selects those checks. The current smoke selection contains
six cases: Settings launch, Calendar launch, Messages home, Messages compose/cancel,
and Maps landmark search with location denied and allowed.

Run the combined smoke suite on an available iOS 27.0 simulator:

```bash
uv run pytest --run-integration -m smoke \
  --platform-version 27.0 --timeout=300
```

Simulator names are unrestricted. `--platform-version 27.0` selects the tested
runtime; optionally add `--device-name "iPhone 17 Pro"` (or any existing simulator
name) to select a specific device. All selected apps share that simulator.
Omitting both options uses the framework's normal simulator preference order,
which can select an older runtime.

For Settings and Calendar smoke checks on an automatically selected simulator:

```bash
uv run pytest --run-integration -m "smoke and (settings or calendar)" --timeout=300
```

For app-specific smoke checks:

```bash
uv run pytest --run-integration -m "messages and smoke" \
  --device-name "UIAutomation Messages" --platform-version 27.0 --timeout=300

uv run pytest --run-integration -m "maps and smoke" \
  --platform-version 27.0 --timeout=300
```

### App suites and navigation journeys

```bash
# All Messages draft/navigation cases
uv run pytest --run-integration -m messages \
  --device-name "UIAutomation Messages" --platform-version 27.0 --timeout=300

# All Maps cases
uv run pytest --run-integration -m maps \
  --platform-version 27.0 --timeout=300

# Cross-app navigation journeys, without opening Device Hub
uv run pytest --run-integration -m journey --headless-simulator \
  --platform-version 27.0 --timeout=300

# Full integration selection; hardware-only cases skip on simulator
uv run pytest --run-integration tests/integration \
  --platform-version 27.0 --timeout=300

# One Settings test
uv run pytest --run-integration \
  tests/integration/test_settings.py::TestSettingsNavigation::test_settings_app_launches \
  --device-name "iPhone 17 Pro" --platform-version 27.0 --timeout=300

# Opt-in Calendar observations
uv run pytest --run-integration --run-diagnostics -m diagnostic --timeout=300
```

`journey` includes Settings General/About, Calendar day/month and new-event/cancel,
Messages discard/conversation round trips, and Maps Directions/route/repeated-search
flows. App markers can be combined with `smoke` or `journey` using pytest expressions.
Selecting `regression` is not a substitute for running `tests/integration`; the
registered marker does not automatically mark every integration test.

See [Messages testing](docs/messages-testing.md) for seed-data assumptions and
[Maps testing](docs/maps-testing.md) for exact assertions and coverage boundaries.

## Runtime setup, state, and artifacts

One Appium driver session is reused per pytest run. Integration tests run serially;
parallel device execution is rejected. App fixtures establish each test's starting
state and register termination cleanup before launching the app.

For simulator runs, the framework:

- Finds an existing target and boots it if needed.
- Opens Device Hub from `DEVELOPER_DIR` or the Xcode selected by `xcode-select`.
  `--headless-simulator` skips that window. Appium always receives `isHeadless=True`
  so it does not attempt to open the removed Simulator.app.
- Starts local Appium if the configured local server is unavailable. An existing
  server is reused and supplies its own installed drivers.
- By default, terminates Settings/Calendar and resets their privacy permissions
  once per session. This does not erase app data.

Per-app cleanup has additional rules:

- Settings Wi-Fi mutation fixtures restore the initial radio state.
- Messages clears only the test-owned compose draft before cancellation; existing
  conversation drafts are preserved.
- Maps uses the selected simulator, resets location authorization before each
  test, answers the prompt, dismisses owned cards, terminates Maps, and resets location
  authorization on teardown. Searches can remain in Recents.

`--skip-simulator-state-reset` or `--no-reset` skips the session-level Settings/Calendar
reset. Neither disables app fixture cleanup or Maps' per-test permission resets.
`--restart-simulator` takes effect only when session-level reset is enabled.

On failure, hooks write unique directories under `artifacts/<run-id>/` containing
metadata and, when available, screenshots, page XML, and local Appium logs. Missing
captures are recorded in metadata. External servers must supply logs separately.
Use `--artifacts-dir PATH` to change the output root.

Setup subprocesses have bounded timeouts. Pytest defaults to 120 seconds per test;
examples use 300 seconds to allow setup. A first WebDriverAgent build may require
`--timeout=600`.

## Target selection and configuration

Simulator name and runtime arguments are exact filters; either may be omitted.
Among matching available iPhones, preference order is:

1. iPhone 17 Pro / iOS 26.4
2. iPhone 16 Pro / iOS 18.5
3. iPhone 17 Pro / iOS 26.2
4. iPhone 17 Pro / iOS 26.0
5. iPhone 15 / iOS 17.0

If none matches that preference list, the highest available runtime wins, with
name as the tie-breaker. Explicit target mismatches list available choices.
Maps accepts the same selected simulator as the other app fixtures; no special name is required.

| Option | Default | Behavior |
| --- | --- | --- |
| `--run-integration` | off | Enable device tests |
| `--run-diagnostics` | off | Include diagnostic cases; device cases still need `--run-integration` |
| `--device-name` | auto | Exact simulator name; physical-device name when `--udid` is supplied |
| `--platform-version` | auto | Exact simulator runtime; provide actual OS version for physical devices |
| `--appium-server` | `http://localhost:4723` | Appium endpoint |
| `--headless-simulator` | off | Skip opening Device Hub |
| `--restart-simulator` | off | Restart simulator during session-level reset |
| `--no-reset` | off | Enable Appium `noReset` and skip framework session-level reset |
| `--skip-simulator-state-reset` | off | Skip framework session-level termination/privacy reset |
| `--artifacts-dir` | `artifacts` | Root for run artifacts |
| `--udid` | unset | Physical device identifier; omit for simulator selection |
| `--team-id` | unset | Signing team for physical-device WebDriverAgent |
| `--timeout` | `120` | pytest-timeout limit in seconds |

## Physical devices

Connect and trust the device, configure Xcode signing, and enable device development
access as required by its OS. Find its identifier using Xcode or:

```bash
xcrun xctrace list devices
```

Use actual device values in place of these placeholders:

```bash
uv run pytest --run-integration -m "settings and smoke" \
  --device-name "YOUR_DEVICE_NAME" --platform-version "YOUR_IOS_VERSION" \
  --udid "YOUR_DEVICE_UDID" --team-id "YOUR_APPLE_TEAM_ID" --timeout=600
```

First run builds/installs WebDriverAgent and may require trusting its developer
certificate. Tests marked `real_device` skip on simulators. Maps cases skip on
physical devices; current Messages cases assume simulator seed data and are not
a delivery-validation suite.

## Project layout

```text
UIAutomation/
├── src/uiautomation/
│   ├── drivers/                  # Driver config, sessions, system bundle IDs
│   ├── pages/
│   │   ├── base_page.py
│   │   ├── settings/
│   │   ├── calendar/
│   │   ├── messages/
│   │   └── maps/
│   └── utils/                    # App lifecycle, simulator, Appium, artifacts
├── tests/
│   ├── unit/                     # Device-free tests, including page contracts
│   └── integration/              # Settings, Calendar, Messages, Maps
├── docs/                         # Messages and Maps test setup/scope
├── scripts/inspect_locators.py   # Explicit locator-discovery utility
├── .github/workflows/tests.yml   # Linux unit/lint/type checks
├── conftest.py                   # CLI options, fixtures, collection, artifacts
├── pyproject.toml                # Dependencies, package and tool configuration
└── uv.lock
```

## Writing tests

Place device tests under `tests/integration/` and device-free tests under
`tests/unit/`. Collection assigns `integration`/`unit` markers based on those
paths. Add app and scope markers explicitly:

```python
import pytest

from uiautomation.pages.settings import SettingsHomePage


@pytest.mark.settings
@pytest.mark.smoke
def test_settings_ready(settings_app: SettingsHomePage) -> None:
    """Require visible, usable Settings home controls."""
    settings_app.assert_home_visually_ready()
```

Available app fixtures are `settings_app`, `calendar_home`, `messages_home`,
`message_draft`, and `maps_home`. `driver` exposes the raw Appium driver;
`app_launcher` controls app lifecycle. `restored_wifi` restores radio state and
skips on simulators. Mark hardware-specific tests with
`@pytest.mark.real_device(reason="...")` so they skip before fixture setup.

Import runtime modules as `uiautomation.*`. Page objects inherit `BasePage`:

```python
from uiautomation.pages.base_page import BasePage


class MyAppPage(BasePage):
    SAVE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Save")

    def save(self) -> None:
        """Tap the app's Save control."""
        self.click(self.SAVE_BUTTON)
```

Prefer accessibility IDs, then iOS predicates/class chains; use XPath only when
needed. Wait for meaningful live controls and verify resulting state. Register
cleanup before mutations. Full XML is for diagnostics, not a readiness assertion.

## Debugging and development

Failure artifacts are automatic. For explicit captures:

```python
print(page.get_page_source())
page.take_screenshot("debug_screenshot.png")
```

The locator helper uses pytest and writes XML under `debug_output/`:

```bash
uv run pytest --run-integration scripts/inspect_locators.py -v -k calendar --timeout=300
```

For setup failures, inspect Appium logs, confirm the selected Xcode with
`xcode-select -p`, and list installed simulators. Inspect live accessibility
controls when locators change; increasing waits cannot repair an incorrect locator.

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
uv build
```

CI runs on Linux for pushes and pull requests. It installs with
`uv sync --locked --no-editable`, then runs Ruff lint/format checks, Pyright, and
`tests/unit`. Simulator/device tests run locally on macOS.

Runtime dependencies are Appium's Python client and Selenium; pytest, plugins,
Ruff, and Pyright are development dependencies. `uv sync --no-dev` installs only
runtime dependencies. The wheel contains `uiautomation`; tests and scripts remain
checkout utilities. Run `uv sync` after checkout updates to refresh the editable
installation.

```bash
uv add <package>
uv add --dev <package>
```

## License

Project metadata declares the MIT license.
