"""Self-contained HTML report and email body for a Swift (XCUITest) run."""

from __future__ import annotations

import base64
from html import escape
from typing import Any

from uiautomation.utils.xcresult import SwiftTest

# Larger screenshots are left out so emailed reports fit the 10 MB attachment limit.
MAX_EMBEDDED_SCREENSHOT_BYTES = 2 * 1024 * 1024
_SKIP_PREFIX = "Test skipped - "
_LABELS = {"passed": "Passed", "failed": "Failed", "skipped": "Skipped"}

_CSS = """
:root { color-scheme: light dark; --bg:#f6f7f9; --card:#fff; --text:#1c1e21; --muted:#667085;
  --line:#e4e7ec; --pass:#12805c; --fail:#c0352b; --skip:#8a6d1a; --pass-bg:#e7f6ef;
  --fail-bg:#fdecea; --skip-bg:#fbf3d9; }
@media (prefers-color-scheme: dark) { :root { --bg:#111315; --card:#1b1e21; --text:#e8eaed;
  --muted:#9aa4b2; --line:#2c3136; --pass:#4cc38a; --fail:#ff7b72; --skip:#e3b341;
  --pass-bg:#12261d; --fail-bg:#2d1513; --skip-bg:#2a2410; } }
* { box-sizing: border-box; }
body { margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--text);
  font:15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
main { max-width:920px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:17px; margin:32px 0 12px; }
.meta { color:var(--muted); font-size:13px; }
.pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px;
  font-weight:600; letter-spacing:.03em; text-transform:uppercase; vertical-align:middle; }
.passed { color:var(--pass); } .failed { color:var(--fail); } .skipped { color:var(--skip); }
.pill.passed { background:var(--pass-bg); } .pill.failed { background:var(--fail-bg); }
.pill.skipped { background:var(--skip-bg); }
.tiles { display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin:20px 0 0; }
.tile, .card { background:var(--card); border:1px solid var(--line); border-radius:10px; }
.tile { padding:12px 14px; } .tile b { display:block; font-size:24px; line-height:1.2; }
.tile span { color:var(--muted); font-size:12px; }
.card { padding:14px 16px; margin:0 0 12px; overflow:hidden; }
.card.failure { border-left:4px solid var(--fail); }
.card h3 { margin:0 0 6px; font-size:15px; }
code, pre { font:13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }
pre { margin:8px 0; padding:10px 12px; background:var(--bg); border-radius:6px;
  white-space:pre-wrap; overflow-wrap:anywhere; }
img { display:block; max-height:520px; max-width:100%; margin-top:10px; border-radius:8px;
  border:1px solid var(--line); }
table { width:100%; border-collapse:collapse; }
td { padding:6px 0; border-top:1px solid var(--line); vertical-align:top; }
td.status { width:76px; font-weight:600; font-size:13px; }
td.time { width:72px; text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }
.suite { display:flex; justify-content:space-between; align-items:baseline; gap:12px;
  margin-bottom:8px; }
.suite h3 { margin:0; } summary { cursor:pointer; font-weight:600; }
.reason { color:var(--muted); font-size:13px; }
footer { margin-top:32px; color:var(--muted); font-size:12px; overflow-wrap:anywhere; }
@media (max-width:560px) { .tiles { grid-template-columns:repeat(2, 1fr); } }
"""


def format_duration(seconds: float) -> str:
    """Render seconds as ``8.2s`` or ``3m 05s``."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes}m {rest:02d}s"


def verdict(manifest: dict[str, Any]) -> str:
    """One word for the run: failed, passed, or (nothing ran) error."""
    summary = manifest.get("summary") or {}
    if summary.get("failed"):
        return "failed"
    if summary.get("passed") or summary.get("skipped"):
        return "passed" if manifest.get("exit_status") in (0, None) else "failed"
    return "failed"


def _app(suite: str) -> str:
    """``RemindersTests`` -> ``Reminders``."""
    return suite.removesuffix("Tests") or suite


def _reason(test: SwiftTest) -> str:
    return "; ".join(message.removeprefix(_SKIP_PREFIX) for message in test.messages if message)


def _facts(manifest: dict[str, Any], label: str) -> list[str]:
    """Run facts shared by the report header and the email."""
    target = manifest.get("target") or {}
    options = manifest.get("options") or {}
    environment = manifest.get("environment") or {}
    flags = [
        name.removeprefix("run_").replace("_", " ")
        for name in ("run_lifecycle", "run_maps_navigation", "run_diagnostics")
        if options.get(name) is True
    ]
    facts = [
        label,
        f"{target.get('device_name') or 'unknown device'} · iOS {target.get('platform_version') or '?'}",
        f"Opt-ins: {', '.join(flags) if flags else 'none'}",
    ]
    if manifest.get("finished_at"):
        facts.append(f"Finished {str(manifest['finished_at'])[:19].replace('T', ' ')} UTC")
    if environment.get("commit"):
        dirty = " (uncommitted changes)" if environment.get("working_tree_dirty") else ""
        facts.append(f"Commit {str(environment['commit'])[:10]}{dirty}")
    return facts


def render_report(
    manifest: dict[str, Any],
    tests: list[SwiftTest],
    label: str,
    screenshots: dict[str, bytes] | None = None,
    result_bundle: str | None = None,
) -> str:
    """Build the full report as one HTML file with no external resources.

    Args:
        manifest: The run manifest from ``xcresult.build_manifest``.
        tests: The run's tests, in the order to show them.
        label: What was run, e.g. ``Swift · Smoke``.
        screenshots: Failure screenshots (JPEG or PNG bytes) keyed by Xcode test identifier.
        result_bundle: Local path of the ``.xcresult`` bundle, shown for deeper debugging.
    """
    screenshots = screenshots or {}
    counts = {key: sum(test.outcome == key for test in tests) for key in _LABELS}
    state = verdict(manifest)
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>UIAutomation {escape(label)}: {state.upper()}</title>",
        f"<style>{_CSS}</style></head><body><main>",
        f'<h1>UIAutomation <span class="pill {state}">{state}</span></h1>',
        f'<div class="meta">{" &nbsp;·&nbsp; ".join(escape(fact) for fact in _facts(manifest, label))}</div>',
        '<div class="tiles">',
    ]
    for key, text in _LABELS.items():
        parts.append(
            f'<div class="tile"><b class="{key}">{counts[key]}</b><span>{text}</span></div>'
        )
    duration = float(manifest.get("duration_seconds") or 0)
    parts.append(
        f'<div class="tile"><b>{format_duration(duration)}</b><span>Duration</span></div></div>'
    )
    if not tests:
        parts.append(
            '<div class="card failure" style="margin-top:20px"><h3>No tests ran</h3>'
            '<div class="reason">The build or test startup failed. '
            "See the xcodebuild output and the result bundle.</div></div>"
        )

    failures = [test for test in tests if test.outcome == "failed"]
    if failures:
        parts.append(f"<h2>Failures ({len(failures)})</h2>")
    for test in failures:
        parts.append(
            f'<div class="card failure"><h3>{escape(_app(test.suite))} › '
            f"<code>{escape(test.name)}</code></h3>"
        )
        where = f"{test.location} · " if test.location else ""
        parts.append(
            f'<div class="meta">{escape(where)}{format_duration(test.duration_seconds)}</div>'
        )
        for message in test.messages or ("No failure message recorded.",):
            parts.append(f"<pre>{escape(message)}</pre>")
        image = screenshots.get(test.identifier)
        if image and len(image) <= MAX_EMBEDDED_SCREENSHOT_BYTES:
            kind = "png" if image[:8] == b"\x89PNG\r\n\x1a\n" else "jpeg"
            encoded = base64.b64encode(image).decode("ascii")
            parts.append(
                f'<img alt="Screen when {escape(test.name)} failed" '
                f'src="data:image/{kind};base64,{encoded}">'
            )
        elif image:
            parts.append('<div class="reason">Screenshot too large to embed; see the bundle.</div>')
        parts.append("</div>")

    suites: dict[str, list[SwiftTest]] = {}
    for test in tests:
        suites.setdefault(test.suite, []).append(test)
    if suites:
        parts.append("<h2>Results by app</h2>")
    for suite, members in suites.items():
        ran = [test for test in members if test.outcome != "skipped"]
        if not ran:
            # Nothing to show here; its tests are listed under Skipped.
            continue
        failed = sum(test.outcome == "failed" for test in members)
        tally = f"{len(ran) - failed}/{len(ran)} passed"
        total = format_duration(sum(test.duration_seconds for test in members))
        parts.append(
            f'<div class="card"><div class="suite"><h3>{escape(_app(suite))}</h3>'
            f'<span class="meta"><span class="{"failed" if failed else "passed"}">{tally}</span>'
            f" · {total}</span></div><table>"
        )
        for test in ran:
            parts.append(
                f'<tr><td class="status {test.outcome}">{_LABELS[test.outcome]}</td>'
                f"<td><code>{escape(test.name)}</code></td>"
                f'<td class="time">{format_duration(test.duration_seconds)}</td></tr>'
            )
        parts.append("</table></div>")

    skipped = [test for test in tests if test.outcome == "skipped"]
    if skipped:
        parts.append(f'<details class="card"><summary>Skipped ({len(skipped)})</summary><table>')
        for test in skipped:
            parts.append(
                f"<tr><td>{escape(_app(test.suite))} › <code>{escape(test.name)}</code>"
                f'<div class="reason">{escape(_reason(test)) or "No reason recorded"}</div></td></tr>'
            )
        parts.append("</table></details>")

    parts.append(f"<footer>Run {escape(str(manifest.get('run_id') or 'unknown'))}.")
    if result_bundle:
        parts.append(
            " For step-by-step logs, screen recordings and accessibility hierarchies, open "
            f"<code>{escape(result_bundle)}</code> in Xcode."
        )
    parts.append("</footer></main></body></html>")
    return "\n".join(parts)


def render_email_html(manifest: dict[str, Any], tests: list[SwiftTest], label: str) -> str:
    """Build the email body: a small summary that survives mail clients' styling limits.

    Mail clients drop ``<style>`` blocks and scripts, so this uses tables and inline styles.
    """
    state = verdict(manifest)
    colour = "#12805c" if state == "passed" else "#c0352b"
    counts = {key: sum(test.outcome == key for test in tests) for key in _LABELS}
    duration = format_duration(float(manifest.get("duration_seconds") or 0))
    cell = 'style="padding:6px 18px 6px 0;font:14px -apple-system,Segoe UI,Arial,sans-serif"'
    rows = [
        '<div style="font:15px -apple-system,Segoe UI,Arial,sans-serif;color:#1c1e21">',
        f'<p style="font-size:18px;margin:0 0 4px"><strong>UIAutomation: '
        f'<span style="color:{colour}">{state.upper()}</span></strong></p>',
        f'<p style="margin:0 0 14px;color:#667085;font-size:13px">'
        f"{' · '.join(escape(fact) for fact in _facts(manifest, label))}</p>",
        '<table cellpadding="0" cellspacing="0" style="border-collapse:collapse"><tr>',
    ]
    for key, text in _LABELS.items():
        rows.append(f"<td {cell}><strong>{counts[key]}</strong> {text.lower()}</td>")
    rows.append(f"<td {cell}><strong>{duration}</strong> total</td></tr></table>")
    failures = [test for test in tests if test.outcome == "failed"]
    if failures:
        rows.append('<p style="margin:16px 0 6px"><strong>Failed tests</strong></p><ul>')
        for test in failures[:20]:
            message = escape(test.messages[0][:300]) if test.messages else "No message recorded"
            rows.append(
                f'<li style="margin-bottom:6px">{escape(_app(test.suite))} › '
                f"{escape(test.name)}<br>"
                f'<span style="color:#667085;font-size:13px">{message}</span></li>'
            )
        rows.append("</ul>")
        if len(failures) > 20:
            rows.append(f"<p>… {len(failures) - 20} more; see the attached report.</p>")
    rows.append(
        '<p style="color:#667085;font-size:13px">The attached report.html has screenshots '
        "and every test's result.</p></div>"
    )
    return "\n".join(rows)
