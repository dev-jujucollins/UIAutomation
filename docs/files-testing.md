# Files simulator testing

Inspected November 2, 2026: Xcode 27.2, iOS 27.2, iPhone 18 Pro simulator.
Bundle ID: `com.apple.DocumentsApp` (`SystemApps.FILES`).

## Observed behavior

| Screen | Behavior and test handling |
| --- | --- |
| First launch | Opens on Recents ("No Recents") with no onboarding |
| Browse | Reopens the last location; tapping Browse again shows the locations list (`DOC.sidebar.item.On My iPhone`, `…Recently Deleted`, `…iCloud Drive`, tags). `FilesPage.open_location` handles both |
| New Folder | More → New Folder immediately creates "untitled folder" with an inline rename field (`DOC.inlineRenameField`); type the name, then Done |
| Folder rows | Cells named `<name>, Folder`, labelled `<name>, N items`. Test names never contain commas |
| Context menu | Long-press (`mobile: touchAndHold`) shows Rename, Delete, Move, Duplicate, … |
| Delete | Immediate, no confirmation; the folder moves to Recently Deleted, labelled `<name>, On My iPhone` |
| Recently Deleted | Not passcode-locked. Long-press → Delete Now asks "Are you sure you want to delete “<name>”?"; `purge_folder` confirms only when the alert names its folder |

## Run

```bash
# Browser ready; open On My iPhone and Recently Deleted (no data changes)
uv run pytest --run-integration -m "files and not lifecycle"

# Folder lifecycle on a disposable simulator
uv run pytest --run-integration --run-lifecycle -m "files and lifecycle" \
  --device-name "UIAutomation Worker 0 – iPhone 18 Pro 27.2" --timeout=300
```

The lifecycle test creates `UIAutomation <hex>`, relaunches, renames it, relaunches,
deletes it, and purges it from Recently Deleted. Cleanup is registered before creation and
removes only those two generated names from both locations, so nothing is left behind.
