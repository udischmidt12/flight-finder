# Flight Finder

Finds the cheapest flight from your home airport to one representative airport per country on your wishlist, using SerpApi's Google Flights engine. Also tracks trip expenses with currency conversion to ILS.

## Setup

1. `pip install -r requirements.txt`
2. `cp config.json.example config.json` and fill in `home_airport`, `visited_countries`, `wishlist_countries`.
3. Provide `SERPAPI_KEY` — either as a real environment variable, or in a local `.env` file next to `app.py`:

   ```
   SERPAPI_KEY=your_key_here
   # optional: require HTTP basic auth (password only)
   APP_ACCESS_TOKEN=some_shared_secret
   ```

   `.env` is gitignored and loaded automatically at startup; real environment variables take precedence over it.
4. `python app.py` — serves on http://localhost:5000.

Deployed on PythonAnywhere, where `SERPAPI_KEY` is set as a web-app environment variable (no `.env` needed there).
