# Continuous checks

## Pull requests and pushes

`.github/workflows/tests.yml` runs Linux jobs for Python 3.10 (the minimum
supported version) and 3.12 (the development version). Each job installs the
locked, noneditable package, checks Ruff formatting/lint and Pyright, and runs
device-free unit tests with branch coverage.
`UV_PYTHON` is set per matrix job so the checkout's `.python-version` cannot
silently switch the Python 3.10 job back to the development interpreter.

Every run uploads `unit-python-<version>` for 14 days, including:

- `reports/unit.html` and `reports/unit.xml` (JUnit).
- `reports/coverage.xml` and `reports/coverage/index.html`.
- `artifacts/<run-id>/run.json` and any failure evidence.

Coverage is an observable baseline, with no arbitrary pass threshold. Inspect
missing branches and add tests for meaningful failure paths before setting a
future threshold. The matrix verifies Python compatibility, not iOS runtime
compatibility.

Local validation on September 28, 2026 passed all 285 unit tests on Python 3.10.0
and 3.12.12. The 3.10 run used an isolated environment and the installed
noneditable package. Python 3.12 coverage measured 73.58% of lines and 55.06% of
branches. Ruff formatting/lint and Pyright passed. These local results do not
claim that the GitHub workflows have completed.

## Dedicated simulator runner

`.github/workflows/simulator-smoke.yml` supports manual dispatch and a nightly
schedule at 10:17 UTC. Nightly execution is disabled until the repository variable
`ENABLE_SIMULATOR_CI` is set to `true`; manual dispatch does not require that flag.
The workflow must be on the default branch for scheduled execution.

Provision a dedicated Apple Silicon Mac runner with these labels:

```text
self-hosted, macOS, ARM64, uiautomation, xcode-27, ios-27
```

Configure the runner before enabling the schedule:

1. Install and select Xcode 27, complete its first-launch setup, and install the
   iOS 27.0 simulator runtime. Ensure the runner account can run `xcodebuild` and
   `xcrun` without interactive prompts.
2. Install Node.js, Appium, and its XCUITest driver under the runner account.
   Keep their tested versions stable; the run manifest records installed versions.
   Appium must be on the runner service's `PATH`, which may differ from a terminal.
3. Create one simulator named `UIAutomation CI`, using an available iPhone type
   and iOS 27.0. Configure English UI; these app locators use English labels.
   For example, after confirming the identifiers exist:

   ```bash
   xcrun simctl create "UIAutomation CI" \
     com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro \
     com.apple.CoreSimulator.SimRuntime.iOS-27-0
   ```

4. Give the runner an active macOS user session suitable for XCUITest and network
   access for Maps search. Keep the simulator dedicated to this workflow.
5. Dispatch `Simulator smoke` manually and inspect the results before enabling
   `ENABLE_SIMULATOR_CI=true`.

The workflow installs Python 3.12 and locked Python packages, runs the read-only
doctor check, then runs the existing six smoke cases serially on the exact
simulator/runtime. It allows ten minutes per test for an initial WDA build and
thirty minutes for the job. One concurrency group queues runs instead of
interrupting a device session. No simulator is erased, no messages are sent,
and no lifecycle data-creation suite is selected.

Simulator reports and failure evidence upload for 14 days under
`simulator-smoke-<run-id>`. Download and extract the whole bundle; keeping
`reports/` beside `artifacts/` preserves HTML evidence links.

This workflow does not run on pull-request events. Use a dedicated runner and
trusted branches for manual dispatch: self-hosted jobs execute checked-out code
on that Mac. Enabling the schedule and provisioning the runner are repository
administration steps; adding the workflow alone does not provide a runner.

## Run the same checks locally

```bash
uv sync --locked
uv run pytest tests/unit --cov=uiautomation --cov-branch \
  --cov-report=term-missing --cov-report=xml:reports/coverage.xml \
  --cov-report=html:reports/coverage \
  --junitxml=reports/unit.xml --html=reports/unit.html --self-contained-html
```
## Weekly simulator journeys

`simulator-journeys.yml` runs Sundays at 10:47 UTC when `ENABLE_SIMULATOR_CI`
is enabled, using the same dedicated runner labels and `UIAutomation CI` simulator
as smoke tests. Both workflows share a concurrency group to prevent device overlap.
Scheduled runs select journeys excluding lifecycle and Maps navigation cases.
Manual dispatch offers separate `lifecycle` and `navigation` checkboxes, off by
default; only selecting them enables saved-data or turn-by-turn coverage.
Journey artifacts remain available for 30 days. The workflow must be pushed to
GitHub and the dedicated runner connected before these checks can execute.
