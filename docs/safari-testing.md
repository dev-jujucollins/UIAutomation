# Safari simulator testing

Inspected November 2, 2026: Xcode 27.2, iOS 27.2, iPhone 18 Pro simulator.

## Two kinds of test

| Test | Site | Purpose |
| --- | --- | --- |
| `test_load_follow_link_and_go_back`, `test_form_input_reaches_the_page` | `tests/integration/fixtures/site/`, served on `127.0.0.1` by `utils/local_site.py` | Safari's own behavior (load, links, Back, form input) with no dependence on the internet |
| `test_apple_com_menu_to_iphone_and_back` (`network` marker) | `https://www.apple.com` | A real HTTPS site: menu → iPhone menu → Explore All iPhone, then Back |

The apple.com test checks only structure that outlives marketing copy: the
`Global, navigation` and `iPhone family, navigation` landmarks, the `Menu` and
`iPhone menu` buttons, the `Explore All iPhone` link, and the address bar host. When
apple.com changes those, update the constants at the top of `test_safari.py`.

Offline, skip it with `-m "safari and not network"`. Physical devices cannot reach this
Mac's `localhost`, so the local-page tests skip with `--udid`.

## Observed behavior

| Screen | Behavior and handling |
| --- | --- |
| First launch | Start Page card "Include topics from other devices" (Not Now), then "Safari search now shows personalized suggestions…" (Continue). `SafariPage` taps each only when its text is on screen |
| Address bar | `TabBarItemTitle` while showing a page, `URL` while editing. Its value is the host with a left-to-right mark (`‎apple.com`), which `host()` strips |
| Submitting a URL | Typing a trailing return; the keyboard's Go key is missing when the simulator hides the software keyboard |
| Web content | Exposed by accessible name: headings and text as StaticText, links as Link, `<nav aria-label>` landmarks as Other, inputs as TextField named by `aria-label` |
