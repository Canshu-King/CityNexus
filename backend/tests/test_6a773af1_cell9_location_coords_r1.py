"""Cell nine: place coordinates are validated within valid ranges.

When a Place or LocationObservation carries a latitude outside [-90, 90] or longitude outside
[-180, 180], the schema refuses it with a validation error. This is the next layer out from cell eight's
route-point count check — completeness → correctness.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from pydantic import ValidationError


def test_latitude_below_negative_ninety_refused():
    """Latitudes below -90 are invalid."""
    from app.schemas import GeoPoint
    with pytest.raises(ValidationError):
        GeoPoint(latitude=-91.0, longitude=120.0)


def test_latitude_above_ninety_refused():
    """Latitudes above 90 are invalid."""
    from app.schemas import GeoPoint
    with pytest.raises(ValidationError):
        GeoPoint(latitude=91.0, longitude=120.0)


def test_longitude_below_negative_one_hundred_eighty_refused():
    """Longitudes below -180 are invalid."""
    from app.schemas import GeoPoint
    with pytest.raises(ValidationError):
        GeoPoint(latitude=30.0, longitude=-181.0)


def test_longitude_above_one_hundred_eighty_refused():
    """Longitudes above 180 are invalid."""
    from app.schemas import GeoPoint
    with pytest.raises(ValidationError):
        GeoPoint(latitude=30.0, longitude=181.0)


def test_latitude_boundary_negative_ninety_accepted():
    """Latitude exactly -90 is accepted (South Pole)."""
    from app.schemas import GeoPoint
    gp = GeoPoint(latitude=-90.0, longitude=0.0)
    assert gp.latitude == -90.0


def test_latitude_boundary_ninety_accepted():
    """Latitude exactly 90 is accepted (North Pole)."""
    from app.schemas import GeoPoint
    gp = GeoPoint(latitude=90.0, longitude=0.0)
    assert gp.latitude == 90.0


def test_longitude_boundary_negative_one_hundred_eighty_accepted():
    """Longitude exactly -180 is accepted (ID line)."""
    from app.schemas import GeoPoint
    gp = GeoPoint(latitude=0.0, longitude=-180.0)
    assert gp.longitude == -180.0


def test_longitude_boundary_one_hundred_eighty_accepted():
    """Longitude exactly 180 is accepted (ID line)."""
    from app.schemas import GeoPoint
    gp = GeoPoint(latitude=0.0, longitude=180.0)
    assert gp.longitude == 180.0
