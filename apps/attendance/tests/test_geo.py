
from apps.attendance.domain.geo import haversine_distance


def test_haversine_distance_same_point():
    """Test distance between same point is zero."""
    distance = haversine_distance(6.5244, 3.3792, 6.5244, 3.3792)
    assert distance == 0


def test_haversine_distance_lagos_abuja():
    """Test distance between Lagos and Abuja (approximately 526 km)."""
    # Lagos coordinates
    lat1, lon1 = 6.5244, 3.3792
    # Abuja coordinates
    lat2, lon2 = 9.0765, 7.3986

    distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Distance should be approximately 526 km with some tolerance
    assert 520000 < distance < 530000


def test_haversine_distance_small_distance():
    """Test distance for a small distance (within a campus)."""
    # Two points within a campus
    lat1, lon1 = 6.5244, 3.3792
    lat2, lon2 = 6.5254, 3.3802

    distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Distance should be small (approximately 150 meters)
    assert 100 < distance < 200


def test_haversine_distance_negative_coordinates():
    """Test distance with negative coordinates (southern hemisphere)."""
    lat1, lon1 = -6.5244, -3.3792
    lat2, lon2 = -6.5254, -3.3802

    distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Distance should still be positive
    assert distance > 0
    assert 100 < distance < 200
