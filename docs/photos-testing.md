# Photos simulator testing

Inspected November 2, 2026: Xcode 27.2, iOS 27.2, iPhone 18 Pro simulator.
Bundle ID: `com.apple.mobileslideshow` (`SystemApps.PHOTOS`).

## Observed behavior

| Screen | Behavior and test handling |
| --- | --- |
| First launch | "What’s New in Photos" (Continue), then the notifications permission prompt (declined via `system_prompts`). Opening Collections later triggers iOS 27's staged contacts prompt; the session reset denies Photos contacts access |
| Library | `PXCuratedLibraryUIView`, summary `Library, N Photos`, Library/Collections/Search tabs. The simulator ships 6 sample photos dated 2009–2018 |
| Grid photos | Image elements named `PXGGridLayout-Info`, labelled `Photo, October 09, 2009, 2:09 PM`. A narrow no-break space (U+202F) precedes AM/PM, and photos from the current year omit the year |
| Viewer | `PUOneUpView` with the date (`October 9, 2009`, or `Today`), a Favorite switch, Share, Delete, and Back |
| Delete | Confirm **Delete Photo**; the photo moves to Recently Deleted for 30 days |
| Recently Deleted | Pinned shelf → Recently Deleted asks for the device passcode. Tests cannot open or empty it |
| Imports | `simctl addmedia` adds a photo, but an open grid does not refresh; relaunch Photos to see it |

## Run

```bash
# Library ready, open a sample photo, check its date, Back (no data changes)
uv run pytest --run-integration -m "photos and not lifecycle"

# Imported-photo lifecycle on a disposable simulator
uv run pytest --run-integration --run-lifecycle -m "photos and lifecycle" \
  --device-name "UIAutomation Worker 0 – iPhone 18 Pro 27.2" --timeout=300
```

The lifecycle test imports one solid-colour PNG, toggles Favorite on and off, and deletes
it. Cleanup is registered before the import and deletes only photos that were not in the
library beforehand. The deleted photo remains in the passcode-locked Recently Deleted
album until iOS purges it after 30 days, so run it only on a disposable simulator.
