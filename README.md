# UIAutomation

Python/Appium framework for testing native iOS apps with XCUITest, pytest, and page
objects. Device-free unit tests cover framework behavior; device tests exercise
Settings, Calendar, Contacts, Messages, Maps, Reminders, Safari, Photos, and Files,
serially or spread across several simulators.

The `uiautomation` CLI checks local setup, picks a simulator, runs test presets with
optional email summaries, reruns failures, and compares saved runs. Failures collect
screenshots, page XML, Appium logs, and matching simulator crash reports when
available.

A native Swift/XCUITest port of the device tests, with no Appium or WebDriverAgent,
lives in [`swift/`](swift/README.md). The two suites are independent.

## Quick start

From the repository root:

```bash
uv sync
uv run pytest                         # Device-free unit tests
uv run uiautomation doctor            # Check Xcode, simulator, Appium, WebDriverAgent
uv run uiautomation devices           # Show which simulator a run would use, and why

# After installing the iOS toolchain (see Requirements)
uv run uiautomation smoke
```

Device tests start a local Appium server automatically or reuse one already running.
On a simulator, WebDriverAgent is built once before the first test (up to 10 minutes on
a first run) and reused until Xcode or the XCUITest driver changes, so the default
120-second test timeout is enough.

## Current coverage

| App | Bundle ID | Automated coverage |
| --- | --- | --- |
| Settings | `com.apple.Preferences` | Home readiness, General/About, plus physical-device Wi-Fi, display, search, and radio cases |
| Calendar | `com.apple.mobilecal` | Onboarding, verified date navigation, owned draft cleanup, calendar lists, and opt-in saved-event lifecycle |
| Contacts | `com.apple.MobileAddressBook` | Opt-in create, relaunch, exact-name search, Unicode editing, deletion, and cleanup |
| Messages | `com.apple.MobileSMS` | Home, compose/cancel, recipient text, plain/Unicode/multiline drafts, discard, and seeded-conversation navigation |
| Maps | `com.apple.Maps` | Apple Park simulated location by default, location allow/deny, search editing, driving/walking previews, and opt-in guidance |
| Reminders | `com.apple.reminders` | Lists overview past first-launch screens, default list round trip, discarded draft, and opt-in create/complete/delete lifecycle |
| Safari | `com.apple.mobilesafari` | Local fixture pages (links, Back, form input) and an apple.com menu journey |
| Photos | `com.apple.mobileslideshow` | Library readiness, viewer date check, and opt-in imported-photo Favorite/delete lifecycle |
| Files | `com.apple.DocumentsApp` | On My iPhone and Recently Deleted, and opt-in folder create/rename/delete/purge lifecycle |

Messages tests do not send messages. Every Maps test temporarily sets the simulator
location to Apple Park, Cupertino. Route previews still use explicit coordinates
through the native Maps URL handler. An opt-in case starts and ends turn-by-turn
guidance from My Location. Manual origin editing, real movement, and rerouting are
outside current automated coverage.

Safari's local-page tests use pages from `tests/integration/fixtures/site/`, served
on `127.0.0.1` during the run, so they need no internet. The apple.com journey checks
only structure that outlives marketing copy and carries the `network` marker. The
Photos lifecycle leaves its deleted photo in the passcode-locked Recently Deleted
album, so run it only on a disposable simulator. Other apps listed in `SystemApps`
have bundle identifiers, not test suites.

Flows were exercised on an English iOS 27.2 iPhone 18 Pro simulator. Locators and
seed-data assumptions are runtime-specific; installed older runtimes are not a
guarantee that these app flows will pass. The iPhone Duo simulator is not yet
automatable: on Xcode 27.2 every element reports itself as not visible.

## Requirements

Unit tests need Python 3.12+ and [uv](https://docs.astral.sh/uv/). Device tests also
need macOS with Xcode 27+ and Device Hub, an iPhone simulator or configured physical
device, Node.js, and Appium with the XCUITest driver. Maps and the Safari apple.com
journey need internet access.

See [setup](docs/setup.md) for installation, the read-only `doctor` checks, choosing a
simulator, parallel runs, display settings, what a device run changes on the
simulator, and fixes for common failures.

## Run tests

### Local presets

The CLI runs these presets. It keeps pytest's terminal output and exit status and
saves each invocation under its own `artifacts/local-<id>/` directory.

```bash
uv run uiautomation unit
uv run uiautomation integration
uv run uiautomation all
uv run uiautomation smoke
uv run uiautomation journey
uv run uiautomation locators        # Key page locators that no longer match
uv run uiautomation accessibility   # Focusable controls with no accessibility label
uv run uiautomation rerun           # Only the latest run's failures, same target
```

`unit` selects `tests/unit`; `integration` selects `tests/integration`; `all`
selects both. `smoke` selects the 10 integration smoke checks; `journey` selects
integration journeys excluding saved-data and Maps guidance cases. `locators` and
`accessibility` are opt-in diagnostics over the main screens of every app.
Diagnostics, saved-data lifecycle, and Maps guidance otherwise require their explicit
opt-in flags.

Common options work directly: `--device-name`, `--platform-version`, `--timeout`,
`--headless-simulator`, `--appearance`, `--content-size`, device/signing options,
reset and opt-in flags, `-n`, `-m`, `-k`, `-v`, and `-q`. Use `--` for other pytest
arguments:

```bash
uv run uiautomation integration --email --device-name "iPhone 18 Pro" -- --maxfail=1
```

Runner options such as `--email`, `--email-preview`, `--email-config`, and
`--artifacts-dir` belong before `--`. `uiautomation run --suite NAME` remains
supported with the same options.

Add `--email-preview` to build a summary and `report.html` without sending, or
`--email` to send one after the run. Email is opt-in per run, the SMTP password
stays in macOS Keychain, and plain `uv run pytest` never sends email. See
[reporting](docs/reporting.md#opt-in-local-email) for sender setup and delivery details.

### Parallel simulators

```bash
uv run uiautomation all -n 2
```

Each worker gets its own simulator (`UIAutomation Worker <n> – <model> <iOS>`, created
once with the target's model and runtime and kept booted between runs), its own Appium
and WebDriverAgent ports, and its own copy of the WebDriverAgent build. Device runs
switch xdist to `--dist worksteal` so an idle worker takes queued tests. On an
8-core Mac, `all -n 2` took about 7.6 minutes against 11–12 serially. Physical
devices, remote Appium servers, `--run-lifecycle`, and `--run-maps-navigation` stay
serial. See [setup](docs/setup.md#run-simulator-tests-in-parallel).

### Dark mode and large text

```bash
uv run uiautomation smoke --appearance dark
uv run uiautomation smoke --content-size accessibility-extra-extra-extra-large
```

`--appearance` (`light`, `dark`) and `--content-size` (the 12 Dynamic Type sizes)
change the simulator with `simctl ui` once the session starts, and restore the
original values when it ends, even after a failure. `rerun` repeats them. They need a
simulator, not `--udid`.

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
has 10 cases: Settings, Calendar, Reminders, Safari, Photos, and Files launch;
Messages home and compose/cancel; and Maps landmark search with location denied and
allowed.

```bash
# Smoke checks on the default simulator
uv run pytest --run-integration -m smoke

# One app, optionally combined with smoke or journey
uv run pytest --run-integration -m "messages and smoke"
uv run pytest --run-integration -m maps

# Safari without the internet
uv run pytest --run-integration -m "safari and not network"

# Cross-app navigation journeys, without opening Device Hub
uv run pytest --run-integration -m journey --headless-simulator

# Full integration selection; hardware-only cases skip on simulator
uv run pytest --run-integration tests/integration

# One test
uv run pytest --run-integration \
  tests/integration/test_settings.py::TestSettingsNavigation::test_settings_app_launches \
  --device-name "iPhone 18 Pro"
```

`journey` includes Settings General/About, Calendar day/month and new-event/cancel,
Messages discard/conversation round trips, Maps Directions/route/repeated-search
flows, the Reminders list and discarded draft, Safari's local pages and apple.com,
Photos' viewer, and Files' locations. Selecting `regression` is not a substitute for
running `tests/integration`; the marker does not mark every integration test.

### Opt-in suites

```bash
# Start guidance from Apple Park, then end the route
uv run pytest --run-integration --run-maps-navigation -m maps_navigation \
  --device-name "UIAutomation Maps" --timeout=600

# Create, change, and remove owned Calendar, Contacts, Reminders, Photos, and Files data
uv run pytest --run-integration --run-lifecycle -m lifecycle \
  --device-name "UIAutomation Worker 0 – iPhone 18 Pro 27.2" --timeout=600

# Environment observations, locator health, and accessibility labels
uv run pytest --run-integration --run-diagnostics -m diagnostic
```

Guidance and lifecycle cases need an explicitly named simulator and never run on
physical devices; the parallel worker simulators are convenient disposable targets.
Lifecycle tests generate unique names, register cleanup before creating anything, and
remove only what they created. Diagnostics can accept an empty environment, so their
results do not establish event or network correctness. See
[lifecycle testing](docs/lifecycle-testing.md), [Messages](docs/messages-testing.md),
[Maps](docs/maps-testing.md), [Reminders](docs/reminders-testing.md),
[Safari](docs/safari-testing.md), [Photos](docs/photos-testing.md), and
[Files](docs/files-testing.md) for isolation, seed data, and exact assertions.

## Reports and failure evidence

Every executed run writes `artifacts/<run-id>/run.json` with the commit, selected
tests, target, options, tool versions, phase durations, and outcomes. On failure,
hooks add a folder with the screenshot, page XML, Appium log, and matching simulator
crash reports when available. Each run ends with a **Failure artifacts** section
listing those files, and HTML reports show the screenshot inline and link the rest.
Use `--artifacts-dir PATH` to change the output root.

```bash
uv run uiautomation history --limit 15        # Recurring failures and slow setup
uv run uiautomation history --flaky --runs 20 # Tests that keep flipping pass/fail
uv run uiautomation history --json
uv run uiautomation rerun                     # Retry only the latest failures
```

`--flaky` ranks tests that both passed and failed on the same target by how often the
result flipped, so a fixed regression ranks below a flaky test. See
[reporting](docs/reporting.md) for manifest contents, crash collection limits, run
comparison, reruns, locator health, and accessibility labels.

## Target selection and configuration

Simulator name and runtime arguments are exact filters; either may be omitted. Among
matching available iPhones, the model decides first, in this order:

1. iPhone 18 Pro
2. iPhone 17 Pro
3. iPhone 16 Pro
4. iPhone 15

Within a model, its pinned runtime wins (iPhone 18 Pro / iOS 27.0, iPhone 17 Pro /
iOS 26.4, then 26.2 and 26.0, iPhone 16 Pro / iOS 18.5, iPhone 15 / iOS 17.0), then the
newest installed runtime. If no preferred model matches, the newest runtime wins, with
name as the tie-breaker. Parallel-run worker simulators are never chosen by default.
`uiautomation devices` shows the choice and the reason; explicit mismatches list
available choices.

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
| `--appearance` | unchanged | `light` or `dark` for the run; restored afterwards (simulator only) |
| `--content-size` | unchanged | Dynamic Type size for the run; restored afterwards (simulator only) |
| `-n` | serial | Parallel workers; each simulator worker gets its own simulator and ports |
| `--artifacts-dir` | `artifacts` | Root for run artifacts |
| `--udid` | unset | Physical device identifier; omit for simulator selection |
| `--team-id` | unset | Signing team for physical-device WebDriverAgent |
| `--timeout` | `120` | pytest-timeout limit in seconds; the test that starts the session gets 300 s more |

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

The first run builds and installs WebDriverAgent during session start and may require
trusting its developer certificate. Tests marked `real_device` skip on simulators.
Maps cases and Safari's local-page cases skip on physical devices; current Messages
cases assume simulator seed data and are not a delivery-validation suite.

## Project layout

```text
UIAutomation/
├── src/uiautomation/
│   ├── drivers/                  # Driver config, sessions, system bundle IDs
│   ├── pages/
│   │   ├── base_page.py          # Waits, switches, scrolling, health/label checks
│   │   ├── system_prompts.py     # Known permission prompts and their answers
│   │   ├── settings/  calendar/  contacts/  messages/  maps/
│   │   └── reminders/  safari/  photos/  files/
│   ├── utils/                    # Simulators, parallel slots, WDA, artifacts, history, email
│   ├── cli.py                    # Presets, rerun, history, devices, doctor
│   └── pytest_plugin.py          # CLI options, fixtures, collection, artifacts
├── tests/
│   ├── unit/                     # Device-free tests, including page contracts
│   └── integration/              # One module per app, plus locator and label checks
│       └── fixtures/site/        # Local pages served to Safari
├── docs/                         # Setup, per-app coverage, reporting, CI
├── scripts/inspect_locators.py   # Explicit locator-discovery utility
├── .github/workflows/            # Linux checks + gated Mac smoke/journeys
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

Available app fixtures are `settings_app`, `calendar_home`, `calendar_draft`,
`messages_home`, `message_draft`, `maps_home`, `reminders_home`, `reminder_draft`,
`safari_home`, `photos_library`, and `files_home`. `fixture_site` serves the local
Safari pages. `driver` exposes the raw Appium driver; `app_launcher` controls app
lifecycle. `restored_wifi` restores radio state and skips on simulators. Mark
hardware-specific tests with `@pytest.mark.real_device(reason="...")` so they skip
before fixture setup.

Import runtime modules as `uiautomation.*`. Page objects inherit `BasePage`:

```python
from uiautomation.pages.base_page import BasePage


class MyAppPage(BasePage):
    SAVE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Save")
    HEALTH_LOCATORS = ("SAVE_BUTTON",)  # Checked by `uiautomation locators`

    def save(self) -> None:
        """Tap the app's Save control."""
        self.click(self.SAVE_BUTTON)
```

Prefer accessibility IDs, then iOS predicates/class chains; use XPath only when
needed. Wait for meaningful live controls and verify resulting state. Register
cleanup before mutations. Answer system permission prompts through
`pages/system_prompts.py` (`KNOWN_PROMPTS`); unknown alerts fail the run. List only
always-present controls in `HEALTH_LOCATORS`; rows below the fold are absent from the
accessibility tree. Full XML is for diagnostics, not a readiness assertion.

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
`xcode-select -p`, and list installed simulators with `uiautomation devices`. Inspect
live accessibility controls when locators change; increasing waits cannot repair an
incorrect locator. After an iOS update, `uiautomation locators` reports every renamed
control at once.

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
uv build
```

CI runs Ruff, Pyright, and unit tests with coverage on Linux (Python 3.12) for every
push and pull request. The Mac smoke and journey workflows need a self-hosted Mac
runner and the `ENABLE_SIMULATOR_CI` variable; without them they are skipped, and
device suites run locally. See [CI setup](docs/ci.md).

Runtime dependencies are Appium's Python client and Selenium; pytest, plugins,
Ruff, and Pyright are development dependencies. `uv sync --no-dev` installs only
runtime dependencies. The wheel contains `uiautomation`; tests and scripts remain
checkout utilities. Use `uv add <package>` or `uv add --dev <package>` to add one.

## License

Project metadata declares the MIT license.
