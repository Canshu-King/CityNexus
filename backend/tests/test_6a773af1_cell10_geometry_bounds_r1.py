"""Cell ten: a provider route geometry with any out-of-WGS84 vertex is not trusted.

`_route_feature` already refused fewer than two points (cell eight). This arm adds the next layer
out: the points themselves must lie within the same bounds the schema puts on a single place
(`backend/app/schemas.py`, `GeoPoint`). Vertices are [longitude, latitude] in GeoJSON, so the check
reads index 0 as longitude and index 1 as latitude. Positive and negative arms are tested together:
an in-range two-point line still returns a Feature (the guard does not blanket-refuse), while a
single bad vertex returns None.
"""
from app.main import _route_feature


def _call(coords):
    return _route_feature(
        coords,
        provider="test",
        provider_backed=True,
        fallback_reason=None,
        plan_version_id="pv-cell10",
    )


def test_in_range_two_point_line_still_returns_feature():
    coords = [[117.19, 39.13], [116.40, 39.90]]
    result = _call(coords)
    assert result is not None, "a valid geometry must not be refused"
    assert result["geometry"]["coordinates"] == coords


def test_longitudes_at_boundary_are_accepted():
    coords = [[180.0, 90.0], [-180.0, -90.0]]
    result = _call(coords)
    assert result is not None, "exact WGS84 bounds are valid, not out of range"


def test_vertex_with_out_of_range_longitude_refused():
    coords = [[200.0, 39.13], [116.40, 39.90]]
    assert _call(coords) is None


def test_vertex_with_out_of_range_latitude_refused():
    coords = [[117.19, 95.0], [116.40, 39.90]]
    assert _call(coords) is None


def test_vertex_with_negative_out_of_range_longitude_refused():
    coords = [[117.19, 39.13], [-181.0, 39.90]]
    assert _call(coords) is None


def test_non_numeric_vertex_refused():
    coords = [["nowhere", "nowhere"], [116.40, 39.90]]
    assert _call(coords) is None
