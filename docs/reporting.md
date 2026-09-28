# Run reports and failure evidence

Every executed pytest session writes `artifacts/<run-id>/run.json`, even when
all tests pass. `--artifacts-dir PATH` changes the root; collect-only runs do not
write reports or probe native tools.

The manifest records:

- Repository commit, Python and package versions, and host operating system.
- Requested and then resolved device name/runtime when a driver config or session
  becomes available. Runs without those fixtures retain the CLI requests, which
  are unset by default; no device is selected just to produce a report.
- Local Xcode, Appium, and XCUITest driver versions for integration runs only.
  Missing tools produce `null`; version probes have bounded timeouts. An external
  Appium server may use different versions, so local versions are labeled as such.
- Negotiated capabilities from a small allowlist: platform, runtime, device name,
  automation engine, app bundle, reset/headless settings, timeout, language/locale.
  UDIDs, signing teams, provider credentials, unknown fields, and URLs are omitted.
- Start/end timestamps, total elapsed seconds, exit status, and each test's
  setup/call/teardown outcome and duration. A teardown failure makes the combined
  test outcome failed even if its assertion phase passed.

For parallel unit tests, the controller manifest (`worker: null`) includes all
worker results. Worker manifests are also retained. Integration runs remain serial.
Manifest writes are best effort: a filesystem error is logged without changing
the test result. A hard-killed process may leave an incomplete manifest without
end time or summary; completed phase records remain available.

## HTML and JUnit

```bash
uv run pytest tests/unit --html=reports/unit.html --self-contained-html \
  --junitxml=reports/unit.xml

uv run pytest --run-integration -m smoke -n 0 --platform-version 27.0 \
  --html=reports/simulator.html --self-contained-html \
  --junitxml=reports/simulator.xml --timeout=600
```

On failure, each HTML result has links to the available `screen.png`, `page.xml`,
`appium.log`, and `failure.json`. Links are relative to the report, so the HTML and
the artifact tree can move together. `--self-contained-html` embeds report assets;
failure evidence remains separate linked files. Download/extract the complete CI
bundle and open `reports/unit.html` or `reports/simulator.html` locally.

Failure capture runs independently for screenshots, XML, and logs. Missing
evidence is recorded in `failure.json` instead of masking other captures. Setup
and teardown failures receive evidence too when a driver is available. External
Appium servers must provide their logs separately.

The capability allowlist applies only to the manifest. Screenshots, page XML,
tracebacks, and Appium logs are diagnostic content and are not scrubbed; use
test-owned data on the dedicated CI simulator and review bundles before sharing.
