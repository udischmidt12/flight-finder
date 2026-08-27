"""SerpApi Google Flights lookups."""

import os
import requests

SERPAPI_URL = "https://serpapi.com/search"


class FlightApiError(Exception):
    pass


def search_cheapest_flight(origin, destination, date, direct_only=False):
    """Return the cheapest one-way flight found as a dict:
    {price, airline, departure, is_direct, layovers, total_duration_minutes}
    or None if no route/results. Raises FlightApiError on missing key or
    request failure.
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
        return None

    flights = data.get("best_flights") or data.get("other_flights") or []
    if not flights:
        return None

    cheapest = min(flights, key=lambda f: f.get("price", float("inf")))
    legs = cheapest.get("flights", [{}])
    first_leg = legs[0] if legs else {}
    last_leg = legs[-1] if legs else {}

    layovers = [
        {
            "airport": l.get("name", "unknown"),
            "code": l.get("id", "?"),
            "duration_minutes": l.get("duration", 0),
        }
        for l in cheapest.get("layovers", [])
    ]

    return {
        "price": cheapest.get("price"),
        "airline": first_leg.get("airline", "unknown"),
        "departure": first_leg.get("departure_airport", {}).get("time", ""),
        "arrival": last_leg.get("arrival_airport", {}).get("time", ""),
        "is_direct": len(legs) <= 1,
        "layovers": layovers,
        "total_duration_minutes": cheapest.get("total_duration"),
        "booking_token": cheapest.get("booking_token"),
    }


def get_booking_url(booking_token, origin, destination, date):
    """Exchange a booking_token (from search_cheapest_flight) for the real
    booking link SerpApi found for that specific flight.

    Google's booking redirect is a POST, not a plain link -- it needs both
    the "url" and the accompanying "post_data" submitted together, or it
    lands on a dead page. SerpApi typically lists several sellers for the
    same flight (the airline directly, plus one or more booking agents/OTAs)
    at slightly different prices, so this picks whichever seller is
    actually cheapest rather than just the first one listed.

    Returns {"url", "post_data", "book_with", "price"} or None if no
    booking option is found. Raises FlightApiError on missing key or
    request failure.
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise FlightApiError("SERPAPI_KEY environment variable is not set")

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": date,
        "type": "2",
        "currency": "USD",
        "booking_token": booking_token,
        "api_key": api_key,
    }

    try:
        resp = requests.get(SERPAPI_URL, params=params, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FlightApiError(f"request failed: {e}")

    data = resp.json()
    if "error" in data:
        return None

    cheapest = None
    for option in data.get("booking_options", []):
        for key in ("together", "departing", "returning"):
            leg = option.get(key)
            if not leg:
                continue
            req = leg.get("booking_request", {})
            url = req.get("url")
            if not url:
                continue

            price = leg.get("price")
            candidate = {
                "url": url,
                "post_data": req.get("post_data"),
                "book_with": leg.get("book_with", "unknown"),
                "price": price,
            }

            if cheapest is None:
                cheapest = candidate
            elif price is not None and (cheapest["price"] is None or price < cheapest["price"]):
                cheapest = candidate

    return cheapest
