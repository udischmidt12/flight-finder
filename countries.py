"""Country -> airport(s) table, plus flag/region/lookup helpers.

Each country has a "region" used for two things:
- Grouping "Flying to" destination tiles into sections (Asia / South America).
- Grouping the "Flying from" origin picker: Israel and United States each
  get their own dedicated chip, everything else is grouped under its
  region (Asia / South America, which here includes Central America).

Most countries list a single representative airport; many list several
major international / big-tourist airports so the origin picker can pick
the nearest via GPS (or ask), and the "Flying to" picker can offer a
choice of where to land. Each airport carries a short `city` label for
compact display and a longer `name` for the pickers.
"""

COUNTRY_DATA = {
    # --- Home / dedicated origin buckets ---
    "Israel": {"iso2": "IL", "region": "israel", "currency": "ILS", "airports": [
        {"code": "TLV", "city": "Tel Aviv", "name": "Tel Aviv Ben Gurion", "lat": 32.0055, "lon": 34.8854},
    ]},
    "United States": {"iso2": "US", "region": "united_states", "currency": "USD", "airports": [
        {"code": "JFK", "city": "New York", "name": "New York JFK", "lat": 40.6413, "lon": -73.7781},
        {"code": "LAX", "city": "Los Angeles", "name": "Los Angeles", "lat": 33.9416, "lon": -118.4085},
        {"code": "ORD", "city": "Chicago", "name": "Chicago O'Hare", "lat": 41.9742, "lon": -87.9073},
        {"code": "MIA", "city": "Miami", "name": "Miami", "lat": 25.7959, "lon": -80.2870},
        {"code": "SFO", "city": "San Francisco", "name": "San Francisco", "lat": 37.6213, "lon": -122.3790},
    ]},

    # --- Asia ---
    "Thailand": {"iso2": "TH", "region": "asia", "currency": "THB", "airports": [
        {"code": "BKK", "city": "Bangkok", "name": "Bangkok Suvarnabhumi", "lat": 13.6900, "lon": 100.7501},
        {"code": "HKT", "city": "Phuket", "name": "Phuket", "lat": 8.1132, "lon": 98.3169},
        {"code": "CNX", "city": "Chiang Mai", "name": "Chiang Mai", "lat": 18.7669, "lon": 98.9626},
    ]},
    "Cambodia": {"iso2": "KH", "region": "asia", "currency": "KHR", "airports": [
        {"code": "PNH", "city": "Phnom Penh", "name": "Phnom Penh", "lat": 11.5466, "lon": 104.8441},
        {"code": "SAI", "city": "Siem Reap", "name": "Siem Reap-Angkor", "lat": 13.3113, "lon": 103.8145},
    ]},
    "China": {"iso2": "CN", "region": "asia", "currency": "CNY", "airports": [
        {"code": "PEK", "city": "Beijing", "name": "Beijing Capital", "lat": 40.0799, "lon": 116.6031},
        {"code": "PVG", "city": "Shanghai", "name": "Shanghai Pudong", "lat": 31.1443, "lon": 121.8083},
        {"code": "CAN", "city": "Guangzhou", "name": "Guangzhou Baiyun", "lat": 23.3959, "lon": 113.3080},
        {"code": "CTU", "city": "Chengdu", "name": "Chengdu Shuangliu", "lat": 30.5785, "lon": 103.9471},
    ]},
    "Japan": {"iso2": "JP", "region": "asia", "currency": "JPY", "airports": [
        {"code": "HND", "city": "Tokyo", "name": "Tokyo Haneda", "lat": 35.5494, "lon": 139.7798},
        {"code": "NRT", "city": "Tokyo", "name": "Tokyo Narita", "lat": 35.7719, "lon": 140.3928},
        {"code": "KIX", "city": "Osaka", "name": "Osaka Kansai", "lat": 34.4347, "lon": 135.2441},
    ]},
    "Laos": {"iso2": "LA", "region": "asia", "currency": "LAK", "airports": [
        {"code": "VTE", "city": "Vientiane", "name": "Vientiane Wattay", "lat": 17.9883, "lon": 102.5633},
        {"code": "LPQ", "city": "Luang Prabang", "name": "Luang Prabang", "lat": 19.8973, "lon": 102.1607},
    ]},
    "Philippines": {"iso2": "PH", "region": "asia", "currency": "PHP", "airports": [
        {"code": "MNL", "city": "Manila", "name": "Manila", "lat": 14.5086, "lon": 121.0198},
        {"code": "CEB", "city": "Cebu", "name": "Cebu Mactan", "lat": 10.3075, "lon": 123.9790},
    ]},
    "Indonesia": {"iso2": "ID", "region": "asia", "currency": "IDR", "airports": [
        {"code": "CGK", "city": "Jakarta", "name": "Jakarta Soekarno-Hatta", "lat": -6.1256, "lon": 106.6559},
        {"code": "DPS", "city": "Bali", "name": "Bali Denpasar", "lat": -8.7482, "lon": 115.1675},
        {"code": "SUB", "city": "Surabaya", "name": "Surabaya Juanda", "lat": -7.3798, "lon": 112.7869},
    ]},
    "Taiwan": {"iso2": "TW", "region": "asia", "currency": "TWD", "airports": [
        {"code": "TPE", "city": "Taipei", "name": "Taipei Taoyuan", "lat": 25.0797, "lon": 121.2342},
        {"code": "KHH", "city": "Kaohsiung", "name": "Kaohsiung", "lat": 22.5771, "lon": 120.3499},
    ]},
    "Mongolia": {"iso2": "MN", "region": "asia", "currency": "MNT", "airports": [
        {"code": "ULN", "city": "Ulaanbaatar", "name": "Ulaanbaatar", "lat": 47.6432, "lon": 106.8221},
    ]},
    "Vietnam": {"iso2": "VN", "region": "asia", "currency": "VND", "airports": [
        {"code": "SGN", "city": "Ho Chi Minh City", "name": "Ho Chi Minh City", "lat": 10.8188, "lon": 106.6520},
        {"code": "HAN", "city": "Hanoi", "name": "Hanoi Noi Bai", "lat": 21.2212, "lon": 105.8072},
        {"code": "DAD", "city": "Da Nang", "name": "Da Nang", "lat": 16.0439, "lon": 108.1994},
    ]},
    "South Korea": {"iso2": "KR", "region": "asia", "currency": "KRW", "airports": [
        {"code": "ICN", "city": "Seoul", "name": "Seoul Incheon", "lat": 37.4602, "lon": 126.4407},
        {"code": "PUS", "city": "Busan", "name": "Busan Gimhae", "lat": 35.1795, "lon": 128.9382},
        {"code": "CJU", "city": "Jeju", "name": "Jeju", "lat": 33.5113, "lon": 126.4930},
    ]},
    "India": {"iso2": "IN", "region": "asia", "currency": "INR", "airports": [
        {"code": "DEL", "city": "Delhi", "name": "Delhi", "lat": 28.5562, "lon": 77.1000},
        {"code": "BOM", "city": "Mumbai", "name": "Mumbai", "lat": 19.0896, "lon": 72.8656},
        {"code": "BLR", "city": "Bangalore", "name": "Bangalore", "lat": 13.1979, "lon": 77.7063},
        {"code": "MAA", "city": "Chennai", "name": "Chennai", "lat": 12.9941, "lon": 80.1709},
    ]},

    # --- South America (incl. Central America) ---
    "Brazil": {"iso2": "BR", "region": "south_america", "currency": "BRL", "airports": [
        {"code": "GRU", "city": "Sao Paulo", "name": "Sao Paulo Guarulhos", "lat": -23.4356, "lon": -46.4731},
        {"code": "GIG", "city": "Rio de Janeiro", "name": "Rio de Janeiro Galeao", "lat": -22.8100, "lon": -43.2506},
        {"code": "BSB", "city": "Brasilia", "name": "Brasilia", "lat": -15.8697, "lon": -47.9208},
    ]},
    "Argentina": {"iso2": "AR", "region": "south_america", "currency": "ARS", "airports": [
        {"code": "EZE", "city": "Buenos Aires", "name": "Buenos Aires Ezeiza", "lat": -34.8222, "lon": -58.5358},
        {"code": "COR", "city": "Cordoba", "name": "Cordoba", "lat": -31.3236, "lon": -64.2080},
        {"code": "MDZ", "city": "Mendoza", "name": "Mendoza", "lat": -32.8317, "lon": -68.7929},
    ]},
    "Bolivia": {"iso2": "BO", "region": "south_america", "currency": "BOB", "airports": [
        {"code": "VVI", "city": "Santa Cruz", "name": "Santa Cruz Viru Viru", "lat": -17.6448, "lon": -63.1354},
        {"code": "LPB", "city": "La Paz", "name": "La Paz El Alto", "lat": -16.5133, "lon": -68.1923},
    ]},
    "Chile": {"iso2": "CL", "region": "south_america", "currency": "CLP", "airports": [
        {"code": "SCL", "city": "Santiago", "name": "Santiago", "lat": -33.3930, "lon": -70.7858},
    ]},
    "Colombia": {"iso2": "CO", "region": "south_america", "currency": "COP", "airports": [
        {"code": "BOG", "city": "Bogota", "name": "Bogota", "lat": 4.7016, "lon": -74.1469},
        {"code": "MDE", "city": "Medellin", "name": "Medellin Rionegro", "lat": 6.1645, "lon": -75.4231},
        {"code": "CTG", "city": "Cartagena", "name": "Cartagena", "lat": 10.4424, "lon": -75.5130},
    ]},
    "Ecuador": {"iso2": "EC", "region": "south_america", "currency": "USD", "airports": [
        {"code": "UIO", "city": "Quito", "name": "Quito", "lat": -0.1292, "lon": -78.3575},
        {"code": "GYE", "city": "Guayaquil", "name": "Guayaquil", "lat": -2.1574, "lon": -79.8837},
    ]},
    "Guyana": {"iso2": "GY", "region": "south_america", "currency": "GYD", "airports": [
        {"code": "GEO", "city": "Georgetown", "name": "Georgetown", "lat": 6.4985, "lon": -58.2541},
    ]},
    "Paraguay": {"iso2": "PY", "region": "south_america", "currency": "PYG", "airports": [
        {"code": "ASU", "city": "Asuncion", "name": "Asuncion", "lat": -25.2400, "lon": -57.5200},
    ]},
    "Peru": {"iso2": "PE", "region": "south_america", "currency": "PEN", "airports": [
        {"code": "LIM", "city": "Lima", "name": "Lima", "lat": -12.0219, "lon": -77.1143},
        {"code": "CUZ", "city": "Cusco", "name": "Cusco", "lat": -13.5357, "lon": -71.9388},
    ]},
    "Suriname": {"iso2": "SR", "region": "south_america", "currency": "SRD", "airports": [
        {"code": "PBM", "city": "Paramaribo", "name": "Paramaribo", "lat": 5.4528, "lon": -55.1878},
    ]},
    "Uruguay": {"iso2": "UY", "region": "south_america", "currency": "UYU", "airports": [
        {"code": "MVD", "city": "Montevideo", "name": "Montevideo", "lat": -34.8384, "lon": -56.0308},
        {"code": "PDP", "city": "Punta del Este", "name": "Punta del Este", "lat": -34.8551, "lon": -55.0943},
    ]},
    "Venezuela": {"iso2": "VE", "region": "south_america", "currency": "VES", "airports": [
        {"code": "CCS", "city": "Caracas", "name": "Caracas", "lat": 10.6031, "lon": -66.9906},
    ]},
    "Belize": {"iso2": "BZ", "region": "south_america", "currency": "BZD", "airports": [
        {"code": "BZE", "city": "Belize City", "name": "Belize City", "lat": 17.5391, "lon": -88.3082},
    ]},
    "Costa Rica": {"iso2": "CR", "region": "south_america", "currency": "CRC", "airports": [
        {"code": "SJO", "city": "San Jose", "name": "San Jose", "lat": 9.9939, "lon": -84.2088},
        {"code": "LIR", "city": "Liberia", "name": "Liberia Guanacaste", "lat": 10.5933, "lon": -85.5444},
    ]},
    "El Salvador": {"iso2": "SV", "region": "south_america", "currency": "USD", "airports": [
        {"code": "SAL", "city": "San Salvador", "name": "San Salvador", "lat": 13.4409, "lon": -89.0557},
    ]},
    "Guatemala": {"iso2": "GT", "region": "south_america", "currency": "GTQ", "airports": [
        {"code": "GUA", "city": "Guatemala City", "name": "Guatemala City", "lat": 14.5833, "lon": -90.5275},
        {"code": "FRS", "city": "Flores", "name": "Flores (Tikal)", "lat": 16.9138, "lon": -89.8664},
    ]},
    "Honduras": {"iso2": "HN", "region": "south_america", "currency": "HNL", "airports": [
        {"code": "TGU", "city": "Tegucigalpa", "name": "Tegucigalpa", "lat": 14.0608, "lon": -87.2172},
        {"code": "SAP", "city": "San Pedro Sula", "name": "San Pedro Sula", "lat": 15.4526, "lon": -87.9236},
        {"code": "RTB", "city": "Roatan", "name": "Roatan", "lat": 16.3168, "lon": -86.5230},
    ]},
    "Nicaragua": {"iso2": "NI", "region": "south_america", "currency": "NIO", "airports": [
        {"code": "MGA", "city": "Managua", "name": "Managua", "lat": 12.1415, "lon": -86.1682},
    ]},
    "Panama": {"iso2": "PA", "region": "south_america", "currency": "USD", "airports": [
        {"code": "PTY", "city": "Panama City", "name": "Panama City Tocumen", "lat": 9.0714, "lon": -79.3835},
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
        primary = info["airports"][0]
        result[name] = {
            "iso2": info["iso2"],
            "region": info["region"],
            "currency": info["currency"],
            "flag": flag_emoji(info["iso2"]),
            "airports": info["airports"],
            "airport": primary["code"],
            "airport_city": primary["city"],
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
