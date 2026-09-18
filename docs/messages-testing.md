# Messages simulator testing

## Verified target and capabilities

Initial inspection: September 17, 2026, Xcode 27.0 (27A5194q), iOS 27.0,
iPhone 17 Pro simulator named `UIAutomation Messages`.

| Capability | Observed behavior and test scope |
| --- | --- |
| First launch | Conversation list appears without onboarding on a fresh simulator |
| Existing conversations | Two simulator-provided sample conversations; tests open the first visible row without assuming its phone number |
| New Message toolbar button | Absent on this runtime |
| Native composer | Appium `mobile: deepLink` with `sms:` opens an empty `CKComposeChat` sheet |
| Recipient | The `To:` field supports entering and clearing uncommitted recipient text |
| Draft body | `messageBodyField` supports plain text, accented characters, emoji, and newlines |
| Discard | Clear body and recipient before Cancel; reopen composer to check that no draft remains |
| Attachments | The conversation's add control opens an attachment interface; attachment selection is outside this initial suite |
| Sending and receipt | A separately authorized September 18 probe sent one message to a seeded sample conversation, displayed Delivered, and preserved the bubble after reopening. Real-device receipt was not verified; the automated suite still has no send action |

These observations describe the inspected simulator, not an assertion of support
across all iOS runtimes. A missing expected control fails with normal artifacts.
Unexpected onboarding also fails setup; add a specific handler after inspecting
that screen rather than clicking arbitrary Continue/Allow buttons.

## Run on an isolated simulator

This workspace already has the `UIAutomation Messages` simulator. On another
Mac with the same device type and runtime installed, create it once:

```bash
xcrun simctl create "UIAutomation Messages" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-27-0
```

Run all eight Messages cases:

```bash
uv run pytest --run-integration -m messages \
  --device-name "UIAutomation Messages" --platform-version 27.0 --timeout=300
```

For a short smoke run, use `-m "messages and smoke"`. For navigation and discard
round trips, use `-m "messages and journey"`. Repeat the full command to verify
that cleanup leaves the next run in the same state. First boot and WebDriverAgent
build may take longer than later runs.

## State ownership and assertions

- `messages_home` terminates/relaunches Messages, then returns from a restored
  conversation to the list. It does not clear existing conversation drafts.
- `message_draft` registers its finalizer before opening the native composer.
  It owns that new compose sheet, including a reopened sheet in the discard test.
- Tests type the synthetic recipient `2025550123` without sending. Recipient
  entry coverage checks the editable text; it does not claim contact resolution
  or delivery validation.
- Cleanup verifies both fields are empty before cancellation, waits for the
  compose sheet to disappear, and verifies home controls. Cleanup failures are
  reported rather than swallowed. App termination remains a separate finalizer.
- Conversation navigation uses simulator seed data. Missing seed data fails with
  an actionable precondition message; tests do not inject private database rows.
- Normal readiness uses live controls. Full XML and screenshots are collected
  for failure diagnostics, not polled as part of readiness.

Page objects live in `src/uiautomation/pages/messages/`; integration tests live
in `tests/integration/test_messages.py`. Device-free regression coverage lives
in `tests/unit/pages/messages/`.

## Later coverage

Use a separately configured physical-device suite, marked `real_device`, for
actual SMS/RCS/iMessage delivery, receipts, notifications, and account sync.
Establish controlled sender/recipient accounts and explicit cleanup before adding
those cases. No placeholder passing or skipped delivery tests are included here.

Attachment selection, search results, contact resolution, committed recipient
removal, and runtime-specific onboarding can be added after their UI and test
data contracts are inspected.
