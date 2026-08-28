"""Pre-arrival essentials for a destination country -- visa / e-visa and
max stay, mandatory arrival forms, passport-validity rules, etc. -- pulled
fresh from the web by Claude (web search) and cached for two weeks.

Needs ANTHROPIC_API_KEY (env or .env). One lookup per country per
fortnight; a lookup uses a few web searches (~5-10 cents).
"""

import json
import os
import re
import threading
import time

import anthropic

# Haiku keeps a lookup at a few cents. Bump to "claude-sonnet-5" or
# "claude-opus-5" here if you want higher-confidence visa research.
MODEL = "claude-haiku-4-5"
CACHE_PATH = os.path.join(
    os.environ.get("DATA_DIR") or os.path.dirname(__file__), "prearrival_cache.json")
TTL_SECONDS = 14 * 24 * 3600  # re-fetch after two weeks

# Basic web search -- works on every model tier including Haiku. max_uses
# caps the search rounds; each round re-processes fetched page text, so
# it's the main cost lever.
_WS = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}

_cache_lock = threading.Lock()


class PreArrivalError(Exception):
    """Config / API problem -- surfaced to the user."""


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise PreArrivalError("ANTHROPIC_API_KEY is not set")
    kwargs = {"api_key": key}
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    if ws:  # identity-linked keys require the workspace id on every request
        kwargs["default_headers"] = {"anthropic-workspace-id": ws}
    return anthropic.Anthropic(**kwargs)


def _prompt(country, passport):
    year = time.strftime("%Y")
    return (
        f"I hold a {passport} passport and I am about to fly to {country}. "
        f"Search the web for the CURRENT ({year}) official entry rules and give me "
        "the essential things to sort out or know BEFORE boarding, as short bullets.\n\n"
        "Cover, where relevant:\n"
        f"- Visa / e-visa: does a {passport} passport holder need one? "
        "visa-free, visa-on-arrival, e-visa, or embassy visa? Maximum stay allowed, "
        "and typical cost and processing time for an e-visa.\n"
        "- Any mandatory arrival form, digital arrival card, health declaration or "
        "online registration -- name it and say when it must be completed.\n"
        "- Passport validity rule (e.g. 6 months beyond entry) and blank-page needs.\n"
        "- Onward / return ticket or proof-of-funds checks.\n"
        "- Required vaccinations or health entry requirements.\n"
        "- Any customs / currency-declaration limits worth knowing.\n"
        "- Anything else genuinely essential before flying.\n\n"
        "Prefer official government, embassy or IATA Travel Centre sources. Skip "
        "anything that does not apply. Reply as a plain bulleted list: '- ' for each "
        "point, '  - ' for a sub-point, and start each top-level bullet with a bold "
        "label, e.g. '- **Visa:** ...'. No intro and no closing summary. "
        "Finish with a single final line: 'Sources: ' then the site domains you used, "
        "comma-separated."
    )


def _extract_text(resp):
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(p.strip() for p in parts if p and p.strip()).strip()


_BULLET_RE = re.compile(r"^\s*[-*•]\s+")
_SOURCES_RE = re.compile(r"^\s*sources?\s*:", re.I)


def _normalize(text):
    """Claude (with web search) tends to open with a line like 'I'll search
    ...' and to wrap one bullet across several lines. Drop the preamble and
    fold continuation lines back into their bullet so each line is one clean
    point for the client to render."""
    out = []
    started = False
    for raw in (text or "").replace("\r", "").split("\n"):
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        is_bullet = bool(_BULLET_RE.match(line))
        is_sources = bool(_SOURCES_RE.match(s))

        if not started:
            if is_bullet:
                started = True
                out.append(line)
            continue  # skip any preamble before the first bullet

        if is_bullet or is_sources:
            out.append(line)
        elif out:  # continuation of the previous line
            if s in {".", ",", ";", ":", ")"}:
                out[-1] = out[-1].rstrip() + s
            else:
                out[-1] = out[-1].rstrip() + " " + s
        else:
            out.append(line)

    joined = re.sub(r"[ \t]+([,;:.)])", r"\1", "\n".join(out).strip())
    return joined or (text or "").strip()


def _clean_bad_request(msg):
    m = (msg or "").strip()
    low = m.lower()
    if "credit balance is too low" in low:
        return ("Anthropic account has no API credit -- add credits at "
                "console.anthropic.com (Plans & Billing).")
    if "workspace" in low and "identity-linked" in low:
        return ("This ANTHROPIC_API_KEY is identity-linked -- add "
                "ANTHROPIC_WORKSPACE_ID=... to .env (console.anthropic.com -> "
                "Settings -> Workspaces), or make a standard API key instead.")
    return m[:200] or "bad request to the Claude API"


def _call(country, passport):
    client = _client()
    kwargs = dict(
        model=MODEL,
        max_tokens=1800,
        messages=[{"role": "user", "content": _prompt(country, passport)}],
    )
    try:
        resp = client.messages.create(tools=[_WS], **kwargs)
    except anthropic.AuthenticationError:
        raise PreArrivalError("ANTHROPIC_API_KEY is invalid")
    except anthropic.RateLimitError:
        raise PreArrivalError("Claude API rate limit hit -- try again shortly")
    except anthropic.BadRequestError as e:
        raise PreArrivalError(_clean_bad_request(str(getattr(e, "message", "") or e)))
    except anthropic.APIStatusError as e:
        raise PreArrivalError(f"Claude API error ({e.status_code})")
    except anthropic.APIConnectionError:
        raise PreArrivalError("couldn't reach the Claude API")

    text = _normalize(_extract_text(resp))
    if not text:
        raise PreArrivalError("no information came back")
    return text


# --- disk cache ----------------------------------------------------------

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
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def get(country, passport, force=False):
    """Return {text, fetched_at, passport, cached}. Cached per
    country+passport on disk; re-fetched if missing, older than the TTL,
    or force=True."""
    key = f"{country.lower()}|{passport.lower()}"
    now = time.time()

    if not force:
        hit = _load_cache().get(key)
        if hit and hit.get("text") and now - hit.get("fetched_at", 0) < TTL_SECONDS:
            return {**hit, "text": _normalize(hit["text"]), "cached": True}

    text = _call(country, passport)
    entry = {"text": text, "fetched_at": now, "passport": passport}
    with _cache_lock:
        cache = _load_cache()
        cache[key] = entry
        _save_cache(cache)
    return {**entry, "cached": False}
