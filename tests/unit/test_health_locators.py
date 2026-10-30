"""Health locators name real locators and report every miss at once."""

import importlib
import pkgutil
from unittest.mock import MagicMock

import pytest

import uiautomation.pages
from uiautomation.pages.base_page import BasePage
from uiautomation.utils.local_runner import SUITES


def _page_classes() -> list[type[BasePage]]:
    for module in pkgutil.walk_packages(uiautomation.pages.__path__, "uiautomation.pages."):
        importlib.import_module(module.name)
    found: list[type[BasePage]] = []
    pending = list(BasePage.__subclasses__())
    while pending:
        page = pending.pop()
        found.append(page)
        pending.extend(page.__subclasses__())
    return [page for page in found if "HEALTH_LOCATORS" in vars(page)]


@pytest.mark.parametrize("page", _page_classes(), ids=lambda page: page.__name__)
def test_health_locators_name_locator_attributes(page: type[BasePage]) -> None:
    assert page.HEALTH_LOCATORS, "Declare at least one locator or drop the attribute"
    for name in page.HEALTH_LOCATORS:
        locator = getattr(page, name)
        assert isinstance(locator, tuple) and len(locator) == 2, name
        assert all(isinstance(part, str) and part for part in locator), name


def test_main_screens_declare_health_locators() -> None:
    names = {page.__name__ for page in _page_classes()}
    assert {
        "SettingsHomePage",
        "CalendarHomePage",
        "NewEventPage",
        "MessagesHomePage",
        "ComposeMessagePage",
        "ContactsPage",
        "MapsPage",
    } <= names


def test_missing_locators_are_all_reported_with_their_names() -> None:
    class Page(BasePage):
        PRESENT = (BasePage.By.ACCESSIBILITY_ID, "present")
        GONE = (BasePage.By.ACCESSIBILITY_ID, "gone")
        ALSO_GONE = (BasePage.By.IOS_PREDICATE, "name == 'also-gone'")
        HEALTH_LOCATORS = ("PRESENT", "GONE", "ALSO_GONE")

    driver = MagicMock()
    driver.find_elements.side_effect = lambda by, value: [MagicMock()] if value == "present" else []
    assert Page(driver).missing_health_locators() == [
        "Page.GONE (accessibility id: gone)",
        "Page.ALSO_GONE (-ios predicate string: name == 'also-gone')",
    ]


def test_locators_suite_runs_only_opt_in_health_checks() -> None:
    assert SUITES["locators"] == [
        "tests/integration",
        "--run-integration",
        "--run-diagnostics",
        "-m",
        "locators",
    ]
