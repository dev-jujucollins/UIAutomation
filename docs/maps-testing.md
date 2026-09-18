# Maps testing

## Target and scope

Use an iPhone simulator with iOS 27.0, English UI, and internet access. Any
simulator name works, including automatic target selection. The fixture skips
physical devices before creating a driver session. Existing Appium setup opens
Device Hub for visible runs. An isolated simulator is optional.

```bash
# Optional: create an isolated simulator once
xcrun simctl create "UIAutomation Maps" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-27-0

uv run pytest --run-integration -m maps \
  --platform-version 27.0 --timeout=300
```

The run command selects an available iOS 27.0 simulator. Add `--device-name`
with any existing simulator name to choose one explicitly. First WebDriverAgent
build may take several minutes.

## P0 acceptance cases

| Case | Assertion |
| --- | --- |
| Location denied / allowed | Fresh permission prompt handled with each choice; manual landmark search still works |
| Search editing | Replace and clear landmark/address text; cancel returns home |
| Place details | Search resolves Golden Gate Bridge; place header identity matches and Directions is usable |
| Directions entry | With permission denied, planner retains destination and requests an origin |
| Route previews | Explicit coordinates produce positive duration and distance; endpoint labels match the expected area |
| Travel modes | Driving and walking report selected state and valid metrics; walking summary differs from driving |
| Repeatability | Two search/dismiss cycles return to usable home controls |

Route preview uses the native Maps URL handler with explicit coordinates:
Palace of Fine Arts `(37.8029, -122.4484)` to Golden Gate Bridge area
`(37.8199, -122.4783)`. The destination currently resolves to Golden Gate Bridge
Coastal Trail. This covers route-link entry and native preview controls;
manual origin editing is not automated yet. Search and Directions entry use UI controls.

Network responses receive bounded waits. Assertions do not pin exact ETAs,
route distance, rankings, ratings, business hours, or route geometry.
Missing route metrics fail; a loading/error screen cannot count as a route.
Known fixture destinations are expected to have both driving and walking routes.

## State and cleanup

Before each test, terminate Maps and reset its location authorization. Require
and answer the location prompt explicitly. On teardown, dismiss owned cards,
terminate Maps, and reset location authorization to its unprompted state, even
when setup or assertions fail. This establishes an unprompted baseline on the
selected simulator; it does not restore the simulator's previous location
authorization. Use an isolated simulator if its existing Maps permission state
must be preserved.

Known first-run notification, advertising information, and route safety sheets
are handled explicitly. Unknown alerts fail instead of being silently accepted.
Notification permission is denied when prompted. Searches may remain in Recents;
tests do not rely on Recents or clear unrelated history. No saved places, calls,
messages, or turn-by-turn navigation are created.

Existing framework hooks capture screenshots, UI hierarchy, and available logs
on failure. Discovery captures are local ignored files under
`artifacts/maps-discovery/`.

## Later coverage

P1: address result identity, manual origin editing, unavailable routes,
simulated-location/recenter behavior, pan/zoom, search edge cases, network
loss/recovery, app lifecycle, and accessibility.

P2: test-owned saved places and additional travel modes where supported.
Physical devices: GPS accuracy, real movement/rerouting, compass, navigation
audio, and background navigation. Simulator previews cannot establish these.
