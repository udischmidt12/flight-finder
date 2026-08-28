import csv
import io
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

# Load a local .env (SERPAPI_KEY, APP_ACCESS_TOKEN, ...) if present. Real
# environment variables always win over .env values. No-op if the file is
# absent, so this is safe on PythonAnywhere where the vars are set for real.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from countries import all_countries, origin_regions, REGION_LABELS
from flights import search_flights, FlightApiError
import skyscanner
import receipts
import prearrival
from expenses import load_expenses, add_expense, update_expense, delete_expense, summarize, CATEGORIES

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
# Search window: one SerpApi call per day, so the user picks it per search
# (Tomorrow ... 1 week). Compare-all always forces 1 to stay cheap.
DEFAULT_WINDOW_DAYS = 3
MAX_WINDOW_DAYS = 7
RESULT_LIMIT = 5        # flight options to return per search (no extra API calls)
AIRPORT_CODE_RE = re.compile(r"^[A-Za-z]{3}$")


def load_config():
    """config.json if present (local dev), else HOME_AIRPORT / PASSPORT env
    vars (production), else sensible defaults. Never None -- the app always
    has somewhere to fly from."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "home_airport": os.environ.get("HOME_AIRPORT", "TLV"),
        "passport": os.environ.get("PASSPORT", "Israeli"),
    }


def require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = os.environ.get("APP_ACCESS_TOKEN")
        if not token:
            # no token configured -> auth disabled (local dev only)
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or auth.password != token:
            return Response(
                "Access denied", 401,
                {"WWW-Authenticate": 'Basic realm="flight-finder"'},
            )
        return f(*args, **kwargs)
    return wrapped


DESTINATION_SECTION_ORDER = ["asia", "south_america"]


def destination_sections():
    """Every destination country, grouped Asia then South America -- the
    same country lists the origin picker offers. Each section:
    {"key", "label", "countries": {name: info, ...}}."""
    countries = all_countries()
    regions = origin_regions()  # {"asia": [...names], "south_america": [...]}
    sections = []
    for key in DESTINATION_SECTION_ORDER:
        names = sorted(regions.get(key) or [])
        if not names:
            continue
        sections.append({
            "key": key,
            "label": REGION_LABELS.get(key, key),
            "countries": {n: countries[n] for n in names},
        })
    return sections


@app.after_request
def _no_store_html(response):
    """The page is a single template that changes often during development;
    tell browsers never to serve a stale copy of the HTML."""
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


# --- PWA plumbing: served from the root so the service worker's scope is "/" ---
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(
        _STATIC_DIR, "manifest.webmanifest", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(
        _STATIC_DIR, "sw.js", mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/.well-known/assetlinks.json")
def assetlinks():
    """Digital Asset Links -- lets the signed Android APK (a Trusted Web
    Activity) open this site with no browser UI. Populated after the APK
    is built; returns an empty list until then."""
    path = os.path.join(_STATIC_DIR, "assetlinks.json")
    if os.path.exists(path):
        return send_from_directory(_STATIC_DIR, "assetlinks.json",
                                   mimetype="application/json")
    return jsonify([])


@app.route("/")
@require_auth
def index():
    config = load_config()
    if config is None:
        return render_template(
            "index.html",
            error="config.json not found. Copy config.json.example to config.json and fill in your details.",
            destination_sections=destination_sections(),
            origins=all_countries(),
            origin_regions=origin_regions(),
            region_labels=REGION_LABELS,
            home_airport=None,
            window_days=DEFAULT_WINDOW_DAYS,
            expense_categories=CATEGORIES,
        )

    return render_template(
        "index.html",
        error=None,
        destination_sections=destination_sections(),
        origins=all_countries(),
        origin_regions=origin_regions(),
        region_labels=REGION_LABELS,
        home_airport=config.get("home_airport"),
        window_days=DEFAULT_WINDOW_DAYS,
        expense_categories=CATEGORIES,
    )


@app.route("/search/<country>")
@require_auth
def search_country(country):
    config = load_config()
    if config is None:
        return jsonify({"error": "config.json not found"}), 500

    home_airport = config.get("home_airport")
    if not home_airport:
        return jsonify({"error": "home_airport missing from config.json"}), 500

    origin = request.args.get("origin", home_airport)
    if not AIRPORT_CODE_RE.match(origin or ""):
        origin = home_airport
    origin = origin.upper()

    direct_only = request.args.get("direct_only", "false").lower() == "true"

    entry = all_countries().get(country)
    if not entry:
        return jsonify({"error": f"unknown country: {country}"}), 404

    # Default to the country's primary airport; honour ?dest=<CODE> when it
    # names another airport that actually belongs to this country.
    airport = entry["airport"]
    dest = (request.args.get("dest") or "").upper()
    if dest and AIRPORT_CODE_RE.match(dest):
        by_code = {a["code"]: a for a in entry["airports"]}
        if dest in by_code:
            airport = dest
    airport_city = next(
        (a["city"] for a in entry["airports"] if a["code"] == airport), airport)

    try:
        window_days = int(request.args.get("days", DEFAULT_WINDOW_DAYS))
    except (TypeError, ValueError):
        window_days = DEFAULT_WINDOW_DAYS
    window_days = max(1, min(MAX_WINDOW_DAYS, window_days))

    today = date.today()
    dates = [(today + timedelta(days=i)).isoformat() for i in range(1, window_days + 1)]

    all_flights = []
    skipped_dates = []
    for d in dates:
        # Hit both engines at once so the search isn't the sum of two API
        # round-trips.
        def _skyscanner_leg():
            try:
                return skyscanner.search_cheapest_flight(
                    origin, airport, d, direct_only=direct_only)
            except skyscanner.SkyscannerError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            g_future = pool.submit(
                search_flights, origin, airport, d,
                direct_only=direct_only, limit=RESULT_LIMIT)
            s_future = pool.submit(_skyscanner_leg)

            # Google Flights (SerpApi) -- still authoritative for hard
            # errors like a missing API key.
            try:
                g_list = g_future.result()
            except FlightApiError as e:
                return jsonify({"error": str(e)}), 500
            s = s_future.result()  # best-effort supplement, never fatal

        day_of_week = date.fromisoformat(d).strftime("%A")
        candidates = []
        for g in g_list or []:
            g.setdefault("source", "google")
            candidates.append(g)
        if s and s.get("price") is not None:
            candidates.append(s)

        if not candidates:
            skipped_dates.append(d)
            continue

        for flight in candidates:
            all_flights.append({
                "date": d,
                "day_of_week": day_of_week,
                "price": flight["price"],
                "airline": flight["airline"],
                "departure": flight["departure"],
                "arrival": flight["arrival"],
                "is_direct": flight["is_direct"],
                "layovers": flight["layovers"],
                "total_duration_minutes": flight["total_duration_minutes"],
                "source": flight.get("source", "google"),
                # Skyscanner-sourced fares carry the itinerary id -> the Book
                # link deep-links to that one flight's vendor list on Skyscanner.
                "skyscanner_config": flight.get("itinerary_id"),
            })

    all_flights.sort(key=lambda r: r["price"] if r["price"] is not None else float("inf"))

    # Drop near-duplicates (same airline / times / price / stops) then cap.
    seen = set()
    results = []
    for r in all_flights:
        key = (r["airline"], r["departure"], r["arrival"], r["price"], r["is_direct"])
        if key in seen:
            continue
        seen.add(key)
        results.append(r)
        if len(results) >= RESULT_LIMIT:
            break

    return jsonify({
        "country": country,
        "airport": airport,
        "airport_city": airport_city,
        "origin": origin,
        "results": results,
        "skipped_dates": skipped_dates,
        "window_days": window_days,
    })


@app.route("/api/expenses", methods=["GET"])
@require_auth
def list_expenses():
    expenses = load_expenses()
    expenses_sorted = sorted(expenses, key=lambda e: e.get("logged_at", 0), reverse=True)
    return jsonify({
        "expenses": expenses_sorted,
        "summary": summarize(expenses),
    })


def parse_expense_fields(data):
    """Validate expense fields from a request body. Returns (fields, error)
    -- fields is a dict ready for add_expense/update_expense on success,
    error is an (message, status) tuple on failure."""
    country = (data.get("country") or "").strip()
    category = data.get("category")
    amount = data.get("amount")
    currency = (data.get("currency") or "").strip()
    expense_date = (data.get("date") or "").strip()
    note = (data.get("note") or "").strip()

    if not country:
        return None, ("country is required", 400)
    if category not in CATEGORIES:
        return None, ("invalid category", 400)
    if not isinstance(amount, (int, float)) or amount <= 0:
        return None, ("amount must be a positive number", 400)
    if not re.match(r"^[A-Za-z]{3}$", currency):
        return None, ("invalid currency code", 400)
    if not expense_date:
        expense_date = date.today().isoformat()

    return {
        "country": country,
        "category": category,
        "amount": amount,
        "currency": currency,
        "expense_date": expense_date,
        "note": note,
    }, None


@app.route("/api/expenses", methods=["POST"])
@require_auth
def create_expense():
    fields, error = parse_expense_fields(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error[0]}), error[1]

    record = add_expense(**fields)
    return jsonify({"expense": record, "summary": summarize(load_expenses())})


@app.route("/api/expenses/<expense_id>", methods=["PUT"])
@require_auth
def edit_expense(expense_id):
    fields, error = parse_expense_fields(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error[0]}), error[1]

    record = update_expense(expense_id, **fields)
    if record is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"expense": record, "summary": summarize(load_expenses())})


@app.route("/api/expenses/<expense_id>", methods=["DELETE"])
@require_auth
def remove_expense(expense_id):
    if not delete_expense(expense_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"summary": summarize(load_expenses())})


@app.route("/api/expenses/export")
@require_auth
def export_expenses():
    expenses = sorted(load_expenses(), key=lambda e: e.get("date", ""))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "country", "category", "amount", "currency", "amount_ils", "note"])
    for e in expenses:
        writer.writerow([
            e.get("date", ""),
            e.get("country", ""),
            e.get("category", ""),
            e.get("amount", ""),
            e.get("currency", ""),
            e.get("amount_ils", ""),
            e.get("note", ""),
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses_export.csv"},
    )


RECEIPT_MAX_BYTES = 8 * 1024 * 1024


@app.route("/api/receipts/scan", methods=["POST"])
@require_auth
def scan_receipt():
    """Read a receipt/invoice image or PDF with Claude and return
    {amount, currency, date, merchant} for the expense form to pre-fill."""
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file uploaded"}), 400

    data = f.read(RECEIPT_MAX_BYTES + 1)
    if len(data) > RECEIPT_MAX_BYTES:
        return jsonify({"error": "file is larger than 8 MB"}), 400

    try:
        result = receipts.scan(data, f.mimetype)
    except receipts.ReceiptError as e:
        return jsonify({"error": str(e)}), 502

    return jsonify(result)


PASSPORTS = {
    "israeli": "Israeli", "israel": "Israeli",
    "german": "German", "germany": "German",
}


@app.route("/api/prearrival/<country>")
@require_auth
def prearrival_info(country):
    """Current visa / arrival-form / entry essentials for a destination,
    tailored to ?passport=Israeli|German. Cached ~2 weeks per
    country+passport; ?refresh=1 forces a re-fetch."""
    if country not in all_countries():
        return jsonify({"error": f"unknown country: {country}"}), 404

    config = load_config() or {}
    raw = request.args.get("passport") or config.get("passport") or "Israeli"
    passport = PASSPORTS.get(raw.strip().lower(), "Israeli")
    force = request.args.get("refresh") == "1"

    try:
        data = prearrival.get(country, passport, force=force)
    except prearrival.PreArrivalError as e:
        return jsonify({"error": str(e)}), 502

    return jsonify({"country": country, "passport": passport, **data})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
