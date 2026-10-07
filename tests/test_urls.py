from django.urls import resolve, reverse


def test_named_routes_with_namespaces_resolve_to_expected_paths():
    assert reverse("homepage:index") == "/"
    assert reverse("venues:list") == "/venues/"
    assert reverse("venues:detail", args=[3]) == "/venues/3/"
    assert reverse("bookings:list") == "/bookings/"
    assert reverse("bookings:detail", args=[2]) == "/bookings/2/"


def test_paths_resolve_to_namespaced_routes():
    assert resolve("/").view_name == "homepage:index"
    assert resolve("/venues/").view_name == "venues:list"
    assert resolve("/venues/1/").view_name == "venues:detail"
    assert resolve("/bookings/").view_name == "bookings:list"
    assert resolve("/bookings/1/").view_name == "bookings:detail"
