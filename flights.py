"""SerpApi Google Flights lookups."""

import os
import requests

SERPAPI_URL = "https://serpapi.com/search"


class FlightApiError(Exception):
    pass


def _parse_flight(f):
    """Turn one SerpApi google_flights option into our flat dict shape."""
    legs = f.get("flights", [{}])
    first_leg = legs[0] if legs else {}
    last_leg = legs[-1] if legs else {}

    layovers = [
        {
            "airport": l.get("name", "unknown"),
            "code": l.get("id", "?"),
            "duration_minutes": l.get("duration", 0),
        }
        for l in f.get("layovers", [])
    ]

    return {
        "price": f.get("price"),
        "airline": first_leg.get("airline", "unknown"),
        "departure": first_leg.get("departure_airport", {}).get("time", ""),
        "arrival": last_leg.get("arrival_airport", {}).get("time", ""),
        "is_direct": len(legs) <= 1,
        "layovers": layovers,
        "total_duration_minutes": f.get("total_duration"),
    }


def search_flights(origin, destination, date, direct_only=False, limit=5):
    """Return up to `limit` one-way flights, cheapest first, as a list of
    dicts (see _parse_flight). One SerpApi call -- the response already
    carries many options, we just rank and keep the top few. Returns []
    if no route/results. Raises FlightApiError on missing key / request
    failure.
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise FlightApiError("SERPAPI_KEY environment variable is not set")

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": date,
        "type": "2",  # one-way
        "currency": "USD",
        "api_key": api_key,
    }
    if direct_only:
        params["stops"] = 1  # SerpApi: 1 = nonstop only

    try:
        resp = requests.get(SERPAPI_URL, params=params, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FlightApiError(f"request failed: {e}")

    data = resp.json()

    if "error" in data:
        return []

    flights = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    priced = [f for f in flights if f.get("price") is not None]
    if not priced:
        return []

    priced.sort(key=lambda f: f["price"])
    return [_parse_flight(f) for f in priced[:limit]]


def search_cheapest_flight(origin, destination, date, direct_only=False):
    """Back-compat: the single cheapest flight dict, or None."""
    found = search_flights(origin, destination, date, direct_only=direct_only, limit=1)
    return found[0] if found else None
