# Reminders simulator testing

## Verified target and behavior

Inspected October 30, 2026: Xcode 27.2, iOS 27.2, iPhone 18 Pro simulator with no
Apple Account.

| Screen | Observed behavior and test handling |
| --- | --- |
| First launch | iOS 27 staged contacts prompt, then "Welcome to Reminders" (Continue), then the app alert "Enable iCloud Syncing?" (Not Now). The contacts prompt and alert are in `pages/system_prompts.py`; the session reset also denies Reminders contacts access so the prompt rarely appears |
| Relaunch | Reminders reopens the last screen. `RemindersHomePage.wait_until_ready` taps Back out of a restored list until the lists overview (`Reminders.TTRIAccountsListsView`) shows |
| iCloud banner | The overview shows "Sync Reminders with iCloud"; its "Go to Settings" opens Settings' Apple Account sign-in. Page objects never tap it |
| New Reminder | From the overview, `New Reminder` opens a sheet (`Quick Entry Title Field`, Done, Cancel). Inside a list the same button adds an inline row instead, so tests create reminders only from the overview |
| Discard | Cancel with a typed title shows "Are you sure you want to discard this new reminder?" with **Discard Changes** |
| Rows | Cells labelled `<title>, Incomplete` / `<title>, Completed`; the checkbox is `Circle`. Test titles never contain commas |
| Complete | The row becomes `Completed` immediately and leaves the list about 5 s later; it then appears in the **Completed** smart list as `<title>, Completed, in <list>` |
| Delete | Swipe a row left, tap **Delete**; there is no confirmation |

## Run

```bash
# Overview, list navigation, discarded draft (no data kept)
uv run pytest --run-integration -m reminders

# Owned-data lifecycle: create, relaunch, complete, find in Completed, delete
uv run pytest --run-integration --run-lifecycle -m "reminders and lifecycle" \
  --device-name "UIAutomation Worker 0 – iPhone 18 Pro 27.2" --timeout=300
```

The lifecycle test generates `UIAutomation <hex>`, checks that the title is unused, and
registers cleanup before creating anything. Cleanup deletes only that exact title, from
both the default list and Completed. Any isolated simulator works for `--device-name`;
the parallel-run worker simulators are a convenient choice.
