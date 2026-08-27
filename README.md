# Flight Finder

Finds the cheapest flight from your home airport to one representative airport per country on your wishlist. Each route is checked against **two engines — SerpApi (Google Flights) and Skyscanner (via RapidAPI)** — and the cheaper fare wins; if one engine is down or returns nothing, the other still answers. Also tracks trip expenses with currency conversion to ILS.

## Setup

1. `pip install -r requirements.txt`
2. `cp config.json.example config.json` and fill in `home_airport`, `visited_countries`, `wishlist_countries`.
3. Provide API keys — either as real environment variables, or in a local `.env` file next to `app.py`:

   ```
   SERPAPI_KEY=your_serpapi_key          # Google Flights engine
   RAPIDAPI_KEY=your_rapidapi_key        # Skyscanner engine (optional; skipped if unset)
   # optional: require HTTP basic auth (password only)
   APP_ACCESS_TOKEN=some_shared_secret
   ```

   `.env` is gitignored and loaded automatically at startup; real environment variables take precedence over it. Skyscanner airport-id lookups are cached to `skyscanner_airports.json` (also gitignored).
4. `python app.py` — serves on http://localhost:5000.

Deployed on PythonAnywhere, where `SERPAPI_KEY` / `RAPIDAPI_KEY` are set as web-app environment variables (no `.env` needed there).
