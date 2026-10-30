# Setup and environment diagnostics

Unit tests need only Python 3.12+ and uv. Local iOS integration tests additionally
need macOS, Xcode 27+, an installed iOS simulator runtime, Node.js, Appium, and the
XCUITest driver. Install Python dependencies from the checkout:

```bash
uv sync
uv run pytest
```

For device testing, install Appium and its iOS driver:

```bash
npm install -g appium
appium driver install xcuitest
```

Install simulator runtimes in Xcode Settings and create simulators in Device Hub or
with `simctl`. The framework boots existing simulators; it does not create them or
download Xcode, runtimes, Appium, or drivers. Any iPhone simulator on iOS 27.0 works;
the [Maps](maps-testing.md), [Messages](messages-testing.md), and
[lifecycle](lifecycle-testing.md) guides describe optional dedicated simulators.

## Choose a simulator

```bash
uv run uiautomation devices
uv run uiautomation devices --device-name "iPhone Air" --json
```

Lists available iPhone simulators by runtime, marks the one a run would use, and says why.
Without options the default is iPhone 18 Pro on its pinned runtime, or on the newest installed
one. Pass the same `--device-name` / `--platform-version` to any suite command to change the
target; `devices` resolves them exactly as a run does and exits 1 when nothing matches.

## Check a machine before running iOS tests

```bash
uv run uiautomation doctor
uv run uiautomation doctor --device-name "iPhone 18 Pro" --platform-version 27.0
uv run uiautomation doctor --headless-simulator --json
```

The default doctor inspects the host without booting, creating, resetting, or
shutting down simulators, starting Appium, or installing dependencies. It reports:

- Host and Python version, Node.js version, selected Xcode version and path.
- Device Hub availability, with `DEVELOPER_DIR` respected when set.
- Available iPhone simulators, including runtime, state, and UDID.
- The simulator selected by the same preference and exact-filter rules as pytest.
- Appium and installed XCUITest driver versions.
- The server's `/status` response, requiring an explicit `value.ready: true`.

Normal commands have a 30-second limit; server requests have a 3-second timeout.
The command exits `1` when a required check fails and `0` otherwise. JSON output
contains `ok`, `checks`, `simulators`, and `selected_simulator`. Individual checks
have a `pass`, `warn`, or `fail` status, a detail, and optional next-step guidance.
Passing preflight does not prove app locators or WebDriverAgent work: run the smoke
suite to verify the entire toolchain.

An absent local server is a warning because the test framework normally starts
Appium automatically. To require an already running server, including a custom
base path:

```bash
uv run uiautomation doctor --appium-server http://localhost:4723/wd/hub --require-server
```

An unavailable remote endpoint always fails. The doctor still inspects **this
Mac's** local simulator setup; it cannot certify the remote host or physical
device signing, pairing, trust, or provisioning.

## Optional upstream XCUITest doctor

```bash
uv run uiautomation doctor --run-driver-doctor
```

This explicitly opts into `appium driver doctor xcuitest`, bounded to 60 seconds.
It is separate from the read-only defaults because the upstream doctor can apply
automatic fixes and recent XCUITest drivers may start a device tunnel while
checking optional dependencies. A skipped upstream doctor is reported as a
warning. Required upstream failures fail the overall report; optional upstream
recommendations do not necessarily prevent this project's simulator tests.

## What a device run changes

One Appium driver session is reused per pytest run. Integration tests run serially;
parallel device execution is rejected. App fixtures establish each test's starting
state and register termination cleanup before launching the app.

For simulator runs, the framework:

- Finds an existing target and boots it if needed.
- Opens Device Hub from `DEVELOPER_DIR` or the Xcode selected by `xcode-select`.
  `--headless-simulator` skips that window. Appium receives `isHeadless` to match:
  windowed runs reuse the open Device Hub, while headless mode would make Appium quit
  Device Hub and reboot the simulator without a window.
- Starts local Appium if the configured local server is unavailable. An existing
  server is reused and supplies its own installed drivers.
- By default, terminates Settings/Calendar and resets their privacy permissions
  once per session. This does not erase app data.

Per-app cleanup has additional rules:

- Settings Wi-Fi mutation fixtures restore the initial radio state.
  The brightness mutation case verifies the changed slider reading and restores
  its original value; invalid readings fail instead of returning a fallback.
- Messages clears only the test-owned compose draft before cancellation; existing
  conversation drafts are preserved.
- Maps sets the selected simulator's location to Apple Park before each test,
  handles location prompts, dismisses owned cards, terminates Maps, and clears
  the simulated location and authorization on teardown. Searches can remain in Recents.

`--skip-simulator-state-reset` or `--no-reset` skips the session-level Settings/Calendar
reset. Neither disables app fixture cleanup or Maps' per-test permission resets.
`--restart-simulator` takes effect only when session-level reset is enabled.

Setup subprocesses have bounded timeouts. Pytest defaults to 120 seconds per test.
Simulator runs against a local Appium build WebDriverAgent into
`artifacts/wda-derived-data` after collection and before the first test, so the build
(up to 10 minutes on a first run) is not charged to any test's timeout. The build records
the WebDriverAgent and Xcode versions that produced it and is rebuilt when either changes;
`uiautomation doctor` reports whether it is current. Physical devices and remote Appium
servers still build WebDriverAgent during session start and may need `--timeout=600`.

## Resolve common failures

- **Xcode missing, too old, or wrong selection:** Install Xcode 27+ and select it
  in Xcode Settings > Locations. Open Xcode once to complete first-launch setup.
  `DEVELOPER_DIR`, if set, overrides the system selection.
- **Device Hub missing:** Select the complete Xcode installation. Use
  `--headless-simulator` for both doctor and pytest when a GUI is unnecessary.
- **No matching simulator:** Install the runtime in Xcode Settings, then create
  an iPhone in Device Hub. Match the exact name and runtime listed by the doctor.
- **CoreSimulator inaccessible:** Run diagnostics from a terminal allowed to
  access the local simulator service. A sandbox access error does not establish
  that the runtime is broken.
- **Appium missing:** Run `npm install -g appium` with a supported Node.js version.
- **XCUITest missing:** Run `appium driver install xcuitest`. Ensure Appium can
  access its configured `APPIUM_HOME` (normally `~/.appium`).
- **Server not ready:** Check its host, port, base path, and server logs. A generic
  HTTP 200 page is insufficient; it must return Appium's readiness payload.

## Observed host configuration

The following versions were inspected on September 28, 2026. These are an
observed configuration, not a compatibility guarantee for every dependency
combination or every iOS app flow:

| Component | Observed version |
| --- | --- |
| macOS | 27.2, Apple Silicon |
| Python | 3.12.12; unit suite also verified on 3.10.0 |
| uv | 0.12.19 |
| Xcode | 27.1, build 27A9269 |
| Node.js | 26.10.0 |
| Appium | 3.8.0 |
| XCUITest driver | 10.43.1 |
| Preferred simulator | iPhone 18 Pro, iOS 27.0 |

The selected developer directory was `/Applications/Xcode.app/Contents/Developer`.
Use the following preflight and smoke run to verify a machine end to end:

```bash
uv run uiautomation doctor --platform-version 27.0 --headless-simulator
uv run pytest --run-integration -m smoke --platform-version 27.0 \
  --headless-simulator --timeout=300
```

Create/delete lifecycle journeys use an explicitly isolated simulator; see
[lifecycle testing](lifecycle-testing.md) for their opt-in options and cleanup contract.

### Observed Calendar startup crash

On a freshly erased test simulator, MobileCal produced a FRONTBOARD
`0x8BADF00D` process-launch watchdog report: background launch exceeded the
OS's 30-second allowance while the main thread loaded dependent libraries.
The report preceded WebDriverAgent session readiness and the first test-driven
Calendar activation. Both saved-data lifecycle cases subsequently passed.
This does not establish why library loading was slow, or make that run crash-free.

When a crash dialog appears, preserve its `.ips` report from
`~/Library/Logs/DiagnosticReports/` beside the run's Appium log. Compare the crash
time with session startup and test actions before attributing it to a locator or
data operation. A longer pytest timeout does not change the OS launch watchdog.
