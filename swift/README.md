# UIAutomation — Swift / XCUITest

A native Swift port of the Python/Appium device tests in `../tests/integration`. It drives
the same Apple system apps (Settings, Calendar, Contacts, Messages, Maps, Reminders,
Safari, Photos, Files) directly through XCUITest: no Appium server, Node, or
WebDriverAgent. The Python suite is unchanged and still runs on its own.

## Run

Requires Xcode 27+ and an iOS simulator. From this folder:

```bash
./run-tests.sh                           # everything that needs no opt-in
./run-tests.sh RemindersTests            # one app
./run-tests.sh MessagesTests/testMessagesHomeIsReady
./run-tests.sh --plan Smoke              # the 10 smoke checks
./run-tests.sh --plan Journey            # journeys, minus saved-data and Maps guidance
./run-tests.sh --device "iPhone 18 Pro" --os 27.2 SettingsTests
```

`xcodebuild` boots the simulator without a window; run `open -a Simulator` first to
watch. Or open `UIAutomationSwift.xcodeproj` in Xcode, pick a test plan, and press Cmd+U.

### Reports and email

```bash
./run-tests.sh --plan Smoke --email-preview   # run.json, report.html, email preview
./run-tests.sh --plan Smoke --email           # ...and send it
uv run uiautomation swift --plan Smoke        # from the repo root: record without email
```

These go through the Python CLI, which runs the tests, reads Xcode's result bundle, and
writes `run.json` and a self-contained `report.html` under `../artifacts/local-<id>/`.
Email uses the same sender setup as the Python suite, and `uiautomation history` covers
both suites. See [reporting](../docs/reporting.md#swift-xcuitest-runs).

### Opt-in tests

| Flag | Enables | Python equivalent |
| --- | --- | --- |
| `--lifecycle` | Tests that save and delete their own data (reminder, contact, event, folder, photo) | `--run-lifecycle` |
| `--maps-navigation` | Maps turn-by-turn guidance from Apple Park | `--run-maps-navigation` |
| `--diagnostics` | Locator-health and accessibility-label checks | `--run-diagnostics` |

Without its flag, an opt-in test reports as skipped. Run `--lifecycle` only on a
disposable simulator: the Photos test leaves its deleted photo in the passcode-locked
Recently Deleted album.

```bash
xcrun simctl create "UIAutomation Swift Lifecycle" "iPhone 18 Pro" com.apple.CoreSimulator.SimRuntime.iOS-27-2
./run-tests.sh --device "UIAutomation Swift Lifecycle" --lifecycle
```

The flags set `TEST_RUNNER_UIAUTOMATION_RUN_*` environment variables, which `xcodebuild`
passes to the tests; see `UIAutomationUITests/Support/RunOptions.swift`.

## Layout

| Path | Contents |
| --- | --- |
| `project.yml` | [XcodeGen](https://github.com/yonaskolb/XcodeGen) spec; `xcodegen generate` rebuilds the `.xcodeproj` |
| `TestPlans/` | `All`, `Smoke`, `Journey` |
| `UIAutomationUITests/<App>/` | Page objects and tests for one app |
| `UIAutomationUITests/Support/` | Base test case, waits, system prompts, run options, fixture web server |
| `HostApp/` | The app XCUITest builds against; also imports the Photos test's photo |

After adding or renaming a Swift file, run `xcodegen generate`.

## How it maps to the Python suite

| Python | Swift |
| --- | --- |
| `BasePage` subclasses with locator tuples | `struct` page objects with `XCUIElement` properties |
| pytest fixtures (`reminders_home`, `calendar_draft`, …) | `setUpWithError()` and small helpers in each test class |
| `request.addfinalizer` | `addCleanup { }` on `SystemAppTestCase`, run newest first |
| `smoke` / `journey` markers | `Smoke` / `Journey` test plans |
| `@pytest.mark.parametrize` | One test method per case |
| `answer_system_prompt` | `SystemPrompts.answer(in:context:permission:)` |
| `mobile: deepLink` | `app.open(url)` |
| `simctl location` / `privacy reset` | `XCUIDevice.shared.location`, `app.resetAuthorizationStatus(for:)` |
| `simctl addmedia` | `HostAppHelper.importPhoto` (through the host app) |
| Local `http.server` for Safari pages | `FixtureSite`, serving the same `tests/integration/fixtures/site` files |
| Failure screenshot, page XML | An attached screenshot and accessibility hierarchy, plus Xcode's screen recording |
| pytest-html report, email summary | `report.html` and email from `uiautomation swift` |
| Unlabelled-control query | `performAccessibilityAudit(for: .sufficientElementDescription)` |

## Notes for maintainers

- **Idle waits.** XCUITest waits for an app to go idle around every event. Maps and an
  open Files context menu never report idle, which costs a minute per tap, so those page
  objects turn the waits off (`setIdleWaits`, `withoutIdleWaits` in `Support/Support.swift`)
  and wait for explicit state. This uses a private XCUITest option observed on Xcode 27.2;
  if a later Xcode drops it the helper does nothing and those tests get slow, not wrong.
- **`isVisible`, not `isHittable`.** `isHittable` and `frame` record a test failure for
  some off-screen or just-removed elements. `isVisible` checks existence and screen
  bounds first.
- **`appears(timeout:)`, not `waitForExistence`.** The built-in wait spends about a
  second even when the element is already there.
- **Photos import** asks for permission to add to the library on every run; the helper
  resets the answer first and taps Allow.

## Not ported

- **Physical-device Settings tests** (Wi-Fi, display, brightness, True Tone, Airplane
  Mode, search, Software Update) and Calendar's account-names test. They cannot be
  verified on a simulator.
- **Some Python tooling around the tests**: `doctor`, automatic device selection,
  parallel worker simulators, `rerun`, crash-report collection, `--appearance` and
  `--content-size`. Run history and email reports do cover Swift runs. Xcode covers some
  of the rest natively (`-parallel-testing-enabled`, `-test-iterations`).
