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
| Location denied / allowed | Location prompts are handled with each choice when shown; manual landmark search still works |
| Search editing | Replace and clear landmark/address text; cancel returns home |
| Place details | Search resolves Golden Gate Bridge; place header identity matches and Directions is usable |
| Directions entry | With permission denied, planner retains destination and requests an origin |
| Route previews | Explicit coordinates produce positive duration and distance; endpoint labels match the expected area |
| Travel modes | Driving and walking report selected state and valid metrics; walking summary differs from driving |
| Repeatability | Two search/dismiss cycles return to usable home controls |
| Apple Park guidance (opt-in) | Recenter on simulated Apple Park, route from My Location to Golden Gate Bridge, start guidance, and end the route |

Route preview uses the native Maps URL handler with explicit coordinates:
Palace of Fine Arts `(37.8029, -122.4484)` to Golden Gate Bridge area
`(37.8199, -122.4783)`. The destination currently resolves to Golden Gate Bridge
Coastal Trail. This covers route-link entry and native preview controls;
manual origin editing is not automated yet. Search and Directions entry use UI controls;
search selects an exact-title suggestion if the keyboard Search key is hidden.

Network responses receive bounded waits. Assertions do not pin exact ETAs,
route distance, rankings, ratings, business hours, or route geometry.
Missing route metrics fail; a loading/error screen cannot count as a route.
Known fixture destinations are expected to have both driving and walking routes.

## Apple Park default and navigation

Every Maps test sets its selected simulator to
[Apple Park](https://maps.apple.com/place?_provider=9902&address=Apple+Inc.%2C+One+Apple+Park+Way%2C+Cupertino%2C+CA+95014%2C+Estados+Unidos&coordinate=37.3349%2C-122.00902&name=Apple+Park&place-id=I7C250D2CDCB364A)
at `(37.3349, -122.00902)` before launching Maps. The override is cleared
after each test, including a setup or assertion failure. The guidance case is
still opt-in because it starts a route; use a dedicated, explicitly named
simulator. It grants Maps location access, recenters, and checks that Directions
uses **My Location** as the origin for Golden Gate Bridge, that a positive driving
route is available, and that Maps starts guidance with
a maneuver and the expected destination in its navigation tray.

```bash
uv run pytest --run-integration --run-maps-navigation -m maps_navigation \
  --device-name "UIAutomation Maps" --platform-version 27.0 --timeout=600
```

Use any existing simulator name in place of `UIAutomation Maps`. The navigation
case skips without `--run-maps-navigation` and requires `--device-name`. No Maps
test changes a physical device's location. On the observed iOS 27 simulator,
**Steps** starts turn-by-turn guidance. Teardown taps **End Route** and dismisses
the place card. The simulator proves guidance starts; real movement, rerouting,
and navigation audio still
require a physical-device test.

## State and cleanup

Before each test, terminate Maps, reset its location authorization, and set its
simulated location to Apple Park. Answer the location prompt when shown. On teardown,
dismiss owned cards,
terminate Maps, and reset location authorization to its unprompted state, even
when setup or assertions fail. The simulated location override is also cleared
after every Maps test. This establishes an unprompted baseline on the selected
simulator; it does not restore the simulator's previous location authorization
or location override. Use an isolated simulator if those states must be preserved.

Known first-run notification, widget-location, advertising information, and route
safety sheets are handled explicitly. Unknown alerts fail instead of being silently accepted.
Notification permission is denied when prompted. Searches may remain in Recents;
tests do not rely on Recents or clear unrelated history. No saved places, calls,
or messages are created. The Apple Park case starts and ends one route.

Existing framework hooks capture screenshots, UI hierarchy, and available logs
on failure. Discovery captures are local ignored files under
`artifacts/maps-discovery/`.

## Later coverage

P1: address result identity, manual origin editing, unavailable routes,
pan/zoom, search edge cases, network
loss/recovery, app lifecycle, and accessibility.

P2: test-owned saved places and additional travel modes where supported.
Physical devices: GPS accuracy, real movement/rerouting, compass, navigation
audio, and background navigation. Simulator guidance cannot establish these.
