# UIAutomation

Python/Appium framework for testing native iOS apps with XCUITest, pytest, and page
objects. Device-free unit tests cover framework behavior; serial device tests
exercise Settings, Calendar, Contacts, Messages, and Maps.

The `uiautomation` CLI checks local setup, runs test presets with optional email
summaries, and compares saved runs. Failures collect screenshots, page XML, Appium
logs, and matching simulator crash reports when available.

## Quick start

From the repository root:

```bash
uv sync
uv run pytest                         # Device-free unit tests
uv run uiautomation doctor --platform-version 27.0

# After installing the iOS toolchain (see Requirements)
uv run uiautomation smoke --platform-version 27.0 --timeout=300
```

Device tests can start a local Appium server automatically or reuse one already
running. A dedicated Mac CI runner is optional; local runs use the same tests.

## Current coverage

| App | Bundle ID | Automated coverage |
| --- | --- | --- |
| Settings | `com.apple.Preferences` | Home readiness, General/About, plus physical-device Wi-Fi, display, search, and radio cases |
| Calendar | `com.apple.mobilecal` | Onboarding, verified date navigation, owned draft cleanup, calendar lists, and opt-in saved-event lifecycle |
| Contacts | `com.apple.MobileAddressBook` | Opt-in create, relaunch, exact-name search, Unicode editing, deletion, and cleanup |
| Messages | `com.apple.MobileSMS` | Home, compose/cancel, recipient text, plain/Unicode/multiline drafts, discard, and seeded-conversation navigation |
| Maps | `com.apple.Maps` | Apple Park simulated location by default, location allow/deny, search editing, driving/walking previews, and opt-in guidance |

Messages tests do not send messages. Every Maps test temporarily sets the simulator
location to Apple Park, Cupertino. Route previews still use explicit coordinates
through the native Maps URL handler. An opt-in case starts and ends turn-by-turn
guidance from My Location. Manual origin editing, real movement, and rerouting are
outside current automated coverage. Other apps listed in `SystemApps` have bundle
identifiers, not implemented test suites.

Messages and Maps flows were exercised on an English iOS 27.0 iPhone 17 Pro
simulator. Locators and seed-data assumptions are runtime-specific; installed
older runtimes are not a guarantee that these app flows will pass.

## Requirements

Unit tests need Python 3.10+ and [uv](https://docs.astral.sh/uv/). Device tests also
need macOS with Xcode 27+ and Device Hub, an iPhone simulator or configured physical
device, Node.js, Appium with the XCUITest driver, and internet access for Maps.

See [setup](docs/setup.md) for installation, the read-only `doctor` checks, what a
device run changes on the simulator, and fixes for common failures.

## Run tests

### Local presets

The CLI provides five presets. It keeps pytest's terminal output and exit status
and saves each invocation under its own `artifacts/local-<id>/` directory.

```bash
uv run uiautomation unit
uv run uiautomation integration --platform-version 27.0 --timeout=300
uv run uiautomation all --platform-version 27.0 --timeout=300
uv run uiautomation smoke --platform-version 27.0 --timeout=300
uv run uiautomation journey --platform-version 27.0 --timeout=300
```

`unit` selects `tests/unit`; `integration` selects `tests/integration`; `all`
selects both. `smoke` selects integration smoke checks; `journey` selects
integration journeys excluding saved-data and Maps guidance cases. Diagnostics,
saved-data lifecycle, and Maps guidance still require their explicit opt-in flags.
Common options work directly: `--device-name`, `--platform-version`, `--timeout`,
`--headless-simulator`, device/signing options, reset and opt-in flags, `-m`, `-k`,
`-v`, and `-q`. Use `--` for other pytest arguments:

```bash
uv run uiautomation integration --email --device-name "UIAutomation CI" \
  --platform-version 27.0 --timeout=600 -- --maxfail=1
```

Runner options such as `--email`, `--email-preview`, `--email-config`, and
`--artifacts-dir` belong before `--`. `uiautomation run --suite NAME` remains
supported with the same options.

Add `--email-preview` to build a summary and `report.html` without sending, or
`--email` to send one after the run. Email is opt-in per run, the SMTP password
stays in macOS Keychain, and plain `uv run pytest` never sends email. See
[reporting](docs/reporting.md#opt-in-local-email) for sender setup and delivery details.

### Direct pytest

Default pytest runs exclude integration tests and opt-in diagnostics:

```bash
uv run pytest
uv run pytest tests/unit -n 2
uv run pytest --html=report.html --self-contained-html
```

In an interactive terminal, pytest-sugar shows a progress bar and failures as they
happen; piped output and CI use pytest's compact output. Add `-v` for each test
name, `-p no:sugar` for plain output, or `-o log_cli=true` for live logs.

`--run-integration` enables device tests; markers select them. The smoke selection
has six cases: Settings launch, Calendar launch, Messages home, Messages
compose/cancel, and Maps landmark search with location denied and allowed.

```bash
# Smoke checks on an iOS 27.0 simulator
uv run pytest --run-integration -m smoke --platform-version 27.0 --timeout=300

# One app, optionally combined with smoke or journey
uv run pytest --run-integration -m "messages and smoke" \
  --device-name "UIAutomation Messages" --platform-version 27.0 --timeout=300
uv run pytest --run-integration -m maps --platform-version 27.0 --timeout=300

# Cross-app navigation journeys, without opening Device Hub
uv run pytest --run-integration -m journey --headless-simulator \
  --platform-version 27.0 --timeout=300

# Full integration selection; hardware-only cases skip on simulator
uv run pytest --run-integration tests/integration --platform-version 27.0 --timeout=300

# One test
uv run pytest --run-integration \
  tests/integration/test_settings.py::TestSettingsNavigation::test_settings_app_launches \
  --device-name "iPhone 18 Pro" --platform-version 27.0 --timeout=300
```

`--platform-version 27.0` selects the tested runtime; add `--device-name` to pick a
specific simulator. Omitting both uses the preference order below, which can select
an older runtime. `journey` includes Settings General/About, Calendar day/month and
new-event/cancel, Messages discard/conversation round trips, and Maps
Directions/route/repeated-search flows. Selecting `regression` is not a substitute
for running `tests/integration`; the marker does not mark every integration test.

### Opt-in suites

```bash
# Start guidance from Apple Park, then end the route
uv run pytest --run-integration --run-maps-navigation -m maps_navigation \
  --device-name "UIAutomation Maps" --platform-version 27.0 --timeout=600

# Create, edit, and delete owned Calendar and Contacts records
uv run pytest --run-integration --run-lifecycle -m lifecycle \
  --device-name "UIAutomation Lifecycle" --platform-version 27.0 --timeout=600

# Calendar and Wi-Fi observations (Wi-Fi requires hardware)
uv run pytest --run-integration --run-diagnostics -m diagnostic --timeout=300
```

Guidance and lifecycle cases need an explicitly named simulator and never run on
physical devices. Diagnostics can accept an empty environment, so their results do
not establish event or network correctness. See [lifecycle testing](docs/lifecycle-testing.md),
[Messages testing](docs/messages-testing.md), and [Maps testing](docs/maps-testing.md)
for isolation, seed data, and exact assertions.

## Reports and failure evidence

Every executed run writes `artifacts/<run-id>/run.json` with the commit, selected
tests, target, tool versions, phase durations, and outcomes. On failure, hooks add a
folder with the screenshot, page XML, Appium log, and matching simulator crash
reports when available. HTML reports link to that evidence. Use `--artifacts-dir PATH`
to change the output root.

```bash
uv run uiautomation history --limit 15   # Recurring failures and slow setup
uv run uiautomation history --json
```

See [reporting](docs/reporting.md) for manifest contents, crash collection limits,
and run comparison.

## Target selection and configuration

Simulator name and runtime arguments are exact filters; either may be omitted.
Among matching available iPhones, preference order is:

1. iPhone 18 Pro / iOS 27.0
2. iPhone 17 Pro / iOS 26.4
3. iPhone 16 Pro / iOS 18.5
4. iPhone 17 Pro / iOS 26.2
5. iPhone 17 Pro / iOS 26.0
6. iPhone 15 / iOS 17.0

If none matches that preference list, the highest available runtime wins, with
name as the tie-breaker. Explicit target mismatches list available choices.

| Option | Default | Behavior |
| --- | --- | --- |
| `--run-integration` | off | Enable device tests |
| `--run-diagnostics` | off | Include diagnostic cases; device cases still need `--run-integration` |
| `--run-lifecycle` | off | Enable owned-data journeys on an explicitly named simulator |
| `--run-maps-navigation` | off | Start guidance in the Apple Park route case; requires an explicitly named simulator |
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
│   │   ├── contacts/
│   │   ├── messages/
│   │   └── maps/
│   ├── utils/                    # Runtime, artifacts, history, SMTP reporting
│   ├── cli.py                    # doctor, run, history commands
│   └── pytest_plugin.py          # CLI options, fixtures, collection, artifacts
├── tests/
│   ├── unit/                     # Device-free tests, including page contracts
│   └── integration/              # Settings, Calendar, Contacts, Messages, Maps
├── docs/                         # Setup, app coverage, reporting, CI
├── scripts/inspect_locators.py   # Explicit locator-discovery utility
├── .github/workflows/            # Python matrix + gated Mac smoke/journeys
├── conftest.py                   # Loads uiautomation.pytest_plugin
├── pyproject.toml                # Dependencies, package and tool configuration
├── email.example.json            # Nonsecret SMTP configuration template
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

Available app fixtures are `settings_app`, `calendar_home`, `calendar_draft`, `messages_home`,
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

CI runs Ruff, Pyright, and unit tests with coverage on Linux (Python 3.10 and 3.12)
for every push and pull request. Optional Mac workflows run nightly smoke checks and
weekly journeys on a dedicated runner; see [CI setup](docs/ci.md).

Runtime dependencies are Appium's Python client and Selenium; pytest, plugins,
Ruff, and Pyright are development dependencies. `uv sync --no-dev` installs only
runtime dependencies. The wheel contains `uiautomation`; tests and scripts remain
checkout utilities. Use `uv add <package>` or `uv add --dev <package>` to add one.

## License

Project metadata declares the MIT license.
