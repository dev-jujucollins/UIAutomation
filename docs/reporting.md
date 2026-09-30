# Run reports and failure evidence

Every executed pytest session writes `artifacts/<run-id>/run.json`, even when
all tests pass. `--artifacts-dir PATH` changes the root; collect-only runs do not
write reports or probe native tools.

The manifest records:

- Repository commit, Python and package versions, and host operating system.
- Working-tree dirty status (`null` when unavailable), including untracked files.
  Filenames and file contents are not recorded.
- Selected repository test names and case count, with parameter values omitted.
  A small allowlist records numeric/boolean execution options; raw command lines,
  marker expressions, server URLs, signing teams, and credentials are excluded.
  Selection therefore aids reproduction but is not an exact replay command.
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

Local simulator failures also collect up to five recent `.ips` crash reports
for the marked app and selected simulator. Host reports must contain matching
simulator identity; reports inside the selected simulator's CrashReporter folder
are already scoped. Collection starts at test setup, excludes old/unrelated
reports and files over 10 MB, and limits scanning to two seconds. Late-arriving
reports may be absent; no crash report does not prove the app did not crash.
Physical-device and legacy `.crash` reports are not collected. Crash reports are
linked alongside screenshots and contain unsanitized diagnostic data too.

## Compare runs

```bash
uv run uiautomation history --artifacts-dir artifacts --limit 15
uv run uiautomation history --artifacts-dir artifacts --json
```

The command reads `run.json` files recursively, excludes worker/unfinished/malformed manifests,
deduplicates run IDs, and groups by test, target kind, device name, and runtime.
Setup or teardown failures count as failed tests even when the call passed.
Output ranks recurring failures then median total duration, with setup duration
shown separately. Mixed passing/failing outcomes flag investigation candidates;
they do not prove flakiness because code and environment can differ across runs.
No retries run automatically. Extract multiple CI bundles under one artifact root
to compare their manifests; keep each run's unique directory name.

## Opt-in local email

Run these commands from the repository root:

```bash
# Normal run: no email configuration, credentials, or network access for reporting
uv run uiautomation unit

# Preview: generates report.html and email.txt without contacting an email service
uv run uiautomation unit --email-preview

# After configuring a sender: one summary per explicitly requested run
uv run uiautomation smoke --email --platform-version 27.0 --timeout=300
```

Suites are `unit`, `integration`, `all`, `smoke`, and `journey`. `integration`
runs the full regular device selection, and `all` includes unit tests as well.
Both enable integration execution without a marker filter. Diagnostics, saved-data
lifecycle, and Maps guidance still need explicit opt-in flags; lifecycle and guidance
also require an explicitly named simulator. The journey preset excludes saved-data
and Maps navigation cases. For example:

```bash
uv run uiautomation integration --email --platform-version 27.0 --timeout=300
uv run uiautomation all --email --platform-version 27.0 --timeout=300
```

Common device, timeout, marker/name selection, reset, and opt-in options work
directly after the suite command. Put other pytest arguments after `--`; they
can override pytest selection. Put runner settings before `--`. Existing
`uiautomation run --suite NAME` commands remain supported. Plain
`uv run pytest` never sends these emails.

Each invocation owns `artifacts/local-<id>/`, so email cannot pick up an older
run's report. Messages include counts, failing test names and phases, elapsed
time, target, and commit. Parameter values and tracebacks are omitted from the
summary text. Each email or preview run also generates a self-contained pytest-html
report at `artifacts/local-<id>/report.html`. Live delivery attaches it as
`report.html`; no extra pytest flags are needed. An explicit `--html` path after
`--` is honored, with self-contained assets enabled automatically. Only a report
created or updated during this invocation can be attached.

The attached report contains pytest details, including captured output and failure
tracebacks. Screenshot, XML, crash, and Appium log files remain local; HTML evidence
links work when the report is opened beside the corresponding artifact tree.
Downloading the attachment alone does not include those files. The summary gives
the local artifact path. Missing/unreadable reports or reports larger than 10 MB
are explained in the summary and omitted, so reporting failures can still be emailed.
If pytest fails before producing a manifest, the email reports its exit status
without inventing test counts. Collection errors and interrupted runs may have
incomplete summaries.

### Sender setup

Copy `email.example.json` to `email.local` and fill in your provider's SMTP
host, port, security mode, username, authorized sender, and recipient.
`email.local` is ignored by Git. `--email-config PATH` can select another file.
Use `starttls` for STARTTLS or `ssl` for implicit TLS; unencrypted SMTP is not
supported. Recipient and sender are single plain addresses.

Store the SMTP password/app password in macOS Keychain as a generic password:
service/name `uiautomation.smtp`, account matching `username` exactly. Create
the entry in Keychain Access; do not put the password in the JSON file, shell
history, or repository. The runner retrieves that entry only after an explicit
`--email` run. A Keychain access prompt may require approval on first use.

Pytest does not supply an email account. Use an SMTP service that supports
username/password authentication over TLS. Providers requiring OAuth-only SMTP
need a separate OAuth integration; this sender does not implement OAuth.
Any supported sender can deliver to a Hotmail recipient.

Email failures print a warning and save `email-status.json`, but retain pytest's
exit status. The preview/summary is saved as `email.txt`. SMTP operations have
timeouts, and delivery is not retried automatically because an ambiguous response
could otherwise cause duplicate messages. No scheduler or email subscriptions
are installed.

The capability allowlist applies only to the manifest. Screenshots, page XML,
tracebacks, and Appium logs are diagnostic content and are not scrubbed; use
test-owned data on the dedicated CI simulator and review bundles before sharing.
