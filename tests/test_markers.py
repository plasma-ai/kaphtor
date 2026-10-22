"""Every test carries exactly one of the markers `pyproject.toml` registers: `unit`, `data` or `maintainer`.

Both checks read the tests collected in the same run, so they cover the whole suite only when the whole suite runs.
"""
MARKERS = ("unit", "data", "maintainer")


def test_every_test_has_exactly_one_marker(request):
    wrong = [item.nodeid for item in request.session.items
             if sum(item.get_closest_marker(name) is not None for name in MARKERS) != 1]
    assert not wrong, wrong


def test_a_test_that_skips_without_data_is_not_a_unit_test(request):
    wrong = [item.nodeid for item in request.session.items
             if item.get_closest_marker("unit")
             and any("in this checkout" in mark.kwargs.get("reason", "") for mark in item.iter_markers("skipif"))]
    assert not wrong, wrong
