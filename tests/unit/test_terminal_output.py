"""Readable test names for the terminal output."""

import pytest

from uiautomation.utils.terminal_output import describe


@pytest.mark.parametrize(
    ("nodeid", "expected"),
    [
        ("tests/integration/test_settings.py::test_wifi_toggle", ("Settings", "wifi toggle")),
        (
            "tests/integration/test_calendar_lifecycle.py::TestEvents::test_add_event[light-xl]",
            ("Calendar lifecycle", "add event (light, xl)"),
        ),
        ("tests/unit/test_wda_setup.py::test_reuse", ("WDA setup", "reuse")),
        ("tests/unit/test_wifi_settings.py::test_join", ("Wi-Fi settings", "join")),
        ("tests/unit/test_xcresult.py::test_flatten", ("Xcresult", "flatten")),
    ],
    ids=["function", "class and parameters", "acronym", "Wi Fi", "plain"],
)
def test_describe_reads_like_plain_words(nodeid: str, expected: tuple[str, str]) -> None:
    assert describe(nodeid) == expected


def test_describe_uses_the_file_path_when_the_node_id_has_none() -> None:
    assert describe("::test_failure", "../../tmp/test_color_probe.py") == ("Color probe", "failure")
