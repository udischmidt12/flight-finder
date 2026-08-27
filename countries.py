"""Country -> airport(s) table, plus flag/region/lookup helpers.

Each country has a "region" used for two things:
- Grouping "Flying to" destination tiles into sections (Asia / South America).
- Grouping the "Flying from" origin picker: Israel and United States each
  get their own dedicated chip, everything else is grouped under its
  region (Asia / South America, which here includes Central America).

Most countries list a single representative airport; a few list several
major international airports so the origin picker can choose the nearest
one via GPS, or ask which one if GPS isn't available.
"""

COUNTRY_DATA = {
    # --- Home / dedicated origin buckets ---
    "Israel": {"iso2": "IL", "region": "israel", "currency": "ILS", "airports": [
        {"code": "TLV", "name": "Tel Aviv", "lat": 32.0055, "lon": 34.8854},
    ]},
    "United States": {"iso2": "US", "region": "united_states", "currency": "USD", "airports": [
        {"code": "JFK", "name": "New York", "lat": 40.6413, "lon": -73.7781},
        {"code": "LAX", "name": "Los Angeles", "lat": 33.9416, "lon": -118.4085},
        {"code": "ORD", "name": "Chicago", "lat": 41.9742, "lon": -87.9073},
        {"code": "MIA", "name": "Miami", "lat": 25.7959, "lon": -80.2870},
        {"code": "SFO", "name": "San Francisco", "lat": 37.6213, "lon": -122.3790},
    ]},

    # --- Asia ---
    "Thailand": {"iso2": "TH", "region": "asia", "currency": "THB", "airports": [
        {"code": "BKK", "name": "Bangkok Suvarnabhumi", "lat": 13.6900, "lon": 100.7501},
    ]},
    "Cambodia": {"iso2": "KH", "region": "asia", "currency": "KHR", "airports": [
        {"code": "PNH", "name": "Phnom Penh", "lat": 11.5466, "lon": 104.8441},
    ]},
    "China": {"iso2": "CN", "region": "asia", "currency": "CNY", "airports": [
        {"code": "PEK", "name": "Beijing Capital", "lat": 40.0799, "lon": 116.6031},
        {"code": "PVG", "name": "Shanghai Pudong", "lat": 31.1443, "lon": 121.8083},
        {"code": "CAN", "name": "Guangzhou Baiyun", "lat": 23.3959, "lon": 113.3080},
    ]},
    "Japan": {"iso2": "JP", "region": "asia", "currency": "JPY", "airports": [
        {"code": "HND", "name": "Tokyo Haneda", "lat": 35.5494, "lon": 139.7798},
    ]},
    "Laos": {"iso2": "LA", "region": "asia", "currency": "LAK", "airports": [
        {"code": "VTE", "name": "Vientiane", "lat": 17.9883, "lon": 102.5633},
    ]},
    "Philippines": {"iso2": "PH", "region": "asia", "currency": "PHP", "airports": [
        {"code": "MNL", "name": "Manila", "lat": 14.5086, "lon": 121.0198},
    ]},
    "Indonesia": {"iso2": "ID", "region": "asia", "currency": "IDR", "airports": [
        {"code": "CGK", "name": "Jakarta", "lat": -6.1256, "lon": 106.6559},
    ]},
    "Taiwan": {"iso2": "TW", "region": "asia", "currency": "TWD", "airports": [
        {"code": "TPE", "name": "Taipei Taoyuan", "lat": 25.0797, "lon": 121.2342},
    ]},
    "Mongolia": {"iso2": "MN", "region": "asia", "currency": "MNT", "airports": [
        {"code": "ULN", "name": "Ulaanbaatar", "lat": 47.6432, "lon": 106.8221},
    ]},
    "Vietnam": {"iso2": "VN", "region": "asia", "currency": "VND", "airports": [
        {"code": "SGN", "name": "Ho Chi Minh City", "lat": 10.8188, "lon": 106.6520},
    ]},
    "South Korea": {"iso2": "KR", "region": "asia", "currency": "KRW", "airports": [
        {"code": "ICN", "name": "Seoul Incheon", "lat": 37.4602, "lon": 126.4407},
    ]},
    "India": {"iso2": "IN", "region": "asia", "currency": "INR", "airports": [
        {"code": "DEL", "name": "Delhi", "lat": 28.5562, "lon": 77.1000},
        {"code": "BOM", "name": "Mumbai", "lat": 19.0896, "lon": 72.8656},
    ]},

    # --- South America (incl. Central America) ---
    "Brazil": {"iso2": "BR", "region": "south_america", "currency": "BRL", "airports": [
        {"code": "GRU", "name": "Sao Paulo Guarulhos", "lat": -23.4356, "lon": -46.4731},
        {"code": "GIG", "name": "Rio de Janeiro Galeao", "lat": -22.8100, "lon": -43.2506},
    ]},
    "Argentina": {"iso2": "AR", "region": "south_america", "currency": "ARS", "airports": [
        {"code": "EZE", "name": "Buenos Aires Ezeiza", "lat": -34.8222, "lon": -58.5358},
    ]},
    "Bolivia": {"iso2": "BO", "region": "south_america", "currency": "BOB", "airports": [
        {"code": "VVI", "name": "Santa Cruz", "lat": -17.6448, "lon": -63.1354},
    ]},
    "Chile": {"iso2": "CL", "region": "south_america", "currency": "CLP", "airports": [
        {"code": "SCL", "name": "Santiago", "lat": -33.3930, "lon": -70.7858},
    ]},
    "Colombia": {"iso2": "CO", "region": "south_america", "currency": "COP", "airports": [
        {"code": "BOG", "name": "Bogota", "lat": 4.7016, "lon": -74.1469},
    ]},
    "Ecuador": {"iso2": "EC", "region": "south_america", "currency": "USD", "airports": [
        {"code": "UIO", "name": "Quito", "lat": -0.1292, "lon": -78.3575},
    ]},
    "Guyana": {"iso2": "GY", "region": "south_america", "currency": "GYD", "airports": [
        {"code": "GEO", "name": "Georgetown", "lat": 6.4985, "lon": -58.2541},
    ]},
    "Paraguay": {"iso2": "PY", "region": "south_america", "currency": "PYG", "airports": [
        {"code": "ASU", "name": "Asuncion", "lat": -25.2400, "lon": -57.5200},
    ]},
    "Peru": {"iso2": "PE", "region": "south_america", "currency": "PEN", "airports": [
        {"code": "LIM", "name": "Lima", "lat": -12.0219, "lon": -77.1143},
    ]},
    "Suriname": {"iso2": "SR", "region": "south_america", "currency": "SRD", "airports": [
        {"code": "PBM", "name": "Paramaribo", "lat": 5.4528, "lon": -55.1878},
    ]},
    "Uruguay": {"iso2": "UY", "region": "south_america", "currency": "UYU", "airports": [
        {"code": "MVD", "name": "Montevideo", "lat": -34.8384, "lon": -56.0308},
    ]},
    "Venezuela": {"iso2": "VE", "region": "south_america", "currency": "VES", "airports": [
        {"code": "CCS", "name": "Caracas", "lat": 10.6031, "lon": -66.9906},
    ]},
    "Belize": {"iso2": "BZ", "region": "south_america", "currency": "BZD", "airports": [
        {"code": "BZE", "name": "Belize City", "lat": 17.5391, "lon": -88.3082},
    ]},
    "Costa Rica": {"iso2": "CR", "region": "south_america", "currency": "CRC", "airports": [
        {"code": "SJO", "name": "San Jose", "lat": 9.9939, "lon": -84.2088},
    ]},
    "El Salvador": {"iso2": "SV", "region": "south_america", "currency": "USD", "airports": [
        {"code": "SAL", "name": "San Salvador", "lat": 13.4409, "lon": -89.0557},
    ]},
    "Guatemala": {"iso2": "GT", "region": "south_america", "currency": "GTQ", "airports": [
        {"code": "GUA", "name": "Guatemala City", "lat": 14.5833, "lon": -90.5275},
    ]},
    "Honduras": {"iso2": "HN", "region": "south_america", "currency": "HNL", "airports": [
        {"code": "TGU", "name": "Tegucigalpa", "lat": 14.0608, "lon": -87.2172},
    ]},
    "Nicaragua": {"iso2": "NI", "region": "south_america", "currency": "NIO", "airports": [
        {"code": "MGA", "name": "Managua", "lat": 12.1415, "lon": -86.1682},
    ]},
    "Panama": {"iso2": "PA", "region": "south_america", "currency": "USD", "airports": [
        {"code": "PTY", "name": "Panama City", "lat": 9.0714, "lon": -79.3835},
    ]},
}

REGION_LABELS = {
    "israel": "Israel",
    "united_states": "United States",
    "asia": "Asia",
    "south_america": "South America",
}


def flag_emoji(iso2):
    """Convert a 2-letter ISO country code to its flag emoji."""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())


def all_countries():
    """Every known country, with flag + region + airport list + a primary
    airport (first in the list) for places that just need one code."""
    result = {}
    for name, info in COUNTRY_DATA.items():
        result[name] = {
            "iso2": info["iso2"],
            "region": info["region"],
            "currency": info["currency"],
            "flag": flag_emoji(info["iso2"]),
            "airports": info["airports"],
            "airport": info["airports"][0]["code"],
        }
    return result


def origin_regions():
    """{"asia": [country names...], "south_america": [...]} -- the two
    browsable regions in the origin picker (Israel/United States are their
    own dedicated buckets, not part of this)."""
    regions = {"asia": [], "south_america": []}
    for name, info in COUNTRY_DATA.items():
        if info["region"] in regions:
            regions[info["region"]].append(name)
    return regions


def candidate_countries(visited_countries=None, wishlist_countries=None):
    """Destination countries to search flights for.

    If wishlist_countries is given, use exactly that list. Otherwise fall
    back to "every known country minus visited_countries".
    """
    countries = all_countries()

    if wishlist_countries:
        result = {}
        unknown = []
        for name in wishlist_countries:
            if name in countries:
                result[name] = countries[name]
            else:
                unknown.append(name)
        return result, unknown

    visited = set(visited_countries or [])
    result = {name: info for name, info in countries.items() if name not in visited}
    return result, []
