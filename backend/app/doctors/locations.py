"""
Location handling for doctor recommendations.

There is no GPS permission prompt and no maps API key involved. The
user picks their area from a dropdown, every doctor is seeded with the
coordinates of the area they practise in, and distance is a haversine
calculation between those two points. That is accurate to roughly the
size of a neighbourhood, which is all "is this doctor near me?"
actually needs, and it keeps the feature working offline.

If you later want real GPS, the only change needed is to pass
`latitude`/`longitude` straight into `distance_km()` instead of looking
the area up here - the recommender already works in coordinates.
"""

from math import asin, cos, radians, sin, sqrt

CITY = "Hyderabad"

# Approximate centre point of each area. Good enough for ranking by
# proximity; not meant for navigation.
AREAS: dict[str, tuple[float, float]] = {
    "Ameerpet": (17.4375, 78.4483),
    "Attapur": (17.3616, 78.4237),
    "Banjara Hills": (17.4126, 78.4392),
    "Begumpet": (17.4443, 78.4661),
    "Chanda Nagar": (17.4970, 78.3236),
    "Dilsukhnagar": (17.3687, 78.5247),
    "Gachibowli": (17.4401, 78.3489),
    "Himayatnagar": (17.4009, 78.4863),
    "Jubilee Hills": (17.4319, 78.4073),
    "Kompally": (17.5401, 78.4869),
    "Kondapur": (17.4615, 78.3628),
    "Kukatpally": (17.4948, 78.3996),
    "LB Nagar": (17.3457, 78.5522),
    "Madhapur": (17.4483, 78.3915),
    "Malakpet": (17.3730, 78.5046),
    "Manikonda": (17.4021, 78.3810),
    "Mehdipatnam": (17.3956, 78.4392),
    "Miyapur": (17.4967, 78.3583),
    "Nizampet": (17.5099, 78.3878),
    "Old City": (17.3616, 78.4747),
    "Panjagutta": (17.4256, 78.4522),
    "Sainikpuri": (17.4998, 78.5527),
    "Secunderabad": (17.4399, 78.4983),
    "Somajiguda": (17.4239, 78.4595),
    "Tarnaka": (17.4260, 78.5290),
    "Uppal": (17.4058, 78.5590),
}

EARTH_RADIUS_KM = 6371.0


def area_names() -> list[str]:
    return sorted(AREAS.keys())


def coordinates_for(area: str | None) -> tuple[float, float] | None:
    """Coordinates for an area name, matched case-insensitively."""

    if not area:
        return None

    target = area.strip().lower()

    for name, point in AREAS.items():
        if name.lower() == target:
            return point

    return None


def distance_km(
    origin: tuple[float, float] | None,
    destination: tuple[float, float] | None,
) -> float | None:
    """Great-circle distance between two lat/lng pairs, in kilometres."""

    if not origin or not destination:
        return None

    lat1, lon1 = origin
    lat2, lon2 = destination

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)

    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )

    return round(2 * EARTH_RADIUS_KM * asin(sqrt(a)), 1)


def travel_hint(distance: float | None) -> str:
    """Plain-language version of a distance, for the UI."""

    if distance is None:
        return "Distance unavailable"

    if distance < 1:
        return "Walking distance"

    if distance < 4:
        return f"{distance} km away · about 15 min by car"

    if distance < 9:
        return f"{distance} km away · about 25 min by car"

    if distance < 15:
        return f"{distance} km away · about 35 min by car"

    if distance < 25:
        return f"{distance} km away · about 50 min by car"

    return f"{distance} km away · across the city"
