"""Skyscanner flight lookups via the RapidAPI "sky-scrapper" listing
(sky-scrapper.p.rapidapi.com).

Returns the same normalized dict as flights.py (plus "source": "skyscanner")
so app.py can compare Google Flights and Skyscanner fares and keep the
cheapest.

The search endpoint doesn't take IATA codes -- it needs a (skyId,
entityId) pair per airport, resolved once via /api/v1/flights/searchAirport
and cached to skyscanner_airports.json.

This is still a scraper behind the scenes, so every function fails soft:
on any error it returns None and the caller falls back to the other
provider. A short circuit breaker stops us hammering (and waiting on) a
dead endpoint on every search.

Setup: subscribe (free "Basic" plan) to the sky-scrapper API on RapidAPI,
then set RAPIDAPI_KEY. If the key is unset the Skyscanner leg is skipped.
"""

import json
import os
import threading
import time

import requests

RAPIDAPI_HOST = "sky-scrapper.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "skyscanner_airports.json")

_cache_lock = threading.Lock()
_breaker_until = 0.0  # skip live calls until this epoch time
_BREAKER_COOLDOWN = 300  # seconds to back off after a failure


class SkyscannerError(Exception):
    pass


def _headers():
    key = os.environ.get("RAPIDAPI_KEY")
    if not key:
        raise SkyscannerError("RAPIDAPI_KEY environment variable is not set")
    return {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": key}


def _trip_breaker():
    global _breaker_until
    _breaker_until = time.time() + _BREAKER_COOLDOWN


def _breaker_open():
    return time.time() < _breaker_until


# --- airport id cache -------------------------------------------------------

def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_cache(cache):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except OSError:
        pass


def resolve_airport(iata):
    """(skyId, entityId) for an IATA code, or None if it can't be resolved.
    Hits /api/v1/flights/searchAirport at most once per airport, then caches."""
    iata = (iata or "").upper()
    if not iata:
        return None

    cached = _load_cache().get(iata)
    if cached and cached.get("skyId") and cached.get("entityId"):
        return cached["skyId"], cached["entityId"]

    if _breaker_open():
        return None

    try:
        resp = requests.get(
            f"{BASE_URL}/api/v1/flights/searchAirport",
            params={"query": iata, "locale": "en-US"},
            headers=_headers(),
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        _trip_breaker()
        return None

    if isinstance(data, dict) and data.get("status") is False:
        _trip_breaker()
        return None

    entries = data.get("data") or []
    if not isinstance(entries, list) or not entries:
        return None

    picked = None
    for e in entries:
        nav = e.get("navigation", {}) or {}
        p = nav.get("relevantFlightParams", {}) or {}
        sky = p.get("skyId") or e.get("skyId")
        ent = p.get("entityId") or e.get("entityId")
        ptype = str(p.get("flightPlaceType") or nav.get("entityType") or "").upper()
        if not sky or not ent:
            continue
        if str(sky).upper() == iata and ptype in ("AIRPORT", ""):
            picked = (str(sky), str(ent))
            break
        if picked is None:
            picked = (str(sky), str(ent))

    if picked is None:
        return None

    with _cache_lock:
        cache = _load_cache()
        cache[iata] = {"skyId": picked[0], "entityId": picked[1]}
        _save_cache(cache)
    return picked


# --- search ---------------------------------------------------------------

def _parse_itinerary(it):
    price_obj = it.get("price") or {}
    price = price_obj.get("raw") if isinstance(price_obj, dict) else price_obj
    if not isinstance(price, (int, float)):
        price = None

    legs = it.get("legs") or []
    leg = legs[0] if legs else {}

    carriers = ((leg.get("carriers") or {}).get("marketing")) or []
    airline = carriers[0].get("name") if carriers and isinstance(carriers[0], dict) else "unknown"

    stop_count = leg.get("stopCount", 0) or 0
    segments = leg.get("segments") or []
    layovers = []
    for seg in segments[1:]:
        o = seg.get("origin", {}) or {}
        layovers.append({
            "airport": o.get("name", "unknown"),
            "code": o.get("displayCode") or o.get("id", "?"),
            "duration_minutes": 0,
        })

    return {
        "price": round(price) if isinstance(price, (int, float)) else None,
        "airline": airline or "unknown",
        "departure": str(leg.get("departure") or "").replace("T", " ")[:16],
        "arrival": str(leg.get("arrival") or "").replace("T", " ")[:16],
        "is_direct": stop_count == 0,
        "layovers": layovers,
        "total_duration_minutes": leg.get("durationInMinutes"),
        "source": "skyscanner",
        # Skyscanner's own itinerary id -- used verbatim as the /config/
        # path segment in the deep link to this flight's vendor list.
        "itinerary_id": it.get("id"),
    }


def search_cheapest_flight(origin, destination, date, direct_only=False):
    """Cheapest one-way Skyscanner fare as the dict flights.py returns
    (plus "source": "skyscanner"), or None if unavailable.

    Note: sky-scrapper's first response can be data.context.status ==
    "incomplete" (results still streaming). We don't poll -- the partial
    set is enough for a "cheapest right now" glance.
    """
    if _breaker_open():
        return None

    o = resolve_airport(origin)
    d = resolve_airport(destination)
    if not o or not d:
        return None

    params = {
        "originSkyId": o[0],
        "originEntityId": o[1],
        "destinationSkyId": d[0],
        "destinationEntityId": d[1],
        "date": date,
        "cabinClass": "economy",
        "adults": "1",
        "sortBy": "price_high",  # any order works; we take the min below
        "currency": "USD",
        "market": "en-US",
        "countryCode": "US",
    }

    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/flights/searchFlights",
            params=params, headers=_headers(), timeout=18,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        _trip_breaker()
        return None

    if isinstance(data, dict) and data.get("status") is False:
        _trip_breaker()
        return None

    payload = data.get("data") or data
    itineraries = payload.get("itineraries") or payload.get("results") or []
    if not isinstance(itineraries, list) or not itineraries:
        return None

    parsed = [p for p in (_parse_itinerary(it) for it in itineraries)
              if p["price"] is not None]
    if direct_only:
        parsed = [p for p in parsed if p["is_direct"]] or parsed
    if not parsed:
        return None

    return min(parsed, key=lambda p: p["price"])
