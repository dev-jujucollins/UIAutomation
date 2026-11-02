# Lifecycle tests

These tests exercise saved records: create, reopen, edit, delete, and verify deletion.
Calendar and Contacts are described here; the Reminders, Photos, and Files lifecycle
tests follow the same rules and are described in [Reminders](reminders-testing.md),
[Photos](photos-testing.md), and [Files](files-testing.md).
They are opt-in because they temporarily persist data. Use a dedicated English-language
simulator without personal accounts. Tests never run on physical devices.

## Prepare an isolated simulator

Check existing inventory before creating a simulator; do not create duplicate names:

```sh
xcrun simctl list devices available
xcrun simctl create "UIAutomation Lifecycle" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-27-2
```

Use the host's normal clock and timezone on the simulator. Appium's simulator time
command reports the server's clock/timezone. Calendar navigation asserts the displayed
date against that value, not merely the presence of a Today button.

```sh
uv run uiautomation doctor --device-name "UIAutomation Lifecycle"
uv run pytest --run-integration --run-lifecycle -m lifecycle \
  --device-name "UIAutomation Lifecycle" --timeout=600
```

Any disposable simulator works for `--device-name`; the parallel-run worker
simulators (`UIAutomation Worker 0 – iPhone 18 Pro 27.2`) are a convenient choice.
`--run-lifecycle` and an explicit simulator name are required. Without the opt-in,
lifecycle fixtures skip before creating a driver. A name declares the user's selected
test target; the framework does not erase it or assume that its data is disposable.

## Data ownership

Each case uses a unique `UIAutomation` name. Cleanup is registered before creation,
tracks both original and edited names, and deletes only exact matches owned by that
case. Cleanup runs after assertion failures as well as success. Failure to delete an
owned record is reported as a teardown failure with ordinary failure artifacts.

Calendar draft tests also register discard before opening the editor, so a failed
assertion does not leave a compose sheet for the next case. Existing Messages draft
ownership remains unchanged.

The Contacts journey checks search and Unicode names. No messages, calls, invites,
or account changes are part of these tests. Persisted Calendar events have no invitees.

## Local validation

On September 28, 2026, both lifecycle cases passed on `UIAutomation Lifecycle`
(iPhone 18 Pro, iOS 27.0). Calendar and Contacts each verified saved records after
application restarts following creation, editing, and deletion. Cleanup completed.
Contacts exercised `Élise`, `Zoë`, and `O'Connor` within a generated surname,
checking Unicode and apostrophe handling during search and editing.

An initial background Calendar launch hit the OS startup watchdog before the
WebDriverAgent session became ready. The crash report was preserved separately
from the passing assertions; see [setup diagnostics](setup.md#observed-calendar-startup-crash).

A subsequent combined Calendar regression and smoke selection
finished with 17 passed and two physical-device-only Calendar skips. No new
MobileCal or Contacts crash report appeared during that follow-up run. At the time,
the six smoke cases covered Settings, Calendar, Messages (two), and Maps (two).

On November 2, 2026 (iOS 27.2), the Reminders, Photos, and Files lifecycle tests passed
on a parallel-run worker simulator. The Calendar and Contacts lifecycle tests have not
yet been re-run on iOS 27.2.
