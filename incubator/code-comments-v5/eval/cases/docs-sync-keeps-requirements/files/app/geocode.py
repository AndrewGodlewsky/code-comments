"""Calls to the Mapline geocoding API."""

from app.config import GEOCODE_REQUESTS_PER_MINUTE, GEOCODE_TIMEOUT_SECONDS

URL = "https://api.mapline.example/v2/geocode"

# Seconds to wait between two lookups so the portal stays at its configured rate.
MIN_INTERVAL = 60 / GEOCODE_REQUESTS_PER_MINUTE


def lookup(session, address):
    """Return Mapline's JSON answer for one address."""
    response = session.get(URL, params={"q": address}, timeout=GEOCODE_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
