"""Maps P0 journeys on a dedicated simulator; navigation never starts."""

import pytest

from uiautomation.pages.maps import MapsPage

pytestmark = pytest.mark.maps
ORIGIN = (37.8029, -122.4484)
DESTINATION = (37.8199, -122.4783)


@pytest.mark.smoke
@pytest.mark.parametrize("maps_home", ["deny", "allow"], indirect=True)
def test_launch_and_search_with_location_permission(maps_home: MapsPage) -> None:
    """Both location decisions permit manual place search and dismissal."""
    maps_home.wait_until_ready()
    maps_home.search_place("Golden Gate Bridge San Francisco", "Golden Gate Bridge")
    maps_home.close_to_home()


@pytest.mark.parametrize("query", ["Golden Gate Bridge", "1 Ferry Building San Francisco"])
def test_edit_clear_and_cancel_search(maps_home: MapsPage, query: str) -> None:
    """Search input can be replaced, cleared, and canceled without a result selection."""
    maps_home.edit_search(query)
    assert maps_home.query() == query
    maps_home.edit_search("Palace of Fine Arts")
    assert maps_home.query() == "Palace of Fine Arts"
    maps_home.edit_search("")
    assert maps_home.query() == ""
    maps_home.close_to_home()


@pytest.mark.journey
def test_place_directions_round_trip(maps_home: MapsPage) -> None:
    """Place identity and Directions entry remain usable with location denied."""
    maps_home.search_place("Golden Gate Bridge San Francisco", "Golden Gate Bridge")
    maps_home.open_directions()
    assert maps_home.waypoints() == ["Choose an origin", "Golden Gate Bridge"]
    maps_home.close_to_home()


@pytest.mark.journey
def test_route_preview_and_travel_modes(maps_home: MapsPage) -> None:
    """Fixed endpoints produce driving and walking previews with valid route metrics."""
    maps_home.preview_route(ORIGIN, DESTINATION)
    endpoints = maps_home.waypoints()
    assert len(endpoints) == 2, endpoints
    assert endpoints[0] == "Palace of Fine Arts", endpoints
    assert endpoints[1].startswith("Golden Gate Bridge"), endpoints
    driving = maps_home.select_mode("drive")
    walking = maps_home.select_mode("walk")
    assert walking != driving, "Walking still exposes the driving summary"
    maps_home.select_mode("drive")
    maps_home.close_to_home()


@pytest.mark.journey
def test_search_repeatability(maps_home: MapsPage) -> None:
    """Two complete search/dismiss cycles leave no blocking route or place card."""
    for _ in range(2):
        maps_home.search_place("Golden Gate Bridge San Francisco", "Golden Gate Bridge")
        maps_home.close_to_home()
